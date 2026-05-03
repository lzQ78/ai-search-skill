from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ..models import FetchResult, Freshness, ProviderResult, QueryType
from .base import BaseProvider, text_from


FRESHNESS_START_DATES = {
    "pd": 1,
    "pw": 7,
    "pm": 30,
    "py": 365,
}


class ExaProvider(BaseProvider):
    name = "exa"
    env_var = "EXA_API_KEY"
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
            "numResults": max_results,
            "type": _exa_type_for(intent, profile),
            "contents": {"text": True, "highlights": {"maxCharacters": 1200}},
        }
        if freshness:
            payload["startPublishedDate"] = _start_published_date(freshness)
        data = await self._json_post(
            "https://api.exa.ai/search",
            payload,
            self._headers({"x-api-key": self.api_key or "", "Content-Type": "application/json"}),
        )
        return self.parse_results(data)

    async def fetch(self, url: str) -> FetchResult:
        payload = {"urls": [url], "text": True}
        data = await self._json_post(
            "https://api.exa.ai/contents",
            payload,
            self._headers({"x-api-key": self.api_key or "", "Content-Type": "application/json"}),
        )
        results = data.get("results") or []
        if not results:
            return FetchResult(url=url, provider=self.name, success=False, error="no content")
        item = results[0]
        content = text_from(item.get("text") or item.get("summary"))
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
                    snippet=text_from(
                        item.get("highlights") or item.get("text") or item.get("summary")
                    ),
                    provider=self.name,
                    score=float(item.get("score") or 0.0),
                    published_at=item.get("publishedDate"),
                    source_type="secondary",
                    raw=item,
                )
            )
        return parsed


def _exa_type_for(intent: QueryType | None, profile: str | None) -> str:
    if intent == QueryType.resource:
        return "instant"
    if intent in {QueryType.status, QueryType.news}:
        return "fast"
    if intent == QueryType.exploratory and profile == "deep":
        return "deep"
    return "auto"


def _start_published_date(freshness: Freshness) -> str:
    days = FRESHNESS_START_DATES[freshness]
    return (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
