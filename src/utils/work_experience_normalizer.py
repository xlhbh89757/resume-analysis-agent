"""Work experience normalization helpers."""

from __future__ import annotations

import json
from typing import Any, Dict

from src.utils.project_experience_normalizer import to_text_list


def normalize_work_experience(value: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize mixed LLM output for work experience persistence."""
    responsibilities = to_text_list(value.get("responsibilities"))
    achievements = to_text_list(value.get("achievements"))

    return {
        "company_name": value.get("company_name"),
        "position": value.get("position"),
        "start_date": value.get("start_date"),
        "end_date": value.get("end_date"),
        "responsibilities": json.dumps(responsibilities, ensure_ascii=False),
        "achievements": json.dumps(achievements, ensure_ascii=False),
    }

