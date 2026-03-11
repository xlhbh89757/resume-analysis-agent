from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


LOCAL_TIMEZONE = ZoneInfo("Asia/Shanghai")


def local_now() -> datetime:
    """Return local wall-clock time for values persisted into MySQL DATETIME columns."""
    return datetime.now(LOCAL_TIMEZONE).replace(tzinfo=None)
