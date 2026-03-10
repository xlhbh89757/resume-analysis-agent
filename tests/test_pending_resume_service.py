from types import SimpleNamespace


class FakeMappings:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return FakeMappings(self._rows)


class FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, statement, params):
        self.calls.append({"sql": str(statement), "params": params})
        return FakeResult(self.rows)


def test_pending_resume_service_maps_rows_and_builds_next_cursor():
    from src.services.pending_resume_service import PendingResumeService

    session = FakeSession(
        [
            {
                "source_type": "employee",
                "source_id": "1001",
                "resume_created_time": "2025-02-27 10:25:52",
                "filekey": "/employee/1001.pdf",
            },
            {
                "source_type": "employee",
                "source_id": "1002",
                "resume_created_time": "2025-02-27 10:30:00",
                "filekey": "/employee/1002.pdf",
            },
            {
                "source_type": "employee",
                "source_id": "1003",
                "resume_created_time": "2025-02-27 10:35:00",
                "filekey": "/employee/1003.pdf",
            },
        ]
    )

    service = PendingResumeService(session)
    result = service.list_pending_resumes(source_type="employee", cursor="1000", limit=2)

    assert result == {
        "items": [
            {
                "source_type": "employee",
                "source_id": "1001",
                "resume_created_time": "2025-02-27 10:25:52",
                "filekey": "/employee/1001.pdf",
            },
            {
                "source_type": "employee",
                "source_id": "1002",
                "resume_created_time": "2025-02-27 10:30:00",
                "filekey": "/employee/1002.pdf",
            },
        ],
        "next_cursor": "1002",
    }
    assert session.calls[0]["params"] == {
        "source_type": "employee",
        "cursor": "1000",
        "fetch_limit": 3,
    }


def test_pending_resume_service_returns_empty_for_entrant():
    from src.services.pending_resume_service import PendingResumeService

    session = FakeSession([])
    service = PendingResumeService(session)

    result = service.list_pending_resumes(source_type="entrant", cursor=None, limit=100)

    assert result == {"items": [], "next_cursor": None}
    assert session.calls == []
