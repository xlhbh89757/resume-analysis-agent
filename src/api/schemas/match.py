"""API Pydantic Schemas - 匹配相关"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class MatchRequest(BaseModel):
    """匹配分析请求"""
    candidate_id: int = Field(..., description="候选人 ID")
    job_id: int = Field(..., description="职位 ID")
    llm_provider: Optional[str] = Field(None, description="指定 LLM Provider: local, openai, claude")


class MatchResponse(BaseModel):
    """匹配分析响应"""
    match_id: int
    candidate_id: int
    job_id: int
    
    # 评分
    overall_score: Optional[float] = None
    skill_match_score: Optional[float] = None
    experience_match_score: Optional[float] = None
    education_match_score: Optional[float] = None
    
    # 分析结果
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    risk_flags: List[str] = []
    
    # LLM 生成内容
    summary: Optional[str] = None
    recommendation: Optional[str] = None
    interview_questions: List[str] = []
    
    # 使用的 Provider
    llm_provider: Optional[str] = None
    
    created_at: datetime
    
    class Config:
        from_attributes = True


class JobCreateRequest(BaseModel):
    """创建职位请求"""
    title: str = Field(..., description="职位名称")
    department: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list, description="必需技能")
    preferred_skills: List[str] = Field(default_factory=list, description="优先技能")
    min_experience: Optional[int] = Field(None, ge=0, description="最低工作年限")
    max_experience: Optional[int] = Field(None, ge=0, description="最高工作年限")
    education_requirement: Optional[str] = None
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None


class JobResponse(BaseModel):
    """职位响应"""
    id: int
    title: str
    department: Optional[str] = None
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    min_experience: Optional[int] = None
    max_experience: Optional[int] = None
    education_requirement: Optional[str] = None
    description: Optional[str] = None
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class BatchAnalyzeRequest(BaseModel):
    """批量分析请求"""
    job_id: Optional[int] = Field(None, description="职位 ID，如果提供则进行 JD 匹配")


class BatchAnalyzeResponse(BaseModel):
    """批量分析响应"""
    batch_id: str
    total_files: int
    status: str = "processing"
    estimated_completion_time: Optional[datetime] = None


class BatchStatusResponse(BaseModel):
    """批量任务状态响应"""
    batch_id: str
    status: str  # queued, processing, completed, failed
    progress: dict
    results: Optional[List[dict]] = None
