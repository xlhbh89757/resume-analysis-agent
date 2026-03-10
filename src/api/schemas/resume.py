"""简历相关 API Schema。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class WorkExperienceSchema(BaseModel):
    company_name: Optional[str] = None
    position: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_months: Optional[int] = None
    responsibilities: Optional[str] = None
    achievements: Optional[str] = None

    class Config:
        from_attributes = True


class SkillSchema(BaseModel):
    skill_name: str
    skill_category: Optional[str] = None
    proficiency_level: Optional[str] = None

    class Config:
        from_attributes = True


class ProjectExperienceSchema(BaseModel):
    project_name: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    technologies: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    achievements: Optional[List[str]] = None

    @field_validator("technologies", "responsibilities", "achievements", mode="before")
    @classmethod
    def parse_json_list(cls, value: Any) -> Optional[List[str]]:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return []
        if isinstance(value, list):
            return value
        return None

    class Config:
        from_attributes = True


class ResumeUploadResponse(BaseModel):
    candidate_id: int
    status: str = Field(..., description="uploaded, analyzing, completed, failed")
    task_id: Optional[str] = Field(None, description="异步任务ID")
    message: str = "简历上传成功"


class CandidateResponse(BaseModel):
    id: int
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    employee_id: Optional[str] = None
    entrant_id: Optional[str] = None
    submit_candidate_id: Optional[str] = None
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
    total: int
    items: List[CandidateResponse]


class CandidateSearchRequest(BaseModel):
    query: str = Field(..., description="自然语言查询")
    top_k: int = Field(10, ge=1, le=100, description="返回数量")
    filters: Optional[dict] = Field(None, description="过滤条件")


class SearchResultItem(BaseModel):
    candidate_id: int
    similarity_score: float
    name: Optional[str] = None
    summary: Optional[str] = None
    current_position: Optional[str] = None
    years_of_experience: Optional[int] = None


class CandidateSearchResponse(BaseModel):
    results: List[SearchResultItem]
    total: int


class ResumeUrlStructureRequest(BaseModel):
    resume_url: str


class EmployeeResumeStructureRequest(BaseModel):
    employee_id: str
    resume_created_time: str
    filekey: Optional[str] = None


class SourceResumeStructureRequest(BaseModel):
    source_type: Literal["employee", "submit_candidate", "entrant"]
    source_id: str
    resume_created_time: str
    filekey: Optional[str] = None


class ResumeStructureResponse(BaseModel):
    status: str
    candidate_id: Optional[int] = None
    idempotency_key: Optional[str] = None
    employee_id: Optional[str] = None
    entrant_id: Optional[str] = None
    submit_candidate_id: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    resume_created_time: Optional[str] = None
    resume_url: Optional[str] = None
    structured_resume: dict = Field(default_factory=dict)


class PendingResumeItemResponse(BaseModel):
    source_type: Literal["employee", "submit_candidate", "entrant"]
    source_id: str
    resume_created_time: str
    filekey: Optional[str] = None


class PendingResumeListResponse(BaseModel):
    items: List[PendingResumeItemResponse]
    next_cursor: Optional[str] = None
