"""JobDescription (职位描述) 数据模型"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.core.database import Base


class JobDescription(Base):
    """职位描述表"""
    __tablename__ = "job_descriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    department = Column(String(100), nullable=True)
    
    # 技能要求
    required_skills = Column(Text, nullable=True)  # JSON 数组
    preferred_skills = Column(Text, nullable=True)  # JSON 数组
    
    # 经验要求
    min_experience = Column(Integer, nullable=True)
    max_experience = Column(Integer, nullable=True)
    
    # 学历要求
    education_requirement = Column(String(50), nullable=True)
    
    # 详细描述
    description = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)
    
    # 其他信息
    location = Column(String(100), nullable=True)
    salary_range = Column(String(100), nullable=True)
    
    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    status = Column(String(20), default="active")  # active, closed
    
    # 关系
    match_results = relationship("MatchResult", back_populates="job", cascade="all, delete-orphan")
