import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.database import Base
from src.models.candidate import Candidate
from src.models.resume_batch import ResumeStructBatch, ResumeStructDeadletter, ResumeStructTask
from src.tasks import analysis


class FakeURLStructuringService:
    def __init__(self, db):
        self.db = db

    async def extract_resume_text_from_source(self, source_type: str, source_id: str) -> str:
        assert source_type == "employee"
        assert source_id == "E001"
        return "候选人简历原文"

    async def extract_resume_text_from_url(self, resume_url: str) -> str:
        return "候选人简历原文"


class FakeLLMAnalysisService:
    async def extract_resume_info(self, resume_text: str):
        assert resume_text == "候选人简历原文"
        return {
            "name": "欧桂华",
            "email": "1136309383@qq.com",
            "phone": "19523866354",
            "education_level": "本科",
            "years_of_experience": 5,
            "current_position": "数据开发工程师",
            "summary": "负责数据仓库建设与迁移。",
            "work_experiences": [],
            "project_experiences": [],
            "skills": [],
            "_llm_meta": {
                "provider": "openai",
                "estimated_cost": 0.0123,
                "budget_blocked": False,
            },
        }



def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()



def seed_task(session):
    batch = ResumeStructBatch(batch_id="batch-1", total_count=1, status="running")
    session.add(batch)
    session.commit()

    task = ResumeStructTask(
        batch_id=batch.id,
        source_type="employee",
        source_id="E001",
        resume_created_time="2026-03-09T10:00:00",
        idempotency_key="employee:E001:2026-03-09T10:00:00",
        status="queued",
    )
    session.add(task)
    session.commit()
    return task.id



def test_extract_llm_persist_pipeline_marks_task_success(monkeypatch):
    session = make_session()
    task_id = seed_task(session)

    monkeypatch.setattr(analysis, "SessionLocal", lambda: session)
    monkeypatch.setattr(analysis, "URLStructuringService", FakeURLStructuringService)
    monkeypatch.setattr(analysis, "LLMAnalysisService", FakeLLMAnalysisService)

    llm_payload = analysis.extract_resume_task.run(
        source_type="employee",
        source_id="E001",
        resume_created_time="2026-03-09T10:00:00",
    )
    persist_payload = analysis.llm_extract_task.run(llm_payload)
    persist_result = analysis.persist_result_task.run(persist_payload)

    candidate = session.query(Candidate).one()
    task = session.query(ResumeStructTask).filter(ResumeStructTask.id == task_id).one()

    assert persist_result["status"] == "success"
    assert persist_result["candidate_id"] == candidate.id
    assert task.status == "success"
    assert task.llm_cost == "0.0123"
    assert task.llm_tokens_in is not None
    assert task.llm_tokens_out is not None



def test_deadletter_task_persists_failed_payload(monkeypatch):
    session = make_session()
    task_id = seed_task(session)
    monkeypatch.setattr(analysis, "SessionLocal", lambda: session)

    result = analysis.deadletter_task.run(
        payload={
            "source_type": "employee",
            "source_id": "E001",
            "resume_created_time": "2026-03-09T10:00:00",
            "resume_text": "候选人简历原文",
        },
        error_code="E_LLM",
        error_message="llm timeout",
    )

    deadletter = session.query(ResumeStructDeadletter).one()
    task = session.query(ResumeStructTask).filter(ResumeStructTask.id == task_id).one()

    assert result["error_code"] == "E_LLM"
    assert deadletter.source_id == "E001"
    assert deadletter.last_error == "llm timeout"
    assert json.loads(deadletter.payload_snapshot)["resume_text"] == "候选人简历原文"
    assert task.status == "dead"
    assert task.error_code == "E_LLM"
