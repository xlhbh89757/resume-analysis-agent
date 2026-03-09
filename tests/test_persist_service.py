from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.database import Base
from src.models.candidate import Candidate
from src.models.resume_batch import ResumeStructBatch, ResumeStructTask
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


def make_payload(task_id):
    return {
        "task_id": task_id,
        "source_type": "employee",
        "source_id": "E001",
        "resume_created_time": "2026-03-06T10:00:00",
        "resume_text": "候选人简历原文",
        "structured_resume": {
            "name": "欧桂华",
            "email": "1136309383@qq.com",
            "phone": "19523866354",
            "education_level": "本科",
            "years_of_experience": 5,
            "current_position": "数据开发工程师",
            "summary": "负责数据仓库建设与迁移。",
            "work_experiences": [
                {
                    "company_name": "深德科",
                    "position": "数据开发工程师",
                    "start_date": "2021-01",
                    "end_date": "2026-01",
                    "responsibilities": ["负责 Oracle 到 Greenplum 数据迁移"],
                    "achievements": ["完成多套核心模型迁移"]
                }
            ],
            "project_experiences": [
                {
                    "project_name": "数据仓库迁移",
                    "role": "开发工程师",
                    "start_date": "2024-01",
                    "end_date": "2025-01",
                    "description": "完成仓库迁移改造",
                    "technologies": ["Oracle", "Greenplum"],
                    "responsibilities": ["迁移调度作业"],
                    "achievements": ["提升迁移稳定性"]
                }
            ],
            "skills": [
                {
                    "skill_name": "Python",
                    "skill_category": "编程语言",
                    "proficiency_level": "熟练"
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
    assert candidate.work_experiences[0].achievements == '["完成多套核心模型迁移"]'
    assert task.status == "success"


def test_persist_reuses_existing_candidate_by_submit_candidate_id():
    session = make_session()
    task = create_task(session)
    service = PersistService(session)
    existing = Candidate(name="旧候选人", submit_candidate_id="S001", status="completed")
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
    existing = Candidate(name="旧候选人", phone="19523866354", status="completed")
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
    exact = Candidate(name="欧桂华", phone="19523866354", status="completed")
    phone_only = Candidate(name="其他人", phone="19523866354", status="completed")
    name_only = Candidate(name="欧桂华", phone="17700000000", status="completed")
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
    existing = Candidate(name="欧桂华", status="completed")
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
