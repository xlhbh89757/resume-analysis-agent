"""异步任务模块"""
from src.tasks.analysis import celery_app, analyze_resume_task, batch_analyze_task

__all__ = [
    "celery_app",
    "analyze_resume_task",
    "batch_analyze_task",
]
