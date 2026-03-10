"""来源系统简历清单适配器。"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from src.core.config import settings
from src.obs.OBSSigner import OBSSigner

SOURCE_ENDPOINT_SEGMENTS = {
    "employee": "employees",
    "submit_candidate": "submit-candidates",
    "entrant": "entrants",
}


class ResumeSourceClient:
    """负责获取待处理简历清单，并按 filekey 生成临时访问链接。"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.base_url = (base_url or getattr(settings, "resume_source_api_base_url", "")).rstrip("/")
        self.api_token = api_token or getattr(settings, "resume_source_api_token", "")
        self.timeout = timeout or getattr(settings, "resume_source_api_timeout", 30)
        self._signer: OBSSigner | None = None

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

    def _get_signer(self) -> OBSSigner:
        if self._signer is not None:
            return self._signer

        if not all(
            [
                getattr(settings, "obs_access_key", None),
                getattr(settings, "obs_secret_key", None),
                getattr(settings, "obs_bucket", None),
                getattr(settings, "obs_host", None),
            ]
        ):
            raise ValueError("OBS signer is not configured")

        self._signer = OBSSigner(
            access_key=settings.obs_access_key,
            secret_key=settings.obs_secret_key,
            bucket=settings.obs_bucket,
            host=settings.obs_host,
        )
        return self._signer

    def build_temp_url_from_filekey(
        self,
        filekey: str,
        expire_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """基于 filekey 在本地生成临时访问链接。"""
        effective_expire_seconds = expire_seconds or getattr(settings, "obs_url_expire_seconds", 900)
        signer = self._get_signer()
        temp_url = signer.generate_presigned_url(
            object_key=filekey,
            expire_seconds=effective_expire_seconds,
        )
        return {
            "temp_url": temp_url,
            "expires_in": effective_expire_seconds,
            "filekey": filekey,
        }

    async def get_temp_url(
        self,
        source_type_or_id: str,
        source_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """兼容旧链路，按来源对象从外部接口获取临时 URL。"""
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
        """分页拉取待处理简历清单，清单项需包含 filekey。"""
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
