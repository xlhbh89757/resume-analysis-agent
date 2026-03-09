"""来源系统简历接口适配器。"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from src.core.config import settings

SOURCE_ENDPOINT_SEGMENTS = {
    "employee": "employees",
    "submit_candidate": "submit-candidates",
    "entrant": "entrants",
}


class ResumeSourceClient:
    """负责从来源系统获取临时简历链接和待处理清单。"""

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

    def _resolve_source_path(self, source_type: str) -> str:
        try:
            return SOURCE_ENDPOINT_SEGMENTS[source_type]
        except KeyError as exc:
            raise ValueError(f"Unsupported source_type: {source_type}") from exc

    async def get_temp_url(
        self,
        source_type_or_id: str,
        source_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取某个来源对象对应的临时简历 URL。"""
        if source_id is None:
            source_type = "employee"
            source_id = source_type_or_id
        else:
            source_type = source_type_or_id

        path = self._resolve_source_path(source_type)
        url = f"{self.base_url}/{path}/{source_id}/resume/temp-url"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            return response.json()

    async def list_pending_resumes(
        self,
        source_type: str,
        cursor: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """按来源类型分页拉取待处理简历清单。"""
        self._resolve_source_path(source_type)
        url = f"{self.base_url}/resumes/pending"
        params = {"source_type": source_type, "limit": limit}
        if cursor is not None:
            params["cursor"] = cursor

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._headers(), params=params)
            response.raise_for_status()
            return response.json()

    async def list_pending_employees(
        self,
        cursor: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """兼容旧调用，默认拉取在职员工清单。"""
        return await self.list_pending_resumes(
            source_type="employee",
            cursor=cursor,
            limit=limit,
        )
