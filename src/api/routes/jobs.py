"""职位管理 API 路由"""
import json
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.models.job import JobDescription
from src.services.llm_service import LLMAnalysisService
from src.api.schemas.match import (
    JobCreateRequest,
    JobResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/",response_model=JobResponse)
async def create_job(
    request: JobCreateRequest,
    db: Session = Depends(get_db),
):
    """创建职位"""
    job = JobDescription(
        title=request.title,
        department=request.department,
        required_skills=json.dumps(request.required_skills, ensure_ascii=False),
        preferred_skills=json.dumps(request.preferred_skills, ensure_ascii=False),
        min_experience=request.min_experience,
        max_experience=request.max_experience,
        education_requirement=request.education_requirement,
        description=request.description,
        responsibilities=request.responsibilities,
        location=request.location,
        salary_range=request.salary_range,
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    return JobResponse(
        id=job.id,
        title=job.title,
        department=job.department,
        required_skills=json.loads(job.required_skills) if job.required_skills else [],
        preferred_skills=json.loads(job.preferred_skills) if job.preferred_skills else [],
        min_experience=job.min_experience,
        max_experience=job.max_experience,
        education_requirement=job.education_requirement,
        description=job.description,
        status=job.status,
        created_at=job.created_at,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: Session = Depends(get_db),
):
    """获取职位详情"""
    job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="职位不存在")
    
    return JobResponse(
        id=job.id,
        title=job.title,
        department=job.department,
        required_skills=json.loads(job.required_skills) if job.required_skills else [],
        preferred_skills=json.loads(job.preferred_skills) if job.preferred_skills else [],
        min_experience=job.min_experience,
        max_experience=job.max_experience,
        education_requirement=job.education_requirement,
        description=job.description,
        status=job.status,
        created_at=job.created_at,
    )


@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """获取职位列表"""
    jobs = db.query(JobDescription).order_by(JobDescription.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        JobResponse(
            id=j.id,
            title=j.title,
            department=j.department,
            required_skills=json.loads(j.required_skills) if j.required_skills else [],
            preferred_skills=json.loads(j.preferred_skills) if j.preferred_skills else [],
            min_experience=j.min_experience,
            max_experience=j.max_experience,
            education_requirement=j.education_requirement,
            description=j.description,
            status=j.status,
            created_at=j.created_at,
        )
        for j in jobs
    ]


@router.post("/parse", response_model=dict)
async def parse_jd_text(
    payload: dict = Body(..., example={"text": "JD content here"}),
):
    """解析 JD 文本提取结构化信息
    
    使用 AI 从职位描述文本中自动提取结构化信息,包括:
    - 职位名称、部门、地点
    - 经验要求、学历要求
    - 必需技能、优先技能
    - 职位描述
    """
    text = payload.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    llm_service = LLMAnalysisService()
    result = await llm_service.extract_jd_info(text)
    return result
