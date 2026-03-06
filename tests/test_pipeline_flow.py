from src.tasks.pipeline import (
    PIPELINE_QUEUE_ROUTES,
    PIPELINE_TASK_NAMES,
    build_extract_payload,
)


def test_pipeline_payload_excludes_temp_url():
    payload = build_extract_payload(
        employee_id="E001",
        resume_created_time="2026-03-06T10:00:00",
        temp_url="https://cdn.example.com/temp.pdf",
    )

    assert payload == {
        "employee_id": "E001",
        "resume_created_time": "2026-03-06T10:00:00",
    }
    assert "temp_url" not in payload


def test_pipeline_queue_routes_cover_all_stages():
    assert PIPELINE_TASK_NAMES == {
        "dispatch": "resume.pipeline.dispatch_batch",
        "extract": "resume.pipeline.extract_resume",
        "llm": "resume.pipeline.llm_extract",
        "persist": "resume.pipeline.persist_result",
        "deadletter": "resume.pipeline.deadletter",
    }
    assert PIPELINE_QUEUE_ROUTES == {
        PIPELINE_TASK_NAMES["dispatch"]: {"queue": "dispatch_queue"},
        PIPELINE_TASK_NAMES["extract"]: {"queue": "extract_queue"},
        PIPELINE_TASK_NAMES["llm"]: {"queue": "llm_queue"},
        PIPELINE_TASK_NAMES["persist"]: {"queue": "persist_queue"},
        PIPELINE_TASK_NAMES["deadletter"]: {"queue": "dead_letter_queue"},
    }