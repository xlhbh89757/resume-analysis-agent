from src.api.routes.resume import router as resume_router
from src.api.routes.match import router as match_router
from src.api.routes.jobs import router as jobs_router
from src.api.routes.health import router as health_router

__all__ = [
    "resume_router",
    "match_router",
    "jobs_router",
    "health_router",
]
