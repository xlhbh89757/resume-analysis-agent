"""Client for fetching resume metadata and temporary URLs from source system."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from src.core.config import settings


class ResumeSourceClient:
    """来源系统简历接口适配器。"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.base_url = (base_url or getattr(settings, "resume_source_api_base_url", "")).rstrip("/")
        self.api_token = api_token or getattr(settings, "resume_source_api_token", "")
        self.timeout = timeout or getattr(settings, "resume_source_api_timeout", 30)

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    async def get_temp_url(self, employee_id: str) -> Dict[str, Any]:
        # 任务真正开始执行时再申请临时链接，避免排队导致过期。
        url = f"{self.base_url}/employees/{employee_id}/resume/temp-url"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            return response.json()

    async def list_pending_employees(
        self,
        cursor: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        # 按游标分页拉取待处理员工清单，供批处理调度器投递任务。
        url = f"{self.base_url}/employees/resumes/pending"
        params = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._headers(), params=params)
            response.raise_for_status()
            return response.json()
