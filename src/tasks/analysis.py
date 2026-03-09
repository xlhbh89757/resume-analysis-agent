"""Celery 异步任务入口。"""

import asyncio
from types import SimpleNamespace

try:
    from celery import Celery
except ModuleNotFoundError:
    class _LocalTask:
        def __init__(self, func, bind=False):
            self.func = func
            self.bind = bind
            self.request = SimpleNamespace(retries=0)

        def run(self, *args, **kwargs):
            if self.bind:
                return self.func(self, *args, **kwargs)
            return self.func(*args, **kwargs)

        def __call__(self, *args, **kwargs):
            return self.run(*args, **kwargs)

    class Celery:  # type: ignore[override]
        def __init__(self, *args, **kwargs):
            self.conf = SimpleNamespace(update=lambda **kw: None)

        def task(self, *args, **kwargs):
            bind = kwargs.get("bind", False)

            def decorator(func):
                return _LocalTask(func, bind=bind)

            return decorator

from src.core.config import settings
from src.core.database import SessionLocal
from src.services.llm_service import LLMAnalysisService
from src.services.persist_service import PersistService
from src.services.url_structuring_service import URLStructuringService
from src.tasks.pipeline import (
    PIPELINE_QUEUE_ROUTES,
    PIPELINE_TASK_NAMES,
    build_deadletter_payload,
    build_dispatch_payload,
    build_extract_payload,
    build_extract_service_request,
    build_llm_payload,
    build_persist_payload,
)

celery_app = Celery(
    "resume_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    worker_prefetch_multiplier=1,
    task_routes=PIPELINE_QUEUE_ROUTES,
)


@celery_app.task(bind=True, max_retries=3)
def analyze_resume_task(self, candidate_id: int):
    """兼容旧入口的单份简历分析任务。"""
    return {"candidate_id": candidate_id, "status": "pending_pipeline"}


@celery_app.task(bind=True, max_retries=3)
def batch_analyze_task(self, batch_id: str, candidate_ids: list, job_id: int = None):
    """兼容旧入口的批量分析任务。"""
    return {
        "batch_id": batch_id,
        "candidate_ids": candidate_ids,
        "job_id": job_id,
        "status": "pending_pipeline",
    }


@celery_app.task(name=PIPELINE_TASK_NAMES["dispatch"], bind=True, max_retries=3)
def dispatch_batch_task(self, batch_id: str, items: list[dict]):
    """批量分发结构化任务。"""
    return build_dispatch_payload(batch_id=batch_id, items=items)


@celery_app.task(name=PIPELINE_TASK_NAMES["extract"], bind=True, max_retries=3)
def extract_resume_task(self, employee_id: str, resume_created_time: str, temp_url: str | None = None):
    """抽取阶段任务入口。"""
    extract_payload = build_extract_payload(
        employee_id=employee_id,
        resume_created_time=resume_created_time,
        temp_url=temp_url,
    )
    service_request = build_extract_service_request(
        extract_payload=extract_payload,
        temp_url=temp_url,
    )

    db = SessionLocal()
    try:
        service = URLStructuringService(db=db)
        # 抽取阶段只负责把 URL 转成文本，后续仍交给 llm/persist 阶段处理。
        if service_request["mode"] == "url":
            resume_text = asyncio.run(
                service.extract_resume_text_from_url(service_request["resume_url"])
            )
        else:
            resume_text = asyncio.run(
                service.extract_resume_text_from_employee(service_request["employee_id"])
            )
    finally:
        db.close()

    return build_llm_payload(extract_payload=extract_payload, text=resume_text)


@celery_app.task(name=PIPELINE_TASK_NAMES["llm"], bind=True, max_retries=3)
def llm_extract_task(self, llm_payload: dict):
    """LLM 抽取阶段任务入口。"""
    db = SessionLocal()
    try:
        service = LLMAnalysisService()
        structured_resume = asyncio.run(
            service.extract_resume_info(llm_payload.get("resume_text", ""))
        )
        return build_persist_payload(
            llm_payload=llm_payload,
            structured_resume=structured_resume,
        )
    except Exception as exc:
        deadletter_task.run(
            payload=llm_payload,
            error_code="E_LLM",
            error_message=str(exc),
        )
        raise
    finally:
        db.close()


@celery_app.task(name=PIPELINE_TASK_NAMES["persist"], bind=True, max_retries=3)
def persist_result_task(self, persist_payload: dict):
    """幂等落库阶段任务入口。"""
    db = SessionLocal()
    try:
        service = PersistService(db)
        return service.persist_structured_resume(persist_payload)
    except Exception as exc:
        deadletter_task.run(
            payload=persist_payload,
            error_code="E_PERSIST",
            error_message=str(exc),
        )
        raise
    finally:
        db.close()


@celery_app.task(name=PIPELINE_TASK_NAMES["deadletter"], bind=True, max_retries=3)
def deadletter_task(self, payload: dict, error_code: str, error_message: str):
    """死信任务入口。"""
    db = SessionLocal()
    try:
        service = PersistService(db)
        service.create_deadletter(
            payload=payload,
            error_code=error_code,
            error_message=error_message,
        )
    finally:
        db.close()

    return build_deadletter_payload(
        payload=payload,
        error_code=error_code,
        error_message=error_message,
    )