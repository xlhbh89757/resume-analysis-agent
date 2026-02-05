"""Celery 异步任务"""
# 注意：完整的 Celery 实现需要在 Phase 4 中完成
# 这里提供基础框架

from celery import Celery
from src.core.config import settings

# 创建 Celery 应用
celery_app = Celery(
    "resume_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery 配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 分钟超时
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, max_retries=3)
def analyze_resume_task(self, candidate_id: int):
    """异步分析简历任务
    
    这是一个占位实现，完整版本将在 Phase 4 中实现。
    当前版本使用 FastAPI BackgroundTasks 进行异步处理。
    """
    # TODO: 实现完整的 Celery 任务
    pass


@celery_app.task(bind=True, max_retries=3)
def batch_analyze_task(self, batch_id: str, candidate_ids: list, job_id: int = None):
    """批量分析任务
    
    占位实现。
    """
    # TODO: 实现批量分析逻辑
    pass
