from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import resume as resume_module
from src.core.database import get_db


class FakeUrlStructuringService:
    def __init__(self, db):
        self.db = db

    async def structure_from_url(self, resume_url: str):
        return {
            "status": "success",
            "candidate_id": 101,
            "resume_url": resume_url,
            "structured_resume": {"name": "欧桂华"},
        }

    async def structure_from_employee(self, employee_id: str, resume_created_time: str):
        return {
            "status": "success",
            "candidate_id": 202,
            "employee_id": employee_id,
            "resume_created_time": resume_created_time,
            "structured_resume": {"name": "欧桂华"},
        }

    async def structure_from_source(self, source_type: str, source_id: str, resume_created_time: str):
        return {
            "status": "success",
            "candidate_id": 303,
            "source_type": source_type,
            "source_id": source_id,
            "resume_created_time": resume_created_time,
            "structured_resume": {"name": "欧桂华"},
        }


def build_client(monkeypatch):
    app = FastAPI()
    app.include_router(resume_module.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: iter([object()])
    monkeypatch.setattr(resume_module, "URLStructuringService", FakeUrlStructuringService)
    return TestClient(app)



def test_structure_resume_from_url_endpoint_returns_candidate_id(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/resumes/structure-from-url",
        json={"resume_url": "https://cdn.example.com/resume.pdf"},
    )

    assert response.status_code == 200
    assert response.json()["candidate_id"] == 101
    assert response.json()["structured_resume"]["name"] == "欧桂华"



def test_structure_resume_from_employee_endpoint_returns_candidate_id(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/resumes/structure-from-employee",
        json={
            "employee_id": "E001",
            "resume_created_time": "2026-03-09T10:00:00",
        },
    )

    assert response.status_code == 200
    assert response.json()["candidate_id"] == 202
    assert response.json()["employee_id"] == "E001"


def test_structure_resume_from_source_endpoint_returns_candidate_id(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/resumes/structure-from-source",
        json={
            "source_type": "submit_candidate",
            "source_id": "S001",
            "resume_created_time": "2026-03-09T10:00:00",
        },
    )

    assert response.status_code == 200
    assert response.json()["candidate_id"] == 303
    assert response.json()["source_type"] == "submit_candidate"
    assert response.json()["source_id"] == "S001"
