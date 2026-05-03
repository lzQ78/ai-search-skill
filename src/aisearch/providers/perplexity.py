from __future__ import annotations

from urllib.parse import quote

from ..models import ProviderResult
from .base import BaseProvider, text_from


class PerplexityProvider(BaseProvider):
    name = "perplexity"
    env_var = "PERPLEXITY_API_KEY"
    capabilities = ("synthesis", "search")

    async def search(self, query: str, max_results: int = 5) -> list[ProviderResult]:
        payload = {
            "model": "sonar",
            "messages": [
                {
                    "role": "system",
                    "content": "Answer briefly and include citations when available.",
                },
                {"role": "user", "content": query},
            ],
        }
        data = await self._json_post(
            "https://api.perplexity.ai/v1/sonar",
            payload,
            self._headers(
                {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            ),
        )
        content = text_from((data.get("choices") or [{}])[0].get("message", {}).get("content"))
        citations = data.get("citations") or data.get("search_results") or []
        results = []
        for citation in citations[:max_results]:
            if isinstance(citation, str):
                url = citation
                title = citation
            else:
                url = citation.get("url") or citation.get("link") or ""
                title = citation.get("title") or url
            if url:
                results.append(
                    ProviderResult(
                        title=title,
                        url=url,
                        snippet=content,
                        provider=self.name,
                        score=0.35,
                        source_type="ai_synthesis",
                        raw={"citation": citation},
                    )
                )

        if results:
            return results

        return [
            ProviderResult(
                title="Perplexity synthesis",
                url=f"perplexity://synthesis/{quote(query)}",
                snippet=content,
                provider=self.name,
                score=0.25,
                source_type="ai_synthesis",
                raw={"response": data},
            )
        ]
