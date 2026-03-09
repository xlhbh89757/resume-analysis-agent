"""Candidate 相关数据模型。"""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.core.database import Base


class Candidate(Base):
    """候选人表。"""

    __tablename__ = "candidates"
    __table_args__ = {"comment": "候选人主表"}

    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    name = Column(String(100), nullable=True, comment="姓名")
    email = Column(String(255), unique=True, index=True, nullable=True, comment="邮箱")
    phone = Column(String(50), nullable=True, comment="手机号")

    # 外部业务标识允许共存，方便同一候选人跨流程流转后继续复用。
    employee_id = Column(String(100), nullable=True, index=True, comment="在职员工工号")
    entrant_id = Column(String(100), nullable=True, index=True, comment="待入职人员标识")
    submit_candidate_id = Column(String(100), nullable=True, index=True, comment="报备候选人标识")

    education_level = Column(String(50), nullable=True, comment="学历层级")
    years_of_experience = Column(Integer, nullable=True, comment="工作年限")
    current_position = Column(String(255), nullable=True, comment="当前职位")
    expected_salary = Column(Integer, nullable=True, comment="期望薪资")

    resume_file_path = Column(Text, nullable=True, comment="简历文件路径")
    resume_text = Column(Text, nullable=True, comment="简历原文")
    summary = Column(Text, nullable=True, comment="简历摘要")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
    status = Column(String(20), default="pending", comment="处理状态")

    work_experiences = relationship(
        "WorkExperience",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )
    project_experiences = relationship(
        "ProjectExperience",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )
    skills = relationship(
        "Skill",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )
    match_results = relationship(
        "MatchResult",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )


class WorkExperience(Base):
    """工作经历表。"""

    __tablename__ = "work_experiences"
    __table_args__ = {"comment": "工作经历表"}

    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        comment="候选人ID",
    )

    company_name = Column(String(255), nullable=True, comment="公司名称")
    position = Column(String(255), nullable=True, comment="岗位名称")
    start_date = Column(String(20), nullable=True, comment="开始日期")
    end_date = Column(String(20), nullable=True, comment="结束日期")
    duration_months = Column(Integer, nullable=True, comment="持续月数")
    responsibilities = Column(Text, nullable=True, comment="职责原文JSON")
    achievements = Column(Text, nullable=True, comment="成果原文JSON")

    candidate = relationship("Candidate", back_populates="work_experiences")


class ProjectExperience(Base):
    """项目经历表。"""

    __tablename__ = "project_experiences"
    __table_args__ = {"comment": "项目经历表"}

    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        comment="候选人ID",
    )

    project_name = Column(String(255), nullable=True, comment="项目名称")
    role = Column(String(100), nullable=True, comment="项目角色")
    start_date = Column(String(20), nullable=True, comment="开始日期")
    end_date = Column(String(20), nullable=True, comment="结束日期")
    description = Column(Text, nullable=True, comment="项目描述")
    technologies = Column(Text, nullable=True, comment="技术栈JSON")
    responsibilities = Column(Text, nullable=True, comment="项目职责原文JSON")
    achievements = Column(Text, nullable=True, comment="项目成果原文JSON")

    candidate = relationship("Candidate", back_populates="project_experiences")


class Skill(Base):
    """技能表。"""

    __tablename__ = "skills"
    __table_args__ = {"comment": "技能表"}

    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        comment="候选人ID",
    )

    skill_name = Column(String(100), nullable=False, comment="技能名称")
    skill_category = Column(String(50), nullable=True, comment="技能类别")
    proficiency_level = Column(String(20), nullable=True, comment="熟练度")
    years = Column(Integer, nullable=True, comment="使用年限")

    candidate = relationship("Candidate", back_populates="skills")
