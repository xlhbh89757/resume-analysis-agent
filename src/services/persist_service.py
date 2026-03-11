from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from src.models.candidate import Candidate, ProjectExperience, Skill, WorkExperience
from src.models.resume_batch import ResumeStructDeadletter, ResumeStructTask
from src.utils.project_experience_normalizer import to_text_list
from src.utils.work_experience_normalizer import normalize_work_experience

SOURCE_FIELD_MAPPING = {
    "employee": "employee_id",
    "entrant": "entrant_id",
    "submit_candidate": "submit_candidate_id",
}


class PersistService:
    """统一处理在线上传和离线批处理的结构化结果落库。"""

    def __init__(self, db: Session):
        self.db = db

    def apply_structured_resume(
        self,
        candidate: Candidate,
        resume_text: str | None,
        structured_resume: dict[str, Any],
    ) -> Candidate:
        """把结构化结果写入候选人对象，但不提交事务。"""
        candidate.resume_text = resume_text or candidate.resume_text
        candidate.name = structured_resume.get("name")
        candidate.email = structured_resume.get("email")
        candidate.phone = structured_resume.get("phone")
        candidate.education_level = structured_resume.get("education_level")
        candidate.years_of_experience = structured_resume.get("years_of_experience")
        candidate.current_position = structured_resume.get("current_position")
        candidate.summary = structured_resume.get("summary")
        candidate.status = "completed"

        # 同一候选人重跑时先清空旧明细，避免重复叠加。
        candidate.work_experiences.clear()
        candidate.project_experiences.clear()
        candidate.skills.clear()

        for exp in structured_resume.get("work_experiences", []):
            normalized_work_exp = normalize_work_experience(exp)
            candidate.work_experiences.append(
                WorkExperience(
                    company_name=normalized_work_exp["company_name"],
                    position=normalized_work_exp["position"],
                    start_date=normalized_work_exp["start_date"],
                    end_date=normalized_work_exp["end_date"],
                    responsibilities=normalized_work_exp["responsibilities"],
                    achievements=normalized_work_exp["achievements"],
                )
            )

        for proj in structured_resume.get("project_experiences", []):
            technologies = to_text_list(proj.get("technologies"))
            responsibilities = to_text_list(
                proj.get("responsibilities") or proj.get("work_responsibilities")
            )
            achievements = to_text_list(proj.get("achievements"))
            candidate.project_experiences.append(
                ProjectExperience(
                    project_name=proj.get("project_name"),
                    role=proj.get("role"),
                    start_date=proj.get("start_date"),
                    end_date=proj.get("end_date"),
                    description=proj.get("description"),
                    technologies=json.dumps(technologies, ensure_ascii=False),
                    responsibilities=json.dumps(responsibilities, ensure_ascii=False),
                    achievements=json.dumps(achievements, ensure_ascii=False),
                )
            )

        for skill in structured_resume.get("skills", []):
            candidate.skills.append(
                Skill(
                    skill_name=skill.get("skill_name", ""),
                    skill_category=skill.get("skill_category"),
                    proficiency_level=skill.get("proficiency_level"),
                )
            )

        return candidate

    def persist_structured_resume(self, payload: dict[str, Any]) -> dict[str, Any]:
        """按幂等键写入结构化结果。"""
        source_type = payload["source_type"]
        source_id = payload["source_id"]
        resume_created_time = payload["resume_created_time"]
        force_reparse = bool(payload.get("force_reparse"))
        idempotency_key = self._build_idempotency_key(source_type, source_id, resume_created_time)
        task = self._get_task(payload.get("task_id"), idempotency_key)
        was_success = bool(task and task.status == "success")

        if was_success and not force_reparse:
            return {
                "status": "skipped",
                "candidate_id": None,
                "idempotency_key": idempotency_key,
                "force_reparse": False,
            }

        now = datetime.utcnow()
        if task:
            task.status = "running"
            task.started_at = now
            task.error_code = None
            task.error_message = None
            task.attempt_count = (task.attempt_count or 0) + 1

        structured_resume = payload.get("structured_resume") or {}
        candidate = self._find_or_create_candidate(
            source_type=source_type,
            source_id=source_id,
            structured_resume=structured_resume,
        )

        try:
            self._assign_source_identifier(candidate, source_type, source_id)
            self.apply_structured_resume(
                candidate=candidate,
                resume_text=payload.get("resume_text"),
                structured_resume=structured_resume,
            )

            if task:
                task.status = "success"
                task.finished_at = now
                task.llm_tokens_in = payload.get("llm_tokens_in")
                task.llm_tokens_out = payload.get("llm_tokens_out")
                llm_cost = payload.get("llm_cost")
                task.llm_cost = str(llm_cost) if llm_cost is not None else None
                if task.batch and not was_success:
                    task.batch.success_count += 1

            self.db.commit()
            self.db.refresh(candidate)
            return {
                "status": "success",
                "candidate_id": candidate.id,
                "idempotency_key": idempotency_key,
                "force_reparse": force_reparse,
            }
        except Exception as exc:
            self.db.rollback()
            self._mark_task_failed(task_id=task.id if task else None, error_message=str(exc))
            raise

    def create_deadletter(
        self,
        payload: dict[str, Any],
        error_code: str,
        error_message: str,
    ) -> dict[str, Any]:
        """记录死信任务，保留后续重试所需上下文。"""
        task = self._get_task(
            payload.get("task_id"),
            self._build_idempotency_key(
                payload["source_type"],
                payload["source_id"],
                payload["resume_created_time"],
            ),
        )
        if task is None:
            raise ValueError("ResumeStructTask not found for deadletter payload")

        task.status = "dead"
        task.error_code = error_code
        task.error_message = error_message
        task.finished_at = datetime.utcnow()

        deadletter = ResumeStructDeadletter(
            task_id=task.id,
            source_type=payload["source_type"],
            source_id=payload["source_id"],
            filekey=payload.get("filekey"),
            resume_created_time=payload["resume_created_time"],
            last_error=error_message,
            payload_snapshot=json.dumps(payload, ensure_ascii=False),
        )
        self.db.add(deadletter)
        self.db.commit()
        self.db.refresh(deadletter)

        return {
            "status": "dead",
            "deadletter_id": deadletter.id,
            "error_code": error_code,
        }

    def _build_idempotency_key(self, source_type: str, source_id: str, resume_created_time: str) -> str:
        return f"{source_type}:{source_id}:{resume_created_time}"

    def _get_task(self, task_id: int | None, idempotency_key: str) -> ResumeStructTask | None:
        if task_id is not None:
            return self.db.query(ResumeStructTask).filter(ResumeStructTask.id == task_id).first()
        return (
            self.db.query(ResumeStructTask)
            .filter(ResumeStructTask.idempotency_key == idempotency_key)
            .first()
        )

    def _find_or_create_candidate(
        self,
        source_type: str,
        source_id: str,
        structured_resume: dict[str, Any],
    ) -> Candidate:
        candidate = self._find_candidate_by_source(source_type, source_id)
        if candidate:
            return candidate

        candidate = self._find_candidate_by_contact(
            name=structured_resume.get("name"),
            phone=structured_resume.get("phone"),
        )
        if candidate:
            return candidate

        candidate = Candidate(status="pending")
        self.db.add(candidate)
        self.db.flush()
        return candidate

    def _find_candidate_by_source(self, source_type: str, source_id: str) -> Candidate | None:
        field_name = SOURCE_FIELD_MAPPING[source_type]
        column = getattr(Candidate, field_name)
        return self.db.query(Candidate).filter(column == source_id).first()

    def _find_candidate_by_contact(self, name: str | None, phone: str | None) -> Candidate | None:
        if name and phone:
            candidate = (
                self.db.query(Candidate)
                .filter(Candidate.name == name, Candidate.phone == phone)
                .first()
            )
            if candidate:
                return candidate

        if phone:
            candidate = self.db.query(Candidate).filter(Candidate.phone == phone).first()
            if candidate:
                return candidate

        if name:
            return self.db.query(Candidate).filter(Candidate.name == name).first()

        return None

    def _assign_source_identifier(self, candidate: Candidate, source_type: str, source_id: str) -> None:
        field_name = SOURCE_FIELD_MAPPING[source_type]
        if getattr(candidate, field_name) != source_id:
            setattr(candidate, field_name, source_id)

    def _mark_task_failed(self, task_id: int | None, error_message: str) -> None:
        if task_id is None:
            return

        failed_task = (
            self.db.query(ResumeStructTask)
            .filter(ResumeStructTask.id == task_id)
            .first()
        )
        if not failed_task:
            return

        failed_task.status = "failed"
        failed_task.error_code = "E_PERSIST"
        failed_task.error_message = error_message
        failed_task.finished_at = datetime.utcnow()
        if failed_task.batch:
            failed_task.batch.failed_count += 1
        self.db.commit()
