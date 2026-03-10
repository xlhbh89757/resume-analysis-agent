from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.core.database import Base
from src.models.candidate import Candidate
from src.models.resume_batch import (
    ResumeStructBatch,
    ResumeStructDeadletter,
    ResumeStructTask,
)


def make_session():
    # 用内存 sqlite 做 ORM 单测，不影响 MySQL 数据。
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_resume_struct_tables_can_be_created():
    session = make_session()

    batch = ResumeStructBatch(batch_id="batch-1", total_count=10, status="created")
    session.add(batch)
    session.commit()

    assert batch.id is not None


def test_resume_struct_task_unique_idempotency_key():
    session = make_session()
    batch = ResumeStructBatch(batch_id="batch-1", total_count=10, status="created")
    session.add(batch)
    session.commit()

    first = ResumeStructTask(
        batch_id=batch.id,
        source_type="employee",
        source_id="E001",
        resume_created_time="2026-03-06T10:00:00",
        idempotency_key="E001:2026-03-06T10:00:00",
        status="queued",
    )
    second = ResumeStructTask(
        batch_id=batch.id,
        source_type="employee",
        source_id="E001",
        resume_created_time="2026-03-06T10:00:00",
        idempotency_key="E001:2026-03-06T10:00:00",
        status="queued",
    )

    session.add(first)
    session.commit()
    session.add(second)

    try:
        # 唯一幂等键必须拦住重复任务写入。
        session.commit()
        raised = False
    except IntegrityError:
        session.rollback()
        raised = True

    assert raised is True


def test_deadletter_can_reference_task():
    session = make_session()
    batch = ResumeStructBatch(batch_id="batch-1", total_count=10, status="created")
    session.add(batch)
    session.commit()

    task = ResumeStructTask(
        batch_id=batch.id,
        source_type="submit_candidate",
        source_id="S002",
        resume_created_time="2026-03-06T11:00:00",
        idempotency_key="submit_candidate:S002:2026-03-06T11:00:00",
        status="dead",
    )
    session.add(task)
    session.commit()

    dead = ResumeStructDeadletter(
        task_id=task.id,
        source_type="submit_candidate",
        source_id="S002",
        resume_created_time="2026-03-06T11:00:00",
        last_error="E_LLM",
        payload_snapshot='{"source_type":"submit_candidate","source_id":"S002"}',
    )
    session.add(dead)
    session.commit()

    assert dead.id is not None


def test_candidate_supports_multiple_source_identifiers():
    session = make_session()
    candidate = Candidate(
        name="欧桂华",
        employee_id="E001",
        entrant_id="N001",
        submit_candidate_id="S001",
    )
    session.add(candidate)
    session.commit()
    session.refresh(candidate)

    assert candidate.employee_id == "E001"
    assert candidate.entrant_id == "N001"
    assert candidate.submit_candidate_id == "S001"


def test_resume_struct_tables_store_filekey_for_retry():
    task_columns = ResumeStructTask.__table__.columns.keys()
    deadletter_columns = ResumeStructDeadletter.__table__.columns.keys()

    assert "filekey" in task_columns
    assert "filekey" in deadletter_columns


def test_candidate_email_is_not_indexed_but_name_is_indexed():
    indexed_columns = {
        column.name
        for index in Candidate.__table__.indexes
        for column in index.columns
    }

    assert "name" in indexed_columns
    assert "email" not in indexed_columns


def test_source_type_is_indexed_for_task_tables():
    task_indexed_columns = {
        column.name
        for index in ResumeStructTask.__table__.indexes
        for column in index.columns
    }
    deadletter_indexed_columns = {
        column.name
        for index in ResumeStructDeadletter.__table__.indexes
        for column in index.columns
    }

    assert "source_type" in task_indexed_columns
    assert "source_type" in deadletter_indexed_columns
