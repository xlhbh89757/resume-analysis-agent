"""简历相关 API 路由"""
import shutil
import uuid
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import get_db
from src.models.candidate import Candidate, WorkExperience, Skill, ProjectExperience
from src.services.document_parser import DocumentParser
from src.services.llm_service import LLMAnalysisService
from src.services.vector_service import VectorService
from src.api.schemas.resume import (
    ResumeUploadResponse,
    CandidateResponse,
    CandidateListResponse,
    CandidateSearchRequest,
    CandidateSearchResponse,
    SearchResultItem,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/resumes", tags=["Resumes"])

# 初始化服务
document_parser = DocumentParser()


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    auto_analyze: bool = True,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """上传简历
    
    上传 PDF 或 DOCX 格式的简历文件，系统会自动解析并提取信息。
    
    Args:
        file: 简历文件 (PDF/DOCX)
        auto_analyze: 是否自动进行 LLM 分析
        
    Returns:
        上传结果，包含候选人 ID 和处理状态
    """
    # 验证文件类型
    allowed_extensions = ['.pdf', '.docx', '.doc']
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_ext}，仅支持 {allowed_extensions}"
        )
    
    # 验证文件大小
    file_content = await file.read()
    if len(file_content) > settings.max_upload_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大，最大支持 {settings.max_upload_size // 1024 // 1024}MB"
        )
    
    # 保存文件
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = upload_dir / unique_filename
    
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)
    
    # 解析文档
    try:
        resume_text = document_parser.parse(str(file_path))
    except Exception as e:
        logger.error(f"文档解析失败: {e}")
        raise HTTPException(status_code=400, detail=f"文档解析失败: {str(e)}")
    
    # 创建候选人记录
    candidate = Candidate(
        resume_file_path=str(file_path),
        resume_text=resume_text,
        status="analyzing" if auto_analyze else "pending"
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    
    # 异步分析任务
    task_id = None
    if auto_analyze and background_tasks:
        task_id = str(uuid.uuid4())
        background_tasks.add_task(
            analyze_resume_background,
            candidate.id,
            resume_text
        )
    
    return ResumeUploadResponse(
        candidate_id=candidate.id,
        status="analyzing" if auto_analyze else "uploaded",
        task_id=task_id,
        message="简历上传成功，正在分析中" if auto_analyze else "简历上传成功"
    )


async def analyze_resume_background(candidate_id: int, resume_text: str):
    """后台分析简历任务"""
    from src.core.database import SessionLocal
    
    db = SessionLocal()
    try:
        # LLM 分析
        llm_service = LLMAnalysisService()
        extracted_info = await llm_service.extract_resume_info(resume_text)
        
        # 更新候选人信息
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            logger.error(f"Candidate not found: {candidate_id}")
            return
        
        candidate.name = extracted_info.get("name")
        candidate.email = extracted_info.get("email")
        candidate.phone = extracted_info.get("phone")
        candidate.education_level = extracted_info.get("education_level")
        candidate.years_of_experience = extracted_info.get("years_of_experience")
        candidate.current_position = extracted_info.get("current_position")
        candidate.summary = extracted_info.get("summary")
        
        # 添加工作经历
        for exp in extracted_info.get("work_experiences", []):
            work_exp = WorkExperience(
                candidate_id=candidate.id,
                company_name=exp.get("company_name"),
                position=exp.get("position"),
                start_date=exp.get("start_date"),
                end_date=exp.get("end_date"),
                responsibilities=str(exp.get("responsibilities", [])),
            )
            db.add(work_exp)
        
        # 添加项目经验
        for proj in extracted_info.get("project_experiences", []):
            import json
            project_exp = ProjectExperience(
                candidate_id=candidate.id,
                project_name=proj.get("project_name"),
                role=proj.get("role"),
                start_date=proj.get("start_date"),
                end_date=proj.get("end_date"),
                description=proj.get("description"),
                technologies=json.dumps(proj.get("technologies", []), ensure_ascii=False),
                achievements=json.dumps(proj.get("achievements", []), ensure_ascii=False),
            )
            db.add(project_exp)
        
        # 添加技能
        for skill in extracted_info.get("skills", []):
            skill_obj = Skill(
                candidate_id=candidate.id,
                skill_name=skill.get("skill_name", ""),
                skill_category=skill.get("skill_category"),
                proficiency_level=skill.get("proficiency_level"),
            )
            db.add(skill_obj)
        
        candidate.status = "completed"
        db.commit()
        
        # 添加向量索引
        try:
            vector_service = VectorService()
            summary_text = candidate.summary or resume_text[:500]
            await vector_service.add_candidate_vector(
                candidate_id=candidate.id,
                text=summary_text,
                metadata={
                    "name": candidate.name,
                    "summary": candidate.summary,
                    "current_position": candidate.current_position,
                    "years_of_experience": candidate.years_of_experience,
                    "education_level": candidate.education_level,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to add vector: {e}")
        
        logger.info(f"Resume analysis completed: candidate_id={candidate_id}")
        
    except Exception as e:
        logger.error(f"Resume analysis failed: {e}")
        try:
            candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
            if candidate:
                candidate.status = "failed"
                db.commit()
        except:
            pass
    finally:
        db.close()


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
):
    """获取候选人详情"""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    
    return candidate


@router.get("/", response_model=CandidateListResponse)
async def list_candidates(
    skip: int = 0,
    limit: int = 20,
    status: str = None,
    db: Session = Depends(get_db),
):
    """获取候选人列表"""
    query = db.query(Candidate)
    
    if status:
        query = query.filter(Candidate.status == status)
    
    total = query.count()
    candidates = query.order_by(Candidate.created_at.desc()).offset(skip).limit(limit).all()
    
    return CandidateListResponse(
        total=total,
        items=candidates
    )


@router.post("/search", response_model=CandidateSearchResponse)
async def search_candidates(
    request: CandidateSearchRequest,
):
    """语义搜索候选人"""
    vector_service = VectorService()
    
    results = await vector_service.search_candidates(
        query=request.query,
        top_k=request.top_k,
        filters=request.filters,
    )
    
    # 格式化结果
    items = [
        SearchResultItem(
            candidate_id=r["candidate_id"],
            similarity_score=r["similarity_score"],
            name=r.get("name"),
            summary=r.get("summary"),
            current_position=r.get("current_position"),
            years_of_experience=r.get("years_of_experience"),
        )
        for r in results
    ]
    
    return CandidateSearchResponse(
        results=items,
        total=len(items)
    )


@router.delete("/{candidate_id}")
async def delete_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
):
    """删除候选人"""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    
    # 删除文件
    if candidate.resume_file_path:
        file_path = Path(candidate.resume_file_path)
        if file_path.exists():
            file_path.unlink()
    
    # 删除向量
    try:
        vector_service = VectorService()
        await vector_service.delete_candidate_vector(candidate_id)
    except Exception as e:
        logger.warning(f"Failed to delete vector: {e}")
    
    # 删除数据库记录
    db.delete(candidate)
    db.commit()
    
    return {"message": "删除成功"}
