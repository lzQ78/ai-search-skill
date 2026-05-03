from __future__ import annotations

from ..models import FetchResult
from .base import BaseProvider, text_from


class MinerUProvider(BaseProvider):
    name = "mineru"
    env_var = "MINERU_API_TOKEN"
    capabilities = ("fetch",)

    async def fetch(self, url: str) -> FetchResult:
        data = await self._json_post(
            "https://mineru.net/api/v4/extract/task",
            {
                "file_sources": [url],
                "model_version": "MinerU-HTML",
                "is_ocr": True,
            },
            self._headers(
                {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            ),
        )
        content = text_from(
            data.get("markdown")
            or data.get("md")
            or data.get("content")
            or data.get("data", {}).get("markdown")
            or data.get("data", {}).get("content")
        )
        artifacts = _artifacts_from(data)
        return FetchResult(
            url=url,
            provider=self.name,
            success=bool(content or artifacts),
            content=content,
            error=None if content or artifacts else "empty content",
            artifacts=artifacts,
        )


def _artifacts_from(data: dict) -> dict[str, str]:
    payload = data.get("data") if isinstance(data.get("data"), dict) else data
    artifacts = {}
    for key in ("full_zip_url", "markdown_url", "markdown_path", "task_id"):
        value = payload.get(key)
        if value:
            artifacts[key] = str(value)
    return artifacts
