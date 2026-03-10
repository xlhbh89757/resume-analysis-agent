"""Resume Agent 核心配置。"""

from functools import lru_cache
from typing import Literal, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置。"""

    # Application
    app_name: str = "Resume Analysis Agent"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = "mysql+pymysql://root:root@localhost:3306/resume_agent?charset=utf8mb4"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "candidate_resumes"

    # LLM
    llm_provider: Literal["local", "openai", "claude"] = "local"
    local_model_path: str = "/path/to/models/Qwen2.5-14B-Instruct"
    local_model_gpu_memory_utilization: float = 0.9
    local_model_tensor_parallel_size: int = 1
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    openai_base_url: str = "https://api.openai.com/v1"
    claude_api_key: Optional[str] = None
    claude_model: str = "claude-3-5-sonnet-20241022"

    # Embedding
    embedding_model_name: str = "BAAI/bge-m3"
    embedding_dimension: int = 1024

    # File Storage
    upload_dir: str = "./uploads"
    max_upload_size: int = 10 * 1024 * 1024  # 10MB

    # Resume Source API
    resume_source_api_base_url: str = ""
    resume_source_api_token: Optional[str] = None
    resume_source_api_timeout: int = 30

    # OBS
    obs_access_key: Optional[str] = None
    obs_secret_key: Optional[str] = None
    obs_bucket: Optional[str] = None
    obs_host: Optional[str] = None
    obs_url_expire_seconds: int = 900

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value: object) -> object:
        """兼容外部环境中用 release/production 表示非调试模式的写法。"""
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"release", "prod", "production"}:
                return False
        return value

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """返回缓存后的配置实例。"""
    return Settings()


settings = get_settings()
