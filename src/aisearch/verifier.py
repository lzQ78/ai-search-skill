from __future__ import annotations

from collections import defaultdict

from .models import Claim, Conflict, Confidence, FetchResult, ProviderResult, QueryType, Source
from .scoring import composite_score
from .utils import canonical_url, domain_of, truncate, years_in


PROVIDER_BASE_SCORE = {
    "exa": 0.78,
    "tavily": 0.75,
    "brave": 0.72,
    "jina": 0.70,
    "firecrawl": 0.70,
    "perplexity": 0.40,
}


class Verifier:
    def build_sources(
        self,
        results: list[ProviderResult],
        fetches: dict[str, FetchResult] | None = None,
        query: str = "",
        intent: QueryType = QueryType.general,
        domain_boosts: set[str] | None = None,
    ) -> list[Source]:
        fetches = fetches or {}
        deduped = self._dedupe(results)
        sources: list[Source] = []

        for index, result in enumerate(deduped, start=1):
            canon = canonical_url(result.url)
            fetch = fetches.get(canon)
            fetched = bool(fetch and fetch.success and fetch.content)
            content_preview = truncate(fetch.content if fetch else "", 1200)
            score = self._score(
                result,
                fetched,
                query=query,
                intent=intent,
                domain_boosts=domain_boosts or set(),
                content_preview=content_preview,
            )
            source = Source(
                id=f"s{index}",
                title=result.title or result.url,
                url=result.url,
                provider=result.provider,
                source_type=result.source_type,
                published_at=result.published_at,
                fetched=fetched,
                score=score,
                snippet=truncate(result.snippet, 500),
                content_preview=content_preview,
            )
            sources.append(source)

        return sources

    def detect_conflicts(self, sources: list[Source]) -> list[Conflict]:
        year_groups: dict[str, list[Source]] = defaultdict(list)
        for source in sources:
            if source.source_type == "ai_synthesis":
                continue
            text = f"{source.title} {source.snippet} {source.content_preview}"
            for year in years_in(text):
                year_groups[year].append(source)

        if len(year_groups) <= 1:
            return []

        related_sources = {
            source.id for grouped in year_groups.values() for source in grouped
        }
        if len(related_sources) < 2:
            return []

        years = ", ".join(sorted(year_groups))
        return [
            Conflict(
                id="c1",
                description=f"Sources mention different years: {years}",
                source_ids=sorted(related_sources),
            )
        ]

    def confidence_for(self, sources: list[Source], conflicts: list[Conflict]) -> Confidence:
        independent_domains = {
            domain_of(source.url)
            for source in sources
            if source.source_type != "ai_synthesis" and domain_of(source.url)
        }
        fetched_count = sum(
            1
            for source in sources
            if source.fetched and source.source_type != "ai_synthesis"
        )

        if not independent_domains:
            return "low"
        if len(independent_domains) == 1:
            return "low"
        if conflicts:
            return "medium"
        if len(independent_domains) >= 2 and fetched_count >= 1:
            return "high"
        return "medium"

    def claims_for(
        self, query: str, confidence: Confidence, sources: list[Source], conflicts: list[Conflict]
    ) -> list[Claim]:
        non_ai = [source for source in sources if source.source_type != "ai_synthesis"]
        if not non_ai:
            return [
                Claim(
                    text=f"No independently verifiable sources were collected for: {query}",
                    confidence="low",
                    source_ids=[],
                    conflict_ids=[conflict.id for conflict in conflicts],
                )
            ]

        if len({domain_of(source.url) for source in non_ai}) < 2:
            text = f"Only one independent non-AI source was collected for: {query}"
        else:
            text = f"Evidence from multiple independent sources was collected for: {query}"

        return [
            Claim(
                text=text,
                confidence=confidence,
                source_ids=[source.id for source in non_ai[:5]],
                conflict_ids=[conflict.id for conflict in conflicts],
            )
        ]

    def _dedupe(self, results: list[ProviderResult]) -> list[ProviderResult]:
        by_url: dict[str, ProviderResult] = {}
        for result in results:
            key = canonical_url(result.url)
            current = by_url.get(key)
            if current is None or result.score > current.score:
                by_url[key] = result
        return sorted(by_url.values(), key=lambda item: item.score, reverse=True)

    def _score(
        self,
        result: ProviderResult,
        fetched: bool,
        query: str,
        intent: QueryType,
        domain_boosts: set[str],
        content_preview: str,
    ) -> float:
        provider_score = PROVIDER_BASE_SCORE.get(result.provider, 0.5)
        intent_score = composite_score(
            query=query,
            title=result.title,
            snippet=result.snippet,
            content_preview=content_preview,
            url=result.url,
            published_at=result.published_at,
            intent=intent,
            domain_boosts=domain_boosts,
        )
        score = provider_score * 0.45 + intent_score * 0.40
        score += min(max(result.score, 0.0), 1.0) * 0.05
        if fetched:
            score += 0.10
        if result.source_type == "primary":
            score += 0.08
        if result.source_type == "ai_synthesis":
            score -= 0.20
        return round(max(0.0, min(score, 1.0)), 3)
