"""Project experience normalization helpers."""

from __future__ import annotations

import json
from typing import Any, List


def to_text_list(value: Any) -> List[str]:
    """Convert mixed LLM output into a list of non-empty text lines."""
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass

        if "\n" in text:
            return [line.strip() for line in text.splitlines() if line.strip()]
        return [text]

    return [str(value).strip()] if str(value).strip() else []

