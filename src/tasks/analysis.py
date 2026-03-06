"""Celery 异步任务入口。"""

from celery import Celery

from src.core.config import settings
from src.tasks.pipeline import (
    PIPELINE_QUEUE_ROUTES,
    PIPELINE_TASK_NAMES,
    build_deadletter_payload,
    build_dispatch_payload,
    build_extract_payload,
    build_llm_payload,
    build_persist_payload,
)

# 创建 Celery 应用，供离线批处理任务复用。
celery_app = Celery(
    "resume_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# 统一配置任务序列化、时区、超时和队列路由。
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
    # 旧链路仍可能调用这个入口，这里先返回迁移提示，避免直接报错。
    return {"candidate_id": candidate_id, "status": "pending_pipeline"}


@celery_app.task(bind=True, max_retries=3)
def batch_analyze_task(self, batch_id: str, candidate_ids: list, job_id: int = None):
    """兼容旧入口的批量分析任务。"""
    # 旧接口暂时只返回摘要，后续统一切到新的离线批处理链路。
    return {
        "batch_id": batch_id,
        "candidate_ids": candidate_ids,
        "job_id": job_id,
        "status": "pending_pipeline",
    }


@celery_app.task(name=PIPELINE_TASK_NAMES["dispatch"], bind=True, max_retries=3)
def dispatch_batch_task(self, batch_id: str, items: list[dict]):
    """批量分发结构化任务。

    这里只负责把稳定标识整理成抽取阶段载荷，不在队列里传临时 URL。
    """
    return build_dispatch_payload(batch_id=batch_id, items=items)


@celery_app.task(name=PIPELINE_TASK_NAMES["extract"], bind=True, max_retries=3)
def extract_resume_task(self, employee_id: str, resume_created_time: str, temp_url: str | None = None):
    """抽取阶段任务入口。"""
    # Worker 执行时再申请临时 URL，避免 15 分钟链接在排队期间过期。
    return build_extract_payload(
        employee_id=employee_id,
        resume_created_time=resume_created_time,
        temp_url=temp_url,
    )


@celery_app.task(name=PIPELINE_TASK_NAMES["llm"], bind=True, max_retries=3)
def llm_extract_task(self, extract_payload: dict, text: str = ""):
    """LLM 抽取阶段任务入口。"""
    # 这里先返回标准化载荷，后续接入真实 LLM 服务时可直接复用字段结构。
    return build_llm_payload(extract_payload=extract_payload, text=text)


@celery_app.task(name=PIPELINE_TASK_NAMES["persist"], bind=True, max_retries=3)
def persist_result_task(self, llm_payload: dict, structured_resume: dict | None = None):
    """幂等落库阶段任务入口。"""
    # 入库前统一收敛字段，便于后续做幂等校验和事务写入。
    return build_persist_payload(
        llm_payload=llm_payload,
        structured_resume=structured_resume,
    )


@celery_app.task(name=PIPELINE_TASK_NAMES["deadletter"], bind=True, max_retries=3)
def deadletter_task(self, payload: dict, error_code: str, error_message: str):
    """死信任务入口。"""
    # 死信里保留原始上下文，后续才能按 employee_id 精准重试。
    return build_deadletter_payload(
        payload=payload,
        error_code=error_code,
        error_message=error_message,
    )