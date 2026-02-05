"""匹配分析 API 路由"""
import json
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.models.candidate import Candidate
from src.models.job import JobDescription
from src.models.match import MatchResult
from src.services.llm_service import LLMAnalysisService
from src.api.schemas.match import (
    MatchRequest,
    MatchResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/match", tags=["Matching"])


@router.post("/analyze", response_model=MatchResponse)
async def analyze_match(
    request: MatchRequest,
    db: Session = Depends(get_db),
):
    """分析候选人与职位的匹配度
    
    根据候选人信息和职位描述，使用 LLM 进行深度匹配分析。
    """
    # 获取候选人
    candidate = db.query(Candidate).filter(Candidate.id == request.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    
    if candidate.status != "completed":
        raise HTTPException(status_code=400, detail="候选人简历分析尚未完成")
    
    # 获取职位
    job = db.query(JobDescription).filter(JobDescription.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="职位不存在")
    
    # 构建候选人信息
    candidate_info = {
        "name": candidate.name,
        "education_level": candidate.education_level,
        "years_of_experience": candidate.years_of_experience,
        "current_position": candidate.current_position,
        "summary": candidate.summary,
        "skills": [
            {"skill_name": s.skill_name, "proficiency_level": s.proficiency_level}
            for s in candidate.skills
        ],
        "work_experiences": [
            {
                "company_name": e.company_name,
                "position": e.position,
                "start_date": e.start_date,
                "end_date": e.end_date,
            }
            for e in candidate.work_experiences
        ],
    }
    
    # 构建职位信息
    job_info = {
        "title": job.title,
        "department": job.department,
        "required_skills": json.loads(job.required_skills) if job.required_skills else [],
        "preferred_skills": json.loads(job.preferred_skills) if job.preferred_skills else [],
        "min_experience": job.min_experience,
        "education_requirement": job.education_requirement,
        "description": job.description,
    }
    
    # LLM 分析
    llm_service = LLMAnalysisService(provider_name=request.llm_provider)
    analysis_result = await llm_service.analyze_jd_match(candidate_info, job_info)
    
    # 保存匹配结果
    match_result = MatchResult(
        candidate_id=candidate.id,
        job_id=job.id,
        overall_score=analysis_result.get("overall_score"),
        skill_match_score=analysis_result.get("skill_match_score"),
        experience_match_score=analysis_result.get("experience_match_score"),
        education_match_score=analysis_result.get("education_match_score"),
        matched_skills=json.dumps(analysis_result.get("matched_skills", []), ensure_ascii=False),
        missing_skills=json.dumps(analysis_result.get("missing_skills", []), ensure_ascii=False),
        risk_flags=json.dumps(analysis_result.get("risk_flags", []), ensure_ascii=False),
        summary=analysis_result.get("summary"),
        recommendation=analysis_result.get("recommendation"),
        interview_questions=json.dumps(analysis_result.get("interview_questions", []), ensure_ascii=False),
        llm_provider=request.llm_provider or "default",
    )
    
    db.add(match_result)
    db.commit()
    db.refresh(match_result)
    
    # 格式化响应
    return MatchResponse(
        match_id=match_result.id,
        candidate_id=match_result.candidate_id,
        job_id=match_result.job_id,
        overall_score=match_result.overall_score,
        skill_match_score=match_result.skill_match_score,
        experience_match_score=match_result.experience_match_score,
        education_match_score=match_result.education_match_score,
        matched_skills=json.loads(match_result.matched_skills) if match_result.matched_skills else [],
        missing_skills=json.loads(match_result.missing_skills) if match_result.missing_skills else [],
        risk_flags=json.loads(match_result.risk_flags) if match_result.risk_flags else [],
        summary=match_result.summary,
        recommendation=match_result.recommendation,
        interview_questions=json.loads(match_result.interview_questions) if match_result.interview_questions else [],
        llm_provider=match_result.llm_provider,
        created_at=match_result.created_at,
    )


@router.get("/results/{candidate_id}", response_model=List[MatchResponse])
async def get_match_results(
    candidate_id: int,
    db: Session = Depends(get_db),
):
    """获取候选人的所有匹配结果"""
    results = db.query(MatchResult).filter(MatchResult.candidate_id == candidate_id).all()
    
    return [
        MatchResponse(
            match_id=r.id,
            candidate_id=r.candidate_id,
            job_id=r.job_id,
            overall_score=r.overall_score,
            skill_match_score=r.skill_match_score,
            experience_match_score=r.experience_match_score,
            education_match_score=r.education_match_score,
            matched_skills=json.loads(r.matched_skills) if r.matched_skills else [],
            missing_skills=json.loads(r.missing_skills) if r.missing_skills else [],
            risk_flags=json.loads(r.risk_flags) if r.risk_flags else [],
            summary=r.summary,
            recommendation=r.recommendation,
            interview_questions=json.loads(r.interview_questions) if r.interview_questions else [],
            llm_provider=r.llm_provider,
            created_at=r.created_at,
        )
        for r in results
    ]
