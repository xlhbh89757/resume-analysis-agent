"""API Pydantic Schemas - 简历相关"""
import json
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime


class WorkExperienceSchema(BaseModel):
    """工作经历"""
    company_name: Optional[str] = None
    position: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_months: Optional[int] = None
    responsibilities: Optional[str] = None  # 存储为字符串
    
    class Config:
        from_attributes = True


class SkillSchema(BaseModel):
    """技能"""
    skill_name: str
    skill_category: Optional[str] = None
    proficiency_level: Optional[str] = None
    
    class Config:
        from_attributes = True


class ProjectExperienceSchema(BaseModel):
    """项目经验"""
    project_name: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    technologies: Optional[List[str]] = None
    achievements: Optional[List[str]] = None
    
    @field_validator('technologies', 'achievements', mode='before')
    @classmethod
    def parse_json_list(cls, v: Any) -> Optional[List[str]]:
        """解析 JSON 字符串为列表"""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        if isinstance(v, list):
            return v
        return None
    
    class Config:
        from_attributes = True


class ResumeUploadResponse(BaseModel):
    """简历上传响应"""
    candidate_id: int
    status: str = Field(..., description="状态: uploaded, analyzing, completed, failed")
    task_id: Optional[str] = Field(None, description="异步任务 ID")
    message: str = "简历上传成功"


class CandidateResponse(BaseModel):
    """候选人详情响应"""
    id: int
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    education_level: Optional[str] = None
    years_of_experience: Optional[int] = None
    current_position: Optional[str] = None
    summary: Optional[str] = None
    status: str
    created_at: datetime
    work_experiences: List[WorkExperienceSchema] = []
    project_experiences: List[ProjectExperienceSchema] = []
    skills: List[SkillSchema] = []
    
    class Config:
        from_attributes = True


class CandidateListResponse(BaseModel):
    """候选人列表响应"""
    total: int
    items: List[CandidateResponse]


class CandidateSearchRequest(BaseModel):
    """语义搜索请求"""
    query: str = Field(..., description="自然语言查询")
    top_k: int = Field(10, ge=1, le=100, description="返回数量")
    filters: Optional[dict] = Field(None, description="过滤条件")


class SearchResultItem(BaseModel):
    """搜索结果项"""
    candidate_id: int
    similarity_score: float
    name: Optional[str] = None
    summary: Optional[str] = None
    current_position: Optional[str] = None
    years_of_experience: Optional[int] = None


class CandidateSearchResponse(BaseModel):
    """搜索响应"""
    results: List[SearchResultItem]
    total: int
