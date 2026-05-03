from __future__ import annotations

import time
from urllib.parse import quote

from ..models import Freshness, QueryType
from ..models import ProviderRun
from ..models import FetchResult, ProviderResult
from .base import BaseProvider, text_from


class JinaProvider(BaseProvider):
    name = "jina"
    env_var = "JINA_API_KEY"
    capabilities = ("search", "fetch")
    requires_key = False

    async def timed_search(
        self,
        query: str,
        max_results: int = 5,
        intent: QueryType | None = None,
        freshness: Freshness | None = None,
        domain_boost: list[str] | None = None,
        profile: str | None = None,
    ) -> tuple[list[ProviderResult], ProviderRun]:
        if not self.api_key:
            start = time.perf_counter()
            return [], self._run("search", "skipped", 0, start, "missing JINA_API_KEY")
        return await super().timed_search(
            query,
            max_results=max_results,
            intent=intent,
            freshness=freshness,
            domain_boost=domain_boost,
            profile=profile,
        )

    async def search(self, query: str, max_results: int = 5) -> list[ProviderResult]:
        url = f"https://s.jina.ai/{quote(query)}"
        response = await self.client.get(url, headers=self._auth_headers())
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return self._parse_json_search(response.json(), query)
        text = response.text
        return [
            ProviderResult(
                title=f"Jina search results for {query}",
                url=url,
                snippet=text_from(text),
                provider=self.name,
                score=0.55,
                source_type="secondary",
                raw={"format": "text"},
            )
        ]

    async def fetch(self, url: str) -> FetchResult:
        reader_url = f"https://r.jina.ai/{url}"
        response = await self.client.get(reader_url, headers=self._auth_headers({"Accept": "text/plain"}))
        response.raise_for_status()
        content = response.text.strip()
        return FetchResult(
            url=url,
            provider=self.name,
            success=bool(content),
            content=content,
            error=None if content else "empty content",
        )

    def _auth_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = extra.copy() if extra else {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _parse_json_search(self, data: dict, query: str) -> list[ProviderResult]:
        candidates = data.get("data") or data.get("results") or []
        parsed = []
        for item in candidates:
            url = item.get("url") or item.get("link") or ""
            if not url:
                continue
            parsed.append(
                ProviderResult(
                    title=item.get("title") or url,
                    url=url,
                    snippet=text_from(item.get("description") or item.get("content")),
                    provider=self.name,
                    score=0.65,
                    source_type="secondary",
                    raw=item,
                )
            )
        if parsed:
            return parsed
        return [
            ProviderResult(
                title=f"Jina search results for {query}",
                url=f"https://s.jina.ai/{quote(query)}",
                snippet=text_from(data),
                provider=self.name,
                score=0.55,
                source_type="secondary",
                raw=data,
            )
        ]
