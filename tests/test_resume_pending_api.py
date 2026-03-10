from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import resume as resume_module
from src.core.database import get_db


class FakePendingResumeService:
    def __init__(self, db):
        self.db = db

    def list_pending_resumes(self, source_type: str, cursor=None, limit: int = 100):
        return {
            "items": [
                {
                    "source_type": source_type,
                    "source_id": "1528",
                    "resume_created_time": "2025-02-27 10:25:52",
                    "filekey": "/employee/2025-02-27/202545P2RAPP0829.pdf",
                }
            ],
            "next_cursor": None if cursor else "1528",
        }


def build_client(monkeypatch):
    app = FastAPI()
    app.include_router(resume_module.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: iter([object()])
    monkeypatch.setattr(resume_module, "PendingResumeService", FakePendingResumeService)
    return TestClient(app)


def test_pending_resume_endpoint_returns_contract(monkeypatch):
    client = build_client(monkeypatch)

    response = client.get(
        "/api/v1/resumes/pending",
        params={"source_type": "employee", "limit": 2},
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "source_type": "employee",
                "source_id": "1528",
                "resume_created_time": "2025-02-27 10:25:52",
                "filekey": "/employee/2025-02-27/202545P2RAPP0829.pdf",
            }
        ],
        "next_cursor": "1528",
    }
