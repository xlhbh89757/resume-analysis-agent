import asyncio
from types import SimpleNamespace


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeAsyncClient:
    def __init__(self, responses):
        self._responses = responses

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, headers=None, params=None):
        key = (url, tuple(sorted((params or {}).items())))
        payload = self._responses[key]
        return FakeResponse(payload)


def test_get_temp_url_returns_url_and_expire_at(monkeypatch):
    from src.services.resume_source_client import ResumeSourceClient
    import src.services.resume_source_client as module

    monkeypatch.setattr(
        module,
        "settings",
        SimpleNamespace(
            resume_source_api_base_url="https://source.example.com/api",
            resume_source_api_token="token-1",
            resume_source_api_timeout=30,
        ),
    )
    monkeypatch.setattr(
        module.httpx,
        "AsyncClient",
        lambda timeout: FakeAsyncClient(
            {
                (
                    "https://source.example.com/api/employees/E001/resume/temp-url",
                    (),
                ): {
                    "temp_url": "https://cdn.example.com/temp.pdf",
                    "expires_at": "2026-03-06T16:00:00",
                }
            }
        ),
    )

    client = ResumeSourceClient()
    result = asyncio.run(client.get_temp_url("E001"))

    assert result["temp_url"] == "https://cdn.example.com/temp.pdf"
    assert result["expires_at"] == "2026-03-06T16:00:00"


def test_list_pending_employees_returns_cursor_payload(monkeypatch):
    from src.services.resume_source_client import ResumeSourceClient
    import src.services.resume_source_client as module

    monkeypatch.setattr(
        module,
        "settings",
        SimpleNamespace(
            resume_source_api_base_url="https://source.example.com/api",
            resume_source_api_token="token-1",
            resume_source_api_timeout=30,
        ),
    )
    monkeypatch.setattr(
        module.httpx,
        "AsyncClient",
        lambda timeout: FakeAsyncClient(
            {
                (
                    "https://source.example.com/api/employees/resumes/pending",
                    (("cursor", "1001"), ("limit", 2)),
                ): {
                    "items": [
                        {
                            "employee_id": "E001",
                            "resume_created_time": "2026-03-06T10:00:00",
                        },
                        {
                            "employee_id": "E002",
                            "resume_created_time": "2026-03-06T11:00:00",
                        },
                    ],
                    "next_cursor": "1003",
                }
            }
        ),
    )

    client = ResumeSourceClient()
    result = asyncio.run(client.list_pending_employees(cursor="1001", limit=2))

    assert len(result["items"]) == 2
    assert result["items"][0]["employee_id"] == "E001"
    assert result["next_cursor"] == "1003"
