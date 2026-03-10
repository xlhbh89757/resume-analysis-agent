"""Celery 异步任务入口。"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx

try:
    from celery import Celery
except ModuleNotFoundError:
    class _LocalTask:
        def __init__(self, func, bind: bool = False):
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
    return {"candidate_id": candidate_id, "status": "pending_pipeline"}


@celery_app.task(bind=True, max_retries=3)
def batch_analyze_task(self, batch_id: str, candidate_ids: list, job_id: int = None):
    return {
        "batch_id": batch_id,
        "candidate_ids": candidate_ids,
        "job_id": job_id,
        "status": "pending_pipeline",
    }


@celery_app.task(name=PIPELINE_TASK_NAMES["dispatch"], bind=True, max_retries=3)
def dispatch_batch_task(self, batch_id: str, items: list[dict]):
    payload = build_dispatch_payload(batch_id=batch_id, items=items)
    for item in payload["items"]:
        if hasattr(extract_resume_task, "delay"):
            extract_resume_task.delay(**item)
        else:
            extract_resume_task.run(**item)
    return payload


def _refresh_resume_url(
    service: URLStructuringService,
    service_request: dict[str, str],
) -> str:
    """下载 403 时刷新简历访问链接。"""
    if service_request["mode"] == "filekey":
        return service.source_client.build_temp_url_from_filekey(
            service_request["filekey"]
        )["temp_url"]

    refreshed = asyncio.run(
        service.source_client.get_temp_url(
            service_request["source_type"],
            service_request["source_id"],
        )
    )
    return refreshed["temp_url"]


def _classify_extract_error(exc: Exception) -> str:
    if isinstance(exc, RuntimeError) and str(exc).startswith("E_DOWNLOAD"):
        return "E_DOWNLOAD"
    if isinstance(exc, httpx.HTTPStatusError):
        return "E_DOWNLOAD"
    if isinstance(exc, httpx.HTTPError):
        return "E_DOWNLOAD"
    if isinstance(exc, ValueError):
        return "E_PARSE"
    return "E_EXTRACT"


@celery_app.task(name=PIPELINE_TASK_NAMES["extract"], bind=True, max_retries=3)
def extract_resume_task(
    self,
    source_type: str,
    source_id: str,
    resume_created_time: str,
    temp_url: str | None = None,
    filekey: str | None = None,
    enqueue: bool = True,
):
    """抽取阶段任务入口。"""
    extract_payload = build_extract_payload(
        source_type=source_type,
        source_id=source_id,
        resume_created_time=resume_created_time,
        temp_url=temp_url,
        filekey=filekey,
    )
    service_request = build_extract_service_request(
        extract_payload=extract_payload,
        temp_url=temp_url,
    )

    db = SessionLocal()
    try:
        service = URLStructuringService(db=db)
        try:
            if service_request["mode"] == "url":
                resume_url = service_request["resume_url"]
            elif service_request["mode"] == "filekey":
                resume_url = service.source_client.build_temp_url_from_filekey(
                    service_request["filekey"]
                )["temp_url"]
            else:
                resume_text = asyncio.run(
                    service.extract_resume_text_from_source(
                        service_request["source_type"],
                        service_request["source_id"],
                        service_request.get("filekey"),
                    )
                )
            if service_request["mode"] in {"url", "filekey"}:
                try:
                    resume_text = asyncio.run(service.extract_resume_text_from_url(resume_url))
                except httpx.HTTPStatusError as exc:
                    if exc.response is None or exc.response.status_code != 403:
                        raise
                    refreshed_url = _refresh_resume_url(service, service_request)
                    try:
                        resume_text = asyncio.run(service.extract_resume_text_from_url(refreshed_url))
                    except httpx.HTTPStatusError as retry_exc:
                        if retry_exc.response is not None and retry_exc.response.status_code == 403:
                            raise RuntimeError("E_DOWNLOAD: temp url expired after refresh") from retry_exc
                        raise
        except Exception as exc:
            deadletter_task.run(
                payload=extract_payload,
                error_code=_classify_extract_error(exc),
                error_message=str(exc),
            )
            raise
    finally:
        db.close()

    llm_payload = build_llm_payload(extract_payload=extract_payload, text=resume_text)
    if enqueue and hasattr(llm_extract_task, "delay"):
        llm_extract_task.delay(llm_payload)
        return {
            "status": "queued_llm",
            "source_type": source_type,
            "source_id": source_id,
            "resume_created_time": resume_created_time,
        }
    return llm_payload


@celery_app.task(name=PIPELINE_TASK_NAMES["llm"], bind=True, max_retries=3)
def llm_extract_task(self, llm_payload: dict, enqueue: bool = True):
    db = SessionLocal()
    try:
        service = LLMAnalysisService()
        structured_resume = asyncio.run(
            service.extract_resume_info(llm_payload.get("resume_text", ""))
        )
        persist_payload = build_persist_payload(
            llm_payload=llm_payload,
            structured_resume=structured_resume,
        )
        if enqueue and hasattr(persist_result_task, "delay"):
            persist_result_task.delay(persist_payload)
            return {
                "status": "queued_persist",
                "source_type": llm_payload["source_type"],
                "source_id": llm_payload["source_id"],
                "resume_created_time": llm_payload["resume_created_time"],
            }
        return persist_payload
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
