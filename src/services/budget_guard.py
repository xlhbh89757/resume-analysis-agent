"""LLM 预算守卫。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict


class BudgetExceededError(RuntimeError):
    """预算超限异常。"""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


@dataclass
class BudgetGuard:
    """跟踪小时级和总预算消耗。"""

    total_budget: float = 500.0
    hourly_budget: float = 50.0
    total_usage: float = 0.0
    hourly_usage: Dict[str, float] = field(default_factory=dict)

    def assert_can_consume(self, estimated_cost: float, now: datetime | None = None) -> None:
        current_time = now or datetime.now()
        hour_bucket = self._hour_bucket(current_time)
        current_hour_usage = self.hourly_usage.get(hour_bucket, 0.0)

        # 在发起 LLM 请求前先做预算检查，避免预算见底后继续消耗。
        if self.total_usage + estimated_cost > self.total_budget:
            raise BudgetExceededError("E_BUDGET", "total budget exceeded")
        if current_hour_usage + estimated_cost > self.hourly_budget:
            raise BudgetExceededError("E_BUDGET", "hourly budget exceeded")

    def record_usage(self, cost: float, now: datetime | None = None) -> None:
        current_time = now or datetime.now()
        hour_bucket = self._hour_bucket(current_time)
        self.total_usage += cost
        self.hourly_usage[hour_bucket] = self.hourly_usage.get(hour_bucket, 0.0) + cost

    def snapshot(self, now: datetime | None = None) -> dict:
        current_time = now or datetime.now()
        hour_bucket = self._hour_bucket(current_time)
        return {
            "total_budget": self.total_budget,
            "hourly_budget": self.hourly_budget,
            "total_usage": self.total_usage,
            "hourly_usage": self.hourly_usage.get(hour_bucket, 0.0),
        }

    def _hour_bucket(self, current_time: datetime) -> str:
        return current_time.strftime("%Y-%m-%d-%H")