from __future__ import annotations

from typing import Any

from ..models import ProviderResult
from .base import BaseProvider, text_from


class BraveProvider(BaseProvider):
    name = "brave"
    env_var = "BRAVE_API_KEY"
    capabilities = ("search",)

    async def search(self, query: str, max_results: int = 5) -> list[ProviderResult]:
        response = await self.client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": max_results},
            headers=self._headers({"X-Subscription-Token": self.api_key or ""}),
        )
        response.raise_for_status()
        return self.parse_results(response.json())

    def parse_results(self, data: dict[str, Any]) -> list[ProviderResult]:
        parsed = []
        for item in ((data.get("web") or {}).get("results") or []):
            url = item.get("url") or ""
            if not url:
                continue
            parsed.append(
                ProviderResult(
                    title=item.get("title") or url,
                    url=url,
                    snippet=text_from(item.get("description") or item.get("extra_snippets")),
                    provider=self.name,
                    score=0.7,
                    published_at=item.get("age"),
                    source_type="secondary",
                    raw=item,
                )
            )
        return parsed

