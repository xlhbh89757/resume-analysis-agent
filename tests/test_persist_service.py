from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.database import Base
from src.models.candidate import Candidate
from src.models.resume_batch import ResumeStructBatch, ResumeStructDeadletter, ResumeStructTask
from src.services.persist_service import PersistService


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def create_task(session):
    batch = ResumeStructBatch(batch_id="batch-1", total_count=1, status="running")
    session.add(batch)
    session.commit()

    task = ResumeStructTask(
        batch_id=batch.id,
        source_type="employee",
        source_id="E001",
        resume_created_time="2026-03-06T10:00:00",
        idempotency_key="employee:E001:2026-03-06T10:00:00",
        status="queued",
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def create_task_with_batch(session, batch, source_id: str, created_time: str):
    task = ResumeStructTask(
        batch_id=batch.id,
        source_type="employee",
        source_id=source_id,
        resume_created_time=created_time,
        idempotency_key=f"employee:{source_id}:{created_time}",
        status="queued",
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def make_payload(task_id):
    return {
        "task_id": task_id,
        "source_type": "employee",
        "source_id": "E001",
        "filekey": "/employee/2026/03/E001.pdf",
        "resume_created_time": "2026-03-06T10:00:00",
        "resume_text": "resume raw text",
        "structured_resume": {
            "name": "Candidate A",
            "email": "1136309383@qq.com",
            "phone": "19523866354",
            "education_level": "bachelor",
            "years_of_experience": 5,
            "current_position": "data engineer",
            "summary": "build data warehouse",
            "work_experiences": [
                {
                    "company_name": "Demo Corp",
                    "position": "Data Engineer",
                    "start_date": "2021-01",
                    "end_date": "2026-01",
                    "responsibilities": ["move data from Oracle to Greenplum"],
                    "achievements": ["migrated core models"]
                }
            ],
            "project_experiences": [
                {
                    "project_name": "DW Migration",
                    "role": "Engineer",
                    "start_date": "2024-01",
                    "end_date": "2025-01",
                    "description": "migration project",
                    "technologies": ["Oracle", "Greenplum"],
                    "responsibilities": ["move schedulers"],
                    "achievements": ["improved stability"]
                }
            ],
            "skills": [
                {
                    "skill_name": "Python",
                    "skill_category": "language",
                    "proficiency_level": "advanced"
                }
            ]
        }
    }


def test_persist_skips_when_idempotency_key_already_success():
    session = make_session()
    task = create_task(session)
    service = PersistService(session)
    payload = make_payload(task.id)

    first = service.persist_structured_resume(payload)
    second = service.persist_structured_resume(payload)

    candidate = session.query(Candidate).one()
    session.refresh(task)

    assert first["status"] == "success"
    assert first["candidate_id"] == candidate.id
    assert second["status"] == "skipped"
    assert session.query(Candidate).count() == 1
    assert candidate.employee_id == "E001"
    assert candidate.work_experiences[0].achievements == '["migrated core models"]'
    assert task.status == "success"


def test_persist_reuses_existing_candidate_by_submit_candidate_id():
    session = make_session()
    task = create_task(session)
    service = PersistService(session)
    existing = Candidate(name="Old Candidate", submit_candidate_id="S001", status="completed")
    session.add(existing)
    session.commit()

    payload = make_payload(task.id)
    payload["source_type"] = "submit_candidate"
    payload["source_id"] = "S001"

    result = service.persist_structured_resume(payload)
    session.refresh(existing)

    assert result["status"] == "success"
    assert result["candidate_id"] == existing.id
    assert session.query(Candidate).count() == 1
    assert existing.submit_candidate_id == "S001"
    assert existing.phone == "19523866354"


def test_persist_reuses_existing_candidate_by_phone_and_backfills_source_id():
    session = make_session()
    task = create_task(session)
    service = PersistService(session)
    existing = Candidate(name="Old Candidate", phone="19523866354", status="completed")
    session.add(existing)
    session.commit()

    payload = make_payload(task.id)
    payload["source_type"] = "submit_candidate"
    payload["source_id"] = "S002"

    result = service.persist_structured_resume(payload)
    session.refresh(existing)

    assert result["candidate_id"] == existing.id
    assert session.query(Candidate).count() == 1
    assert existing.submit_candidate_id == "S002"


def test_persist_prefers_name_and_phone_before_other_fallbacks():
    session = make_session()
    task = create_task(session)
    service = PersistService(session)
    exact = Candidate(name="Candidate A", phone="19523866354", status="completed")
    phone_only = Candidate(name="Another", phone="19523866354", status="completed")
    name_only = Candidate(name="Candidate A", phone="17700000000", status="completed")
    session.add_all([exact, phone_only, name_only])
    session.commit()

    payload = make_payload(task.id)
    payload["source_type"] = "submit_candidate"
    payload["source_id"] = "S003"

    result = service.persist_structured_resume(payload)
    session.refresh(exact)

    assert result["candidate_id"] == exact.id
    assert exact.submit_candidate_id == "S003"


def test_persist_reuses_existing_candidate_by_name_when_phone_missing():
    session = make_session()
    task = create_task(session)
    service = PersistService(session)
    existing = Candidate(name="Candidate A", status="completed")
    session.add(existing)
    session.commit()

    payload = make_payload(task.id)
    payload["source_type"] = "submit_candidate"
    payload["source_id"] = "S004"
    payload["structured_resume"]["phone"] = None

    result = service.persist_structured_resume(payload)
    session.refresh(existing)

    assert result["candidate_id"] == existing.id
    assert existing.submit_candidate_id == "S004"


def test_create_deadletter_persists_filekey():
    session = make_session()
    task = create_task(session)
    service = PersistService(session)
    payload = make_payload(task.id)

    result = service.create_deadletter(
        payload=payload,
        error_code="E_LLM",
        error_message="llm failed",
    )

    deadletter = session.query(ResumeStructDeadletter).one()

    assert result["status"] == "dead"
    assert deadletter.filekey == "/employee/2026/03/E001.pdf"


def test_force_reparse_overwrites_existing_success_result():
    session = make_session()
    task = create_task(session)
    service = PersistService(session)
    original_payload = make_payload(task.id)

    first = service.persist_structured_resume(original_payload)
    assert first["status"] == "success"

    updated_payload = make_payload(task.id)
    updated_payload["structured_resume"]["name"] = "Candidate B"
    updated_payload["structured_resume"]["summary"] = "reparsed summary"
    updated_payload["structured_resume"]["work_experiences"][0]["achievements"] = ["new achievement"]
    updated_payload["force_reparse"] = True

    second = service.persist_structured_resume(updated_payload)

    candidate = session.query(Candidate).one()
    session.refresh(task)

    assert second["status"] == "success"
    assert candidate.name == "Candidate B"
    assert candidate.summary == "reparsed summary"
    assert candidate.work_experiences[0].achievements == '["new achievement"]'
    assert task.attempt_count == 2


def test_force_reparse_does_not_skip_existing_success_task():
    session = make_session()
    task = create_task(session)
    service = PersistService(session)
    payload = make_payload(task.id)

    first = service.persist_structured_resume(payload)
    assert first["status"] == "success"

    payload["force_reparse"] = True
    second = service.persist_structured_resume(payload)

    assert second["status"] == "success"


def test_persist_updates_batch_counts_and_completion_for_success_and_dead(monkeypatch):
    session = make_session()
    batch = ResumeStructBatch(batch_id="batch-2", total_count=2, status="running")
    session.add(batch)
    session.commit()

    success_task = create_task_with_batch(session, batch, "E101", "2026-03-06T10:00:00")
    dead_task = create_task_with_batch(session, batch, "E102", "2026-03-06T11:00:00")
    service = PersistService(session)
    fake_now = datetime(2026, 3, 11, 16, 30, 0)
    monkeypatch.setattr("src.services.persist_service.local_now", lambda: fake_now)

    success_payload = make_payload(success_task.id)
    success_payload["source_id"] = "E101"
    success_payload["resume_created_time"] = "2026-03-06T10:00:00"
    success_payload["structured_resume"]["phone"] = "19900000001"
    service.persist_structured_resume(success_payload)

    dead_payload = make_payload(dead_task.id)
    dead_payload["source_id"] = "E102"
    dead_payload["resume_created_time"] = "2026-03-06T11:00:00"
    dead_payload["structured_resume"]["phone"] = "19900000002"
    service.create_deadletter(
        payload=dead_payload,
        error_code="E_DOWNLOAD",
        error_message="obs 404",
    )

    session.refresh(batch)
    session.refresh(success_task)
    session.refresh(dead_task)

    assert batch.success_count == 1
    assert batch.failed_count == 1
    assert batch.skipped_count == 0
    assert batch.status == "completed"
    assert batch.finished_at == fake_now
    assert success_task.started_at == fake_now
    assert success_task.finished_at == fake_now
    assert dead_task.finished_at == fake_now


def test_persist_marks_skipped_task_and_updates_batch(monkeypatch):
    session = make_session()
    batch = ResumeStructBatch(batch_id="batch-3", total_count=1, status="running")
    session.add(batch)
    session.commit()

    task = create_task_with_batch(session, batch, "E201", "2026-03-06T10:00:00")
    service = PersistService(session)
    fake_now = datetime(2026, 3, 11, 17, 0, 0)
    monkeypatch.setattr("src.services.persist_service.local_now", lambda: fake_now)

    service.mark_task_skipped(task.id, "already structured")
    session.refresh(batch)
    session.refresh(task)

    assert task.status == "skipped"
    assert task.error_message == "already structured"
    assert task.finished_at == fake_now
    assert batch.skipped_count == 1
    assert batch.status == "completed"
    assert batch.finished_at == fake_now

def make_file_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'batch_state.db'}")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)


def test_batch_completion_survives_concurrent_terminal_updates(monkeypatch, tmp_path):
    SessionFactory = make_file_session(tmp_path)
    seed = SessionFactory()
    batch = ResumeStructBatch(batch_id="batch-concurrent", total_count=2, status="running")
    seed.add(batch)
    seed.commit()
    task1 = create_task_with_batch(seed, batch, "E301", "2026-03-06T10:00:00")
    task2 = create_task_with_batch(seed, batch, "E302", "2026-03-06T11:00:00")
    task1_id = task1.id
    task2_id = task2.id
    seed.close()

    fake_now = datetime(2026, 3, 11, 18, 0, 0)
    monkeypatch.setattr("src.services.persist_service.local_now", lambda: fake_now)

    session1 = SessionFactory()
    session2 = SessionFactory()
    service1 = PersistService(session1)
    service2 = PersistService(session2)

    payload1 = make_payload(task1_id)
    payload1["source_id"] = "E301"
    payload1["resume_created_time"] = "2026-03-06T10:00:00"
    payload1["structured_resume"]["phone"] = "19900000301"
    service1.persist_structured_resume(payload1)

    payload2 = make_payload(task2_id)
    payload2["source_id"] = "E302"
    payload2["resume_created_time"] = "2026-03-06T11:00:00"
    payload2["structured_resume"]["phone"] = "19900000302"
    service2.create_deadletter(
        payload=payload2,
        error_code="E_DOWNLOAD",
        error_message="obs 404",
    )

    verify = SessionFactory()
    batch = verify.query(ResumeStructBatch).filter(ResumeStructBatch.batch_id == "batch-concurrent").one()
    assert batch.success_count == 1
    assert batch.failed_count == 1
    assert batch.status == "completed"
    assert batch.finished_at == fake_now
