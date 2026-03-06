"""Candidate (候选人) 数据模型"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.core.database import Base


class Candidate(Base):
    """候选人表"""
    __tablename__ = "candidates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    phone = Column(String(50), nullable=True)
    
    # 基础信息
    education_level = Column(String(50), nullable=True)  # 本科/硕士/博士
    years_of_experience = Column(Integer, nullable=True)
    current_position = Column(String(255), nullable=True)
    expected_salary = Column(Integer, nullable=True)
    
    # 文件信息
    resume_file_path = Column(Text, nullable=True)
    resume_text = Column(Text, nullable=True)
    
    # 分析结果摘要
    summary = Column(Text, nullable=True)
    
    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    status = Column(String(20), default="pending")  # pending, analyzing, completed, failed
    
    # 关系
    work_experiences = relationship("WorkExperience", back_populates="candidate", cascade="all, delete-orphan")
    project_experiences = relationship("ProjectExperience", back_populates="candidate", cascade="all, delete-orphan")
    skills = relationship("Skill", back_populates="candidate", cascade="all, delete-orphan")
    match_results = relationship("MatchResult", back_populates="candidate", cascade="all, delete-orphan")


class WorkExperience(Base):
    """工作经历表"""
    __tablename__ = "work_experiences"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    
    company_name = Column(String(255), nullable=True)
    position = Column(String(255), nullable=True)
    start_date = Column(String(20), nullable=True)  # YYYY-MM 格式
    end_date = Column(String(20), nullable=True)  # YYYY-MM 格式或 null（至今）
    duration_months = Column(Integer, nullable=True)
    responsibilities = Column(Text, nullable=True)  # JSON 格式
    achievements = Column(Text, nullable=True)  # JSON 格式
    
    # 关系
    candidate = relationship("Candidate", back_populates="work_experiences")


class ProjectExperience(Base):
    """项目经验表"""
    __tablename__ = "project_experiences"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    
    project_name = Column(String(255), nullable=True)
    role = Column(String(100), nullable=True)  # 项目角色
    start_date = Column(String(20), nullable=True)  # YYYY-MM 格式
    end_date = Column(String(20), nullable=True)  # YYYY-MM 格式或 null
    description = Column(Text, nullable=True)  # 项目描述
    technologies = Column(Text, nullable=True)  # JSON 格式的技术栈
    responsibilities = Column(Text, nullable=True)  # JSON 格式的项目职责原文
    achievements = Column(Text, nullable=True)  # JSON 格式的项目成果
    
    # 关系
    candidate = relationship("Candidate", back_populates="project_experiences")


class Skill(Base):
    """技能表"""
    __tablename__ = "skills"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    
    skill_name = Column(String(100), nullable=False)
    skill_category = Column(String(50), nullable=True)  # 技术/软技能/语言/工具
    proficiency_level = Column(String(20), nullable=True)  # 了解/熟悉/精通
    years = Column(Integer, nullable=True)
    
    # 关系
    candidate = relationship("Candidate", back_populates="skills")
