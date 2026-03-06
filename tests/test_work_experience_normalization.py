import json

from src.utils.work_experience_normalizer import normalize_work_experience


def test_normalize_work_experience_serializes_achievements():
    payload = {
        "company_name": "A Corp",
        "position": "Data Engineer",
        "responsibilities": ["Build ETL", "Monitor jobs"],
        "achievements": ["Reduced cost 20%", "Improved SLA"],
    }

    normalized = normalize_work_experience(payload)

    assert json.loads(normalized["responsibilities"]) == ["Build ETL", "Monitor jobs"]
    assert json.loads(normalized["achievements"]) == ["Reduced cost 20%", "Improved SLA"]


def test_normalize_work_experience_handles_multiline_achievements():
    payload = {
        "company_name": "B Corp",
        "position": "Analyst",
        "responsibilities": "Data cleaning",
        "achievements": "Won annual award\nDelivered migration",
    }

    normalized = normalize_work_experience(payload)

    assert json.loads(normalized["achievements"]) == [
        "Won annual award",
        "Delivered migration",
    ]


def test_normalize_work_experience_defaults_empty_achievements():
    payload = {
        "company_name": "C Corp",
        "position": "Developer",
        "responsibilities": None,
    }

    normalized = normalize_work_experience(payload)

    assert json.loads(normalized["responsibilities"]) == []
    assert json.loads(normalized["achievements"]) == []

