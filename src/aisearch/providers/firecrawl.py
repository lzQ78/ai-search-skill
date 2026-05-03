from __future__ import annotations

from ..models import FetchResult
from .base import BaseProvider, text_from


class FirecrawlProvider(BaseProvider):
    name = "firecrawl"
    env_var = "FIRECRAWL_API_KEY"
    capabilities = ("fetch",)

    async def fetch(self, url: str) -> FetchResult:
        data = await self._json_post(
            "https://api.firecrawl.dev/v2/scrape",
            {"url": url, "formats": ["markdown"]},
            self._headers(
                {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            ),
        )
        payload = data.get("data") or data
        content = text_from(payload.get("markdown") or payload.get("content"))
        metadata = payload.get("metadata") or {}
        return FetchResult(
            url=metadata.get("sourceURL") or url,
            provider=self.name,
            success=bool(content),
            title=metadata.get("title"),
            content=content,
            error=None if content else "empty content",
        )

