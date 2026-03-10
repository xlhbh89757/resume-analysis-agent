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
    result = asyncio.run(client.get_temp_url("employee", "E001"))

    assert result["temp_url"] == "https://cdn.example.com/temp.pdf"
    assert result["expires_at"] == "2026-03-06T16:00:00"


def test_get_temp_url_for_submit_candidate_uses_submit_candidate_endpoint(monkeypatch):
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
                    "https://source.example.com/api/submit-candidates/S001/resume/temp-url",
                    (),
                ): {
                    "temp_url": "https://cdn.example.com/submit.pdf",
                }
            }
        ),
    )

    client = ResumeSourceClient()
    result = asyncio.run(client.get_temp_url("submit_candidate", "S001"))

    assert result["temp_url"] == "https://cdn.example.com/submit.pdf"


def test_list_pending_resumes_returns_cursor_payload(monkeypatch):
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
                    "https://source.example.com/api/resumes/pending",
                    (("cursor", "1001"), ("limit", 2), ("source_type", "submit_candidate")),
                ): {
                    "items": [
                        {
                            "source_type": "submit_candidate",
                            "source_id": "S001",
                            "filekey": "/submit-candidate/2026/03/S001.pdf",
                            "resume_created_time": "2026-03-06T10:00:00",
                        },
                        {
                            "source_type": "submit_candidate",
                            "source_id": "S002",
                            "filekey": "/submit-candidate/2026/03/S002.pdf",
                            "resume_created_time": "2026-03-06T11:00:00",
                        },
                    ],
                    "next_cursor": "1003",
                }
            }
        ),
    )

    client = ResumeSourceClient()
    result = asyncio.run(
        client.list_pending_resumes(
            source_type="submit_candidate",
            cursor="1001",
            limit=2,
        )
    )

    assert len(result["items"]) == 2
    assert result["items"][0]["source_id"] == "S001"
    assert result["items"][0]["filekey"] == "/submit-candidate/2026/03/S001.pdf"
    assert result["next_cursor"] == "1003"


def test_build_temp_url_from_filekey_uses_signer(monkeypatch):
    from src.services.resume_source_client import ResumeSourceClient
    import src.services.resume_source_client as module

    class FakeSigner:
        def __init__(self, *args, **kwargs):
            self.calls = []

        def generate_presigned_url(self, object_key, http_method="GET", expire_seconds=900):
            self.calls.append((object_key, http_method, expire_seconds))
            return f"https://obs.example.com{object_key}?expires={expire_seconds}"

    monkeypatch.setattr(
        module,
        "settings",
        SimpleNamespace(
            resume_source_api_base_url="https://source.example.com/api",
            resume_source_api_token="token-1",
            resume_source_api_timeout=30,
            obs_access_key="ak",
            obs_secret_key="sk",
            obs_bucket="bucket-1",
            obs_host="obs.example.com",
            obs_url_expire_seconds=1200,
        ),
    )
    monkeypatch.setattr(module, "OBSSigner", FakeSigner)

    client = ResumeSourceClient()
    result = client.build_temp_url_from_filekey("/employee/2026/03/E001.pdf")

    assert result == {
        "temp_url": "https://obs.example.com/employee/2026/03/E001.pdf?expires=1200",
        "expires_in": 1200,
        "filekey": "/employee/2026/03/E001.pdf",
    }
