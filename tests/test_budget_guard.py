import asyncio
from datetime import datetime

from src.services.budget_guard import BudgetExceededError, BudgetGuard
from src.services.llm_service import LLMAnalysisService


class DummyBudgetGuard:
    def assert_can_consume(self, estimated_cost: float, now=None):
        raise BudgetExceededError("E_BUDGET", "hourly budget exceeded")

    def record_usage(self, cost: float, now=None):
        return None



def test_budget_guard_blocks_when_hourly_budget_exceeded():
    guard = BudgetGuard(total_budget=500.0, hourly_budget=1.0)
    current_hour = datetime(2026, 3, 9, 10, 0, 0)

    guard.record_usage(0.8, now=current_hour)
    guard.record_usage(0.3, now=current_hour)

    try:
        guard.assert_can_consume(0.1, now=current_hour)
        raised = False
    except BudgetExceededError as exc:
        raised = True
        assert exc.error_code == "E_BUDGET"

    assert raised is True



def test_extract_resume_info_returns_budget_error_payload(monkeypatch):
    service = LLMAnalysisService(budget_guard=DummyBudgetGuard())

    result = asyncio.run(service.extract_resume_info("候选人简历原文"))

    assert result["work_experiences"] == []
    assert result["project_experiences"] == []
    assert result["_llm_meta"]["error_code"] == "E_BUDGET"
    assert result["_llm_meta"]["budget_blocked"] is True