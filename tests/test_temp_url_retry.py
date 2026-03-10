from types import SimpleNamespace

import httpx
import pytest

from src.tasks import analysis


class RefreshOnceService:
    def __init__(self, db):
        self.db = db
        self.calls = []
        self.source_client = self
        self._sign_count = 0

    async def get_temp_url(self, source_type: str, source_id: str | None = None):
        if source_id is None:
            source_id = source_type
            source_type = "employee"
        self.calls.append(("refresh", source_type, source_id))
        return {"temp_url": "https://cdn.example.com/new.pdf"}

    def build_temp_url_from_filekey(self, filekey: str, expire_seconds: int | None = None):
        self.calls.append(("sign", filekey, expire_seconds))
        self._sign_count += 1
        suffix = "old.pdf" if self._sign_count == 1 else "new.pdf"
        return {"temp_url": f"https://cdn.example.com/{suffix}", "filekey": filekey}

    async def extract_resume_text_from_url(self, resume_url: str) -> str:
        self.calls.append(("extract", resume_url))
        if resume_url.endswith("old.pdf"):
            request = httpx.Request("GET", resume_url)
            response = httpx.Response(403, request=request)
            raise httpx.HTTPStatusError("expired", request=request, response=response)
        return "候选人简历原文"

    async def extract_resume_text_from_source(self, source_type: str, source_id: str) -> str:
        return "候选人简历原文"


class RefreshStillFailService(RefreshOnceService):
    async def extract_resume_text_from_url(self, resume_url: str) -> str:
        self.calls.append(("extract", resume_url))
        request = httpx.Request("GET", resume_url)
        response = httpx.Response(403, request=request)
        raise httpx.HTTPStatusError("expired", request=request, response=response)



def test_extract_refreshes_temp_url_on_403(monkeypatch):
    service = RefreshOnceService(None)
    monkeypatch.setattr(analysis, "SessionLocal", lambda: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(analysis, "URLStructuringService", lambda db: service)

    result = analysis.extract_resume_task.run(
        source_type="submit_candidate",
        source_id="S001",
        resume_created_time="2026-03-09T10:00:00",
        filekey="/submit/S001.pdf",
        enqueue=False,
    )

    assert result["resume_text"] == "候选人简历原文"
    assert service.calls == [
        ("sign", "/submit/S001.pdf", None),
        ("extract", "https://cdn.example.com/old.pdf"),
        ("sign", "/submit/S001.pdf", None),
        ("extract", "https://cdn.example.com/new.pdf"),
    ]



def test_extract_raises_e_download_when_refresh_still_fails(monkeypatch):
    service = RefreshStillFailService(None)
    deadletters = []
    monkeypatch.setattr(analysis, "SessionLocal", lambda: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(analysis, "URLStructuringService", lambda db: service)
    monkeypatch.setattr(
        analysis,
        "deadletter_task",
        SimpleNamespace(run=lambda **kwargs: deadletters.append(kwargs)),
    )

    with pytest.raises(RuntimeError, match="E_DOWNLOAD"):
        analysis.extract_resume_task.run(
            source_type="submit_candidate",
            source_id="S001",
            resume_created_time="2026-03-09T10:00:00",
            filekey="/submit/S001.pdf",
            enqueue=False,
        )

    assert deadletters == [
        {
            "payload": {
                "source_type": "submit_candidate",
                "source_id": "S001",
                "resume_created_time": "2026-03-09T10:00:00",
                "filekey": "/submit/S001.pdf",
            },
            "error_code": "E_DOWNLOAD",
            "error_message": "E_DOWNLOAD: temp url expired after refresh",
        }
    ]
