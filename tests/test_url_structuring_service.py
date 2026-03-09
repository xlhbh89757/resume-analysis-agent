import asyncio
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.database import Base
from src.models.candidate import Candidate
from src.services.persist_service import PersistService
from src.services.url_structuring_service import URLStructuringService


class FakeTempPath:
    def __init__(self, real_path: Path):
        self.real_path = real_path
        self.deleted = False

    def __str__(self) -> str:
        return str(self.real_path)

    def exists(self) -> bool:
        return not self.deleted

    def unlink(self) -> None:
        self.deleted = True


class FakeParser:
    def __init__(self):
        self.paths = []

    def parse(self, file_path: str) -> str:
        self.paths.append(file_path)
        assert Path(file_path).exists()
        return "候选人简历原文"


class FakeLLMService:
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
            "work_experiences": [
                {
                    "company_name": "深德科",
                    "position": "数据开发工程师",
                    "start_date": "2021-01",
                    "end_date": "2026-01",
                    "responsibilities": ["负责 Oracle 到 Greenplum 数据迁移"],
                    "achievements": ["完成多套核心模型迁移"],
                }
            ],
            "project_experiences": [],
            "skills": [],
        }


class FakeSourceClient:
    def __init__(self):
        self.employee_ids = []

    async def get_temp_url(self, employee_id: str):
        self.employee_ids.append(employee_id)
        return {
            "temp_url": "https://cdn.example.com/resume.pdf",
            "expires_at": "2026-03-09T12:00:00",
        }


class FakeDownloader:
    def __init__(self):
        self.urls = []
        self.last_path = None

    async def __call__(self, resume_url: str):
        self.urls.append(resume_url)
        self.last_path = FakeTempPath(Path('README.md').resolve())
        return self.last_path


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_structure_from_url_downloads_parses_and_persists():
    session = make_session()
    downloader = FakeDownloader()
    parser = FakeParser()
    service = URLStructuringService(
        db=session,
        document_parser=parser,
        llm_service=FakeLLMService(),
        persist_service=PersistService(session),
        downloader=downloader,
    )

    result = asyncio.run(service.structure_from_url("https://cdn.example.com/resume.pdf"))

    candidate = session.query(Candidate).one()
    assert result["status"] == "success"
    assert result["candidate_id"] == candidate.id
    assert result["structured_resume"]["name"] == "欧桂华"
    assert parser.paths == [str(downloader.last_path)]
    assert downloader.last_path.deleted is True



def test_structure_from_employee_uses_temp_url_and_idempotent_persist():
    session = make_session()
    downloader = FakeDownloader()
    parser = FakeParser()
    source_client = FakeSourceClient()
    service = URLStructuringService(
        db=session,
        document_parser=parser,
        llm_service=FakeLLMService(),
        persist_service=PersistService(session),
        source_client=source_client,
        downloader=downloader,
    )

    first = asyncio.run(
        service.structure_from_employee(
            employee_id="E001",
            resume_created_time="2026-03-09T10:00:00",
        )
    )
    second = asyncio.run(
        service.structure_from_employee(
            employee_id="E001",
            resume_created_time="2026-03-09T10:00:00",
        )
    )

    assert first["status"] == "success"
    assert second["status"] == "skipped"
    assert source_client.employee_ids == ["E001", "E001"]
    assert downloader.urls == [
        "https://cdn.example.com/resume.pdf",
        "https://cdn.example.com/resume.pdf",
    ]
    assert session.query(Candidate).count() == 1