import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scripts import retry_deadletter, run_batch_structuring
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


class FakeResumeSourceClient:
    def __init__(self, items):
        self.items = items
        self.calls = []

    async def list_pending_resumes(self, source_type: str, cursor=None, limit=100):
        self.calls.append((source_type, cursor, limit))
        return {"items": self.items, "next_cursor": None}


def test_run_batch_script_enqueues_tasks(monkeypatch):
    session = make_session()
    dispatched = []
    source_client = FakeResumeSourceClient(
        [
            {"source_type": "employee", "source_id": "E001", "filekey": "/employee/E001.pdf", "resume_created_time": "2026-03-09T10:00:00"},
            {"source_type": "employee", "source_id": "E002", "filekey": "/employee/E002.pdf", "resume_created_time": "2026-03-09T11:00:00"},
            {"source_type": "employee", "source_id": "E003", "filekey": "/employee/E003.pdf", "resume_created_time": "2026-03-09T12:00:00"},
        ]
    )

    monkeypatch.setattr(run_batch_structuring, "SessionLocal", lambda: session)
    monkeypatch.setattr(run_batch_structuring, "ResumeSourceClient", lambda: source_client)
    monkeypatch.setattr(
        run_batch_structuring,
        "dispatch_batch_task",
        SimpleNamespace(delay=lambda batch_id, items: dispatched.append((batch_id, items))),
    )

    result = run_batch_structuring.main(
        [
            "--start-employee",
            "E001",
            "--end-employee",
            "E002",
            "--source-type",
            "employee",
            "--batch-size",
            "2",
        ]
    )

    tasks = session.query(ResumeStructTask).order_by(ResumeStructTask.source_id.asc()).all()

    assert result["enqueued_count"] == 2
    assert result["dry_run"] is False
    assert len(dispatched) == 1
    assert len(tasks) == 2
    assert [task.source_id for task in tasks] == ["E001", "E002"]
    assert dispatched[0][1] == [
        {"source_type": "employee", "source_id": "E001", "filekey": "/employee/E001.pdf", "resume_created_time": "2026-03-09T10:00:00"},
        {"source_type": "employee", "source_id": "E002", "filekey": "/employee/E002.pdf", "resume_created_time": "2026-03-09T11:00:00"},
    ]


def test_run_batch_script_dry_run_does_not_write(monkeypatch):
    session = make_session()
    source_client = FakeResumeSourceClient(
        [{"source_type": "submit_candidate", "source_id": "S010", "filekey": "/submit/S010.pdf", "resume_created_time": "2026-03-09T10:00:00"}]
    )

    monkeypatch.setattr(run_batch_structuring, "SessionLocal", lambda: session)
    monkeypatch.setattr(run_batch_structuring, "ResumeSourceClient", lambda: source_client)
    monkeypatch.setattr(
        run_batch_structuring,
        "dispatch_batch_task",
        SimpleNamespace(delay=lambda batch_id, items: (_ for _ in ()).throw(AssertionError("should not dispatch"))),
    )

    result = run_batch_structuring.main(
        [
            "--start-employee",
            "S001",
            "--end-employee",
            "S999",
            "--source-type",
            "submit_candidate",
            "--batch-size",
            "10",
            "--dry-run",
        ]
    )

    assert result["enqueued_count"] == 1
    assert result["dry_run"] is True
    assert session.query(ResumeStructBatch).count() == 0
    assert session.query(ResumeStructTask).count() == 0


def test_retry_deadletter_script_requeues_selected_employees(monkeypatch):
    session = make_session()
    batch = ResumeStructBatch(batch_id="batch-1", total_count=2, status="running")
    session.add(batch)
    session.commit()

    task_1 = ResumeStructTask(
        batch_id=batch.id,
        source_type="employee",
        source_id="E001",
        resume_created_time="2026-03-09T10:00:00",
        idempotency_key="employee:E001:2026-03-09T10:00:00",
        status="dead",
        attempt_count=1,
        error_code="E_LLM",
        error_message="failed",
    )
    task_2 = ResumeStructTask(
        batch_id=batch.id,
        source_type="submit_candidate",
        source_id="S002",
        resume_created_time="2026-03-09T11:00:00",
        idempotency_key="submit_candidate:S002:2026-03-09T11:00:00",
        status="dead",
        attempt_count=2,
        error_code="E_DOWNLOAD",
        error_message="failed",
    )
    session.add_all([task_1, task_2])
    session.commit()

    session.add_all(
        [
            ResumeStructDeadletter(
                task_id=task_1.id,
                source_type="employee",
                source_id="E001",
                resume_created_time="2026-03-09T10:00:00",
                last_error="E_LLM",
                payload_snapshot="{}",
            ),
            ResumeStructDeadletter(
                task_id=task_2.id,
                source_type="submit_candidate",
                source_id="S002",
                resume_created_time="2026-03-09T11:00:00",
                last_error="E_DOWNLOAD",
                payload_snapshot="{}",
            ),
        ]
    )
    session.commit()

    retried = []
    monkeypatch.setattr(retry_deadletter, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        retry_deadletter,
        "extract_resume_task",
        SimpleNamespace(delay=lambda **kwargs: retried.append(kwargs)),
    )

    result = retry_deadletter.main(["--source-id", "S002"])

    refreshed_task_1 = session.query(ResumeStructTask).filter_by(source_id="E001").one()
    refreshed_task_2 = session.query(ResumeStructTask).filter_by(source_id="S002").one()

    assert result["requeued_count"] == 1
    assert retried == [
        {
            "source_type": "submit_candidate",
            "source_id": "S002",
            "resume_created_time": "2026-03-09T11:00:00",
        }
    ]
    assert refreshed_task_1.status == "dead"
    assert refreshed_task_2.status == "queued"
    assert refreshed_task_2.attempt_count == 3
    assert refreshed_task_2.error_code is None
    assert refreshed_task_2.error_message is None


def test_batch_scripts_support_direct_cli_help():
    project_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["DEBUG"] = "release"

    run_help = subprocess.run(
        [sys.executable, "scripts/run_batch_structuring.py", "--help"],
        cwd=project_root,
        capture_output=True,
        text=True,
        env=env,
    )
    retry_help = subprocess.run(
        [sys.executable, "scripts/retry_deadletter.py", "--help"],
        cwd=project_root,
        capture_output=True,
        text=True,
        env=env,
    )

    assert run_help.returncode == 0, run_help.stderr
    assert retry_help.returncode == 0, retry_help.stderr
