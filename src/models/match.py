"""MatchResult (匹配结果) 数据模型"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.core.database import Base


class MatchResult(Base):
    """匹配结果表"""
    __tablename__ = "match_results"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(Integer, ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False)
    
    # 匹配评分
    overall_score = Column(Float, nullable=True)  # 总分 0-100
    skill_match_score = Column(Float, nullable=True)  # 技能匹配度
    experience_match_score = Column(Float, nullable=True)  # 经验匹配度
    education_match_score = Column(Float, nullable=True)  # 学历匹配度
    
    # 分析结果
    matched_skills = Column(Text, nullable=True)  # JSON 数组
    missing_skills = Column(Text, nullable=True)  # JSON 数组
    risk_flags = Column(Text, nullable=True)  # JSON 数组，如 ["频繁跳槽", "技能夸大"]
    
    # LLM 生成内容
    summary = Column(Text, nullable=True)  # 一句话总结
    recommendation = Column(Text, nullable=True)  # 推荐理由
    interview_questions = Column(Text, nullable=True)  # JSON 数组，建议的面试问题
    detailed_analysis = Column(Text, nullable=True)  # 详细分析
    
    # 使用的 LLM Provider
    llm_provider = Column(String(50), nullable=True)
    
    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    candidate = relationship("Candidate", back_populates="match_results")
    job = relationship("JobDescription", back_populates="match_results")
