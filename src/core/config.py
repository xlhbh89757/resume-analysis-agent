"""Resume Agent - 核心配置模块"""
from pydantic_settings import BaseSettings
from typing import Literal, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    app_name: str = "Resume Analysis Agent"
    debug: bool = False
    api_prefix: str = "/api/v1"
    
    # 数据库配置
    database_url: str = "postgresql://postgres:postgres@localhost:5432/resume_agent"
    
    # Redis 配置
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    
    # Qdrant 配置
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "candidate_resumes"
    
    # LLM 配置
    llm_provider: Literal["local", "openai", "claude"] = "local"
    
    # 本地模型配置
    local_model_path: str = "/path/to/models/Qwen2.5-14B-Instruct"
    local_model_gpu_memory_utilization: float = 0.9
    local_model_tensor_parallel_size: int = 1
    
    # OpenAI 配置
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    openai_base_url: str = "https://api.openai.com/v1"
    
    # Claude 配置
    claude_api_key: Optional[str] = None
    claude_model: str = "claude-3-5-sonnet-20241022"
    
    # Embedding 模型配置
    embedding_model_name: str = "BAAI/bge-m3"
    embedding_dimension: int = 1024
    
    # 文件存储配置
    upload_dir: str = "./uploads"
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
