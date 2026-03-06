"""结构化简历落库服务。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from src.models.candidate import Candidate, ProjectExperience, Skill, WorkExperience
from src.models.resume_batch import ResumeStructTask
from src.utils.project_experience_normalizer import to_text_list
from src.utils.work_experience_normalizer import normalize_work_experience


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

        # 重跑同一候选人时先清空旧明细，避免工作经历、项目经历和技能重复叠加。
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
        employee_id = payload["employee_id"]
        resume_created_time = payload["resume_created_time"]
        idempotency_key = f"{employee_id}:{resume_created_time}"
        task = self._get_task(payload.get("task_id"), idempotency_key)

        # 同一幂等键已经成功时直接跳过，避免重复创建候选人记录。
        if task and task.status == "success":
            return {
                "status": "skipped",
                "candidate_id": None,
                "idempotency_key": idempotency_key,
            }

        now = datetime.utcnow()
        if task:
            task.status = "running"
            task.started_at = task.started_at or now
            task.error_code = None
            task.error_message = None

        candidate = Candidate(status="pending")
        self.db.add(candidate)
        self.db.flush()

        try:
            self.apply_structured_resume(
                candidate=candidate,
                resume_text=payload.get("resume_text"),
                structured_resume=payload.get("structured_resume") or {},
            )

            if task:
                task.status = "success"
                task.finished_at = now
                if task.batch:
                    task.batch.success_count += 1

            self.db.commit()
            self.db.refresh(candidate)
            return {
                "status": "success",
                "candidate_id": candidate.id,
                "idempotency_key": idempotency_key,
            }
        except Exception as exc:
            self.db.rollback()
            self._mark_task_failed(task_id=task.id if task else None, error_message=str(exc))
            raise

    def _get_task(self, task_id: int | None, idempotency_key: str) -> ResumeStructTask | None:
        if task_id is not None:
            return self.db.query(ResumeStructTask).filter(ResumeStructTask.id == task_id).first()
        return (
            self.db.query(ResumeStructTask)
            .filter(ResumeStructTask.idempotency_key == idempotency_key)
            .first()
        )

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