"""异步任务模块。"""

from importlib import import_module

__all__ = [
    "celery_app",
    "analyze_resume_task",
    "batch_analyze_task",
]


def __getattr__(name: str):
    """按需加载 Celery 任务，避免普通单测在导入阶段依赖 celery。"""
    if name in __all__:
        module = import_module("src.tasks.analysis")
        return getattr(module, name)
    raise AttributeError(f"module 'src.tasks' has no attribute {name!r}")