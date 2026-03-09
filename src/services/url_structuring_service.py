"""基于 URL 的简历结构化服务。"""

from __future__ import annotations

import mimetypes
import tempfile
from pathlib import Path
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from src.models.candidate import Candidate
from src.models.resume_batch import ResumeStructBatch, ResumeStructTask
from src.services.document_parser import DocumentParser
from src.services.llm_service import LLMAnalysisService
from src.services.persist_service import PersistService
from src.services.resume_source_client import ResumeSourceClient

MANUAL_BATCH_ID = "manual-sync-api"


class URLStructuringService:
    """统一封装 URL 下载、解析、抽取和落库流程。"""

    def __init__(
        self,
        db: Session,
        document_parser: DocumentParser | None = None,
        llm_service: LLMAnalysisService | None = None,
        persist_service: PersistService | None = None,
        source_client: ResumeSourceClient | None = None,
        downloader: Callable[[str], Awaitable[Path]] | None = None,
    ) -> None:
        self.db = db
        self.document_parser = document_parser or DocumentParser()
        self.llm_service = llm_service or LLMAnalysisService()
        self.persist_service = persist_service or PersistService(db)
        self.source_client = source_client or ResumeSourceClient()
        self.downloader = downloader or self._download_to_temp_file

    async def structure_from_employee(
        self,
        employee_id: str,
        resume_created_time: str,
    ) -> dict[str, Any]:
        """按员工标识拉取临时 URL，并执行完整结构化流程。"""
        temp_url_result = await self.source_client.get_temp_url(employee_id)
        temp_url = temp_url_result["temp_url"]
        return await self.structure_from_url(
            resume_url=temp_url,
            employee_id=employee_id,
            resume_created_time=resume_created_time,
        )

    async def structure_from_url(
        self,
        resume_url: str,
        employee_id: str | None = None,
        resume_created_time: str | None = None,
    ) -> dict[str, Any]:
        """按 URL 下载简历、提取文本并同步落库。"""
        file_path = await self.downloader(resume_url)
        try:
            # 统一把 URL 文件下载为本地临时文件，再复用现有解析器。
            resume_text = self.document_parser.parse(str(file_path))
            structured_resume = await self.llm_service.extract_resume_info(resume_text)

            if employee_id and resume_created_time:
                task = self._ensure_manual_task(employee_id, resume_created_time)
                persist_result = self.persist_service.persist_structured_resume(
                    {
                        "task_id": task.id,
                        "employee_id": employee_id,
                        "resume_created_time": resume_created_time,
                        "resume_text": resume_text,
                        "structured_resume": structured_resume,
                    }
                )
            else:
                persist_result = self._persist_without_employee(
                    resume_text=resume_text,
                    structured_resume=structured_resume,
                )

            return {
                **persist_result,
                "resume_url": resume_url,
                "resume_text": resume_text,
                "structured_resume": structured_resume,
            }
        finally:
            # 临时文件只用于本轮解析，任务结束后立即清理，避免占满磁盘。
            if file_path.exists():
                file_path.unlink()

    async def extract_resume_text_from_url(self, resume_url: str) -> str:
        """仅执行 URL 下载与文本提取，供 Celery 抽取阶段复用。"""
        file_path = await self.downloader(resume_url)
        try:
            return self.document_parser.parse(str(file_path))
        finally:
            if file_path.exists():
                file_path.unlink()

    async def extract_resume_text_from_employee(self, employee_id: str) -> str:
        """按员工标识获取临时 URL 并提取文本。"""
        temp_url_result = await self.source_client.get_temp_url(employee_id)
        return await self.extract_resume_text_from_url(temp_url_result["temp_url"])

    async def _download_to_temp_file(self, resume_url: str) -> Path:
        """下载 URL 文件到临时目录，供解析器读取。"""
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.get(resume_url)
            response.raise_for_status()
            suffix = self._guess_suffix(resume_url, response.headers.get("Content-Type"))
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(response.content)
                return Path(temp_file.name)

    def _guess_suffix(self, resume_url: str, content_type: str | None) -> str:
        parsed = urlparse(resume_url)
        suffix = Path(parsed.path).suffix.lower()
        if suffix in {".pdf", ".doc", ".docx"}:
            return suffix

        guessed = mimetypes.guess_extension((content_type or "").split(";")[0].strip())
        if guessed in {".pdf", ".doc", ".docx"}:
            return guessed
        return ".pdf"

    def _persist_without_employee(
        self,
        resume_text: str,
        structured_resume: dict[str, Any],
    ) -> dict[str, Any]:
        candidate = Candidate(status="pending")
        self.db.add(candidate)
        self.db.flush()

        # 调试 URL 入口没有业务幂等键，直接写候选人详情即可。
        self.persist_service.apply_structured_resume(
            candidate=candidate,
            resume_text=resume_text,
            structured_resume=structured_resume,
        )
        self.db.commit()
        self.db.refresh(candidate)
        return {
            "status": "success",
            "candidate_id": candidate.id,
            "idempotency_key": None,
        }

    def _ensure_manual_task(self, employee_id: str, resume_created_time: str) -> ResumeStructTask:
        idempotency_key = f"{employee_id}:{resume_created_time}"
        task = (
            self.db.query(ResumeStructTask)
            .filter(ResumeStructTask.idempotency_key == idempotency_key)
            .first()
        )
        if task:
            return task

        batch = (
            self.db.query(ResumeStructBatch)
            .filter(ResumeStructBatch.batch_id == MANUAL_BATCH_ID)
            .first()
        )
        if not batch:
            batch = ResumeStructBatch(
                batch_id=MANUAL_BATCH_ID,
                total_count=0,
                status="running",
            )
            self.db.add(batch)
            self.db.flush()

        batch.total_count += 1
        task = ResumeStructTask(
            batch_id=batch.id,
            employee_id=employee_id,
            resume_created_time=resume_created_time,
            idempotency_key=idempotency_key,
            status="queued",
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task