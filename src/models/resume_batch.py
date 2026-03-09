"""离线简历批处理治理模型。"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.core.database import Base


class ResumeStructBatch(Base):
    """简历结构化批次表。"""

    __tablename__ = "resume_struct_batches"
    __table_args__ = {"comment": "简历结构化批次表"}

    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    batch_id = Column(String(100), unique=True, nullable=False, index=True, comment="批次唯一标识")
    total_count = Column(Integer, nullable=False, default=0, comment="批次总数")
    success_count = Column(Integer, nullable=False, default=0, comment="成功数量")
    failed_count = Column(Integer, nullable=False, default=0, comment="失败数量")
    skipped_count = Column(Integer, nullable=False, default=0, comment="跳过数量")
    status = Column(String(20), nullable=False, default="created", comment="批次状态")
    started_at = Column(DateTime(timezone=True), nullable=True, comment="开始时间")
    finished_at = Column(DateTime(timezone=True), nullable=True, comment="结束时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    # 一个批次聚合多条结构化任务，用于汇总进度和执行结果。
    tasks = relationship(
        "ResumeStructTask",
        back_populates="batch",
        cascade="all, delete-orphan",
    )


class ResumeStructTask(Base):
    """简历结构化任务表。"""

    __tablename__ = "resume_struct_tasks"
    __table_args__ = {"comment": "简历结构化任务表"}

    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    batch_id = Column(
        Integer,
        ForeignKey("resume_struct_batches.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属批次ID",
    )
    source_type = Column(String(50), nullable=False, index=True, comment="来源类型")
    source_id = Column(String(100), nullable=False, index=True, comment="来源业务ID")
    resume_created_time = Column(String(50), nullable=False, comment="简历创建时间")
    idempotency_key = Column(String(255), unique=True, nullable=False, index=True, comment="幂等键")
    status = Column(String(20), nullable=False, default="queued", comment="任务状态")
    attempt_count = Column(Integer, nullable=False, default=0, comment="重试次数")
    error_code = Column(String(50), nullable=True, comment="错误码")
    error_message = Column(Text, nullable=True, comment="错误信息")
    llm_tokens_in = Column(Integer, nullable=True, comment="LLM输入Token数")
    llm_tokens_out = Column(Integer, nullable=True, comment="LLM输出Token数")
    llm_cost = Column(String(50), nullable=True, comment="LLM成本")
    started_at = Column(DateTime(timezone=True), nullable=True, comment="开始时间")
    finished_at = Column(DateTime(timezone=True), nullable=True, comment="结束时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    batch = relationship("ResumeStructBatch", back_populates="tasks")
    deadletters = relationship(
        "ResumeStructDeadletter",
        back_populates="task",
        cascade="all, delete-orphan",
    )


class ResumeStructDeadletter(Base):
    """简历结构化死信表。"""

    __tablename__ = "resume_struct_deadletters"
    __table_args__ = {"comment": "简历结构化死信表"}

    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    task_id = Column(
        Integer,
        ForeignKey("resume_struct_tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联任务ID",
    )
    source_type = Column(String(50), nullable=False, index=True, comment="来源类型")
    source_id = Column(String(100), nullable=False, index=True, comment="来源业务ID")
    resume_created_time = Column(String(50), nullable=False, comment="简历创建时间")
    last_error = Column(Text, nullable=False, comment="最后一次错误信息")
    payload_snapshot = Column(Text, nullable=True, comment="任务快照")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    task = relationship("ResumeStructTask", back_populates="deadletters")
