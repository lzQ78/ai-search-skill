from __future__ import annotations

from typing import Any

from ..models import FetchResult, Freshness, ProviderResult, QueryType
from .base import BaseProvider, text_from


TAVILY_TIME_RANGE = {
    "pd": "day",
    "pw": "week",
    "pm": "month",
    "py": "year",
}


class TavilyProvider(BaseProvider):
    name = "tavily"
    env_var = "TAVILY_API_KEY"
    capabilities = ("search", "fetch")

    async def search(self, query: str, max_results: int = 5) -> list[ProviderResult]:
        return await self.search_with_context(query, max_results=max_results)

    async def search_with_context(
        self,
        query: str,
        max_results: int = 5,
        intent: QueryType | None = None,
        freshness: Freshness | None = None,
        domain_boost: list[str] | None = None,
        profile: str | None = None,
    ) -> list[ProviderResult]:
        payload = {
            "query": query,
            "max_results": max_results,
            "search_depth": "advanced",
            "include_answer": False,
            "include_raw_content": False,
        }
        if freshness:
            payload["time_range"] = TAVILY_TIME_RANGE[freshness]
        data = await self._json_post(
            "https://api.tavily.com/search",
            payload,
            self._headers(
                {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            ),
        )
        return self.parse_results(data)

    async def fetch(self, url: str) -> FetchResult:
        payload = {"urls": [url], "extract_depth": "basic", "format": "markdown"}
        data = await self._json_post(
            "https://api.tavily.com/extract",
            payload,
            self._headers(
                {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            ),
        )
        results = data.get("results") or []
        if not results:
            return FetchResult(url=url, provider=self.name, success=False, error="no content")
        item = results[0]
        content = text_from(item.get("raw_content") or item.get("content"))
        return FetchResult(
            url=item.get("url") or url,
            provider=self.name,
            success=bool(content),
            title=item.get("title"),
            content=content,
            error=None if content else "empty content",
        )

    def parse_results(self, data: dict[str, Any]) -> list[ProviderResult]:
        parsed = []
        for item in data.get("results") or []:
            url = item.get("url") or ""
            if not url:
                continue
            parsed.append(
                ProviderResult(
                    title=item.get("title") or url,
                    url=url,
                    snippet=text_from(item.get("content") or item.get("raw_content")),
                    provider=self.name,
                    score=float(item.get("score") or 0.0),
                    published_at=item.get("published_date"),
                    source_type="secondary",
                    raw=item,
                )
            )
        return parsed
