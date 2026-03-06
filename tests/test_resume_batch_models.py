from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.core.database import Base
from src.models.resume_batch import (
    ResumeStructBatch,
    ResumeStructDeadletter,
    ResumeStructTask,
)


def make_session():
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
        employee_id="E001",
        resume_created_time="2026-03-06T10:00:00",
        idempotency_key="E001:2026-03-06T10:00:00",
        status="queued",
    )
    second = ResumeStructTask(
        batch_id=batch.id,
        employee_id="E001",
        resume_created_time="2026-03-06T10:00:00",
        idempotency_key="E001:2026-03-06T10:00:00",
        status="queued",
    )

    session.add(first)
    session.commit()
    session.add(second)

    try:
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
        employee_id="E002",
        resume_created_time="2026-03-06T11:00:00",
        idempotency_key="E002:2026-03-06T11:00:00",
        status="dead",
    )
    session.add(task)
    session.commit()

    dead = ResumeStructDeadletter(
        task_id=task.id,
        employee_id="E002",
        resume_created_time="2026-03-06T11:00:00",
        last_error="E_LLM",
        payload_snapshot='{"employee_id":"E002"}',
    )
    session.add(dead)
    session.commit()

    assert dead.id is not None
