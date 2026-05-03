from __future__ import annotations

import asyncio

import httpx

from .config import Settings
from .models import ContentArtifact, FetchOutput, Profile, QueryType, ResearchOutput, SearchOutput
from .planner import build_plan
from .providers import build_providers
from .providers.base import BaseProvider
from .reader import Reader
from .router import select_search_providers
from .thread_reader import ThreadReader
from .utils import canonical_url, looks_like_url
from .verifier import Verifier


async def close_providers(providers: dict[str, BaseProvider]) -> None:
    await asyncio.gather(*(provider.close() for provider in providers.values()))


async def run_search(
    settings: Settings,
    query: str,
    provider_names: list[str] | None = None,
    max_results: int = 5,
    client: httpx.AsyncClient | None = None,
) -> SearchOutput:
    providers = build_providers(settings, client=client)
    try:
        selected = _selected_names(providers, provider_names)
        tasks = [
            providers[name].timed_search(query, max_results=max_results)
            for name in selected
            if "search" in providers[name].capabilities
        ]
        gathered = await asyncio.gather(*tasks) if tasks else []
        results = []
        runs = []
        for provider_results, run in gathered:
            results.extend(provider_results)
            runs.append(run)
        return SearchOutput(query=query, results=results, provider_runs=runs)
    finally:
        if client is None:
            await close_providers(providers)


async def run_fetch(
    settings: Settings,
    url: str,
    client: httpx.AsyncClient | None = None,
    content_fallback: str = "auto",
) -> FetchOutput:
    providers = build_providers(settings, client=client)
    try:
        reader = Reader(
            providers,
            concurrency=settings.fetch_concurrency,
            content_fallback=content_fallback,
        )
        result, runs = await reader.fetch_url(url)
        return FetchOutput(url=url, result=result, provider_runs=runs)
    finally:
        if client is None:
            await close_providers(providers)


async def run_research(
    settings: Settings,
    query: str,
    profile: Profile = Profile.balanced,
    provider_names: list[str] | None = None,
    client: httpx.AsyncClient | None = None,
    intent: QueryType | None = None,
    domain_boosts: list[str] | None = None,
    thread_depth: int = 0,
    max_thread_fetches: int | None = None,
    content_fallback: str = "auto",
) -> ResearchOutput:
    plan = build_plan(query, profile, intent=intent)
    providers = build_providers(settings, client=client)
    verifier = Verifier()
    runs = []
    results = []
    domain_boost_set = {domain.lower() for domain in (domain_boosts or []) if domain}

    try:
        if looks_like_url(query):
            reader = Reader(
                providers,
                concurrency=settings.fetch_concurrency,
                content_fallback=content_fallback,
            )
            fetch_result, fetch_runs = await reader.fetch_url(query)
            runs.extend(fetch_runs)
            synthetic_results = []
            if fetch_result and fetch_result.success:
                synthetic_results.append(
                    _result_from_fetch(fetch_result.url, fetch_result.provider, fetch_result.content)
                )
            fetches = {canonical_url(fetch_result.url): fetch_result} if fetch_result else {}
            sources = verifier.build_sources(
                synthetic_results,
                fetches,
                query=query,
                intent=plan.intent,
                domain_boosts=domain_boost_set,
            )
            conflicts = verifier.detect_conflicts(sources)
            confidence = verifier.confidence_for(sources, conflicts)
            claims = verifier.claims_for(query, confidence, sources, conflicts)
            thread_refs = await _collect_thread_refs(
                sources,
                depth=thread_depth,
                max_fetches=max_thread_fetches if max_thread_fetches is not None else settings.max_thread_fetches,
                client=client,
            )
            return ResearchOutput(
                query=query,
                profile=profile,
                intent=plan.intent,
                plan=plan,
                confidence=confidence,
                claims=claims,
                sources=sources,
                conflicts=conflicts,
                thread_refs=thread_refs,
                content_artifacts=_content_artifacts(fetches),
                provider_runs=runs,
            )

        selected = (
            provider_names
            if provider_names
            else select_search_providers(
                plan, _search_available_names(providers)
            )
        )

        tasks = []
        max_results = 5 if profile != Profile.deep else 8
        for angle in plan.angles:
            for name in selected:
                provider = providers.get(name)
                if provider and "search" in provider.capabilities:
                    tasks.append(
                        provider.timed_search(
                            angle,
                            max_results=max_results,
                            intent=plan.intent,
                            freshness=plan.freshness,
                            domain_boost=domain_boosts,
                            profile=profile.value,
                        )
                    )

        gathered = await asyncio.gather(*tasks) if tasks else []
        for provider_results, run in gathered:
            results.extend(provider_results)
            runs.append(run)

        unique_urls = []
        seen = set()
        for result in sorted(results, key=lambda item: item.score, reverse=True):
            canon = canonical_url(result.url)
            if canon in seen or result.source_type == "ai_synthesis":
                continue
            seen.add(canon)
            if result.url.startswith("http"):
                unique_urls.append(result.url)

        fetches, fetch_runs = await Reader(
            providers,
            concurrency=settings.fetch_concurrency,
            content_fallback=content_fallback,
        ).fetch_many(unique_urls, plan.fetch_limit)
        runs.extend(fetch_runs)

        sources = verifier.build_sources(
            results,
            fetches,
            query=query,
            intent=plan.intent,
            domain_boosts=domain_boost_set,
        )
        conflicts = verifier.detect_conflicts(sources)
        confidence = verifier.confidence_for(sources, conflicts)
        claims = verifier.claims_for(query, confidence, sources, conflicts)
        thread_refs = []
        if thread_depth > 0 and profile == Profile.deep:
            thread_refs = await _collect_thread_refs(
                sources,
                depth=thread_depth,
                max_fetches=max_thread_fetches if max_thread_fetches is not None else settings.max_thread_fetches,
                client=client,
            )
        return ResearchOutput(
            query=query,
            profile=profile,
            intent=plan.intent,
            plan=plan,
            confidence=confidence,
            claims=claims,
            sources=sources,
            conflicts=conflicts,
            thread_refs=thread_refs,
            content_artifacts=_content_artifacts(fetches),
            provider_runs=runs,
        )
    finally:
        if client is None:
            await close_providers(providers)


def _selected_names(
    providers: dict[str, BaseProvider], provider_names: list[str] | None
) -> list[str]:
    if provider_names:
        return [name for name in provider_names if name in providers]
    return sorted(_search_available_names(providers))


def _search_available_names(providers: dict[str, BaseProvider]) -> set[str]:
    names = set()
    for name, provider in providers.items():
        if "search" not in provider.capabilities or not provider.available:
            continue
        if name == "jina" and not provider.api_key:
            continue
        names.add(name)
    return names


def _result_from_fetch(url: str, provider: str, content: str):
    from .models import ProviderResult
    from .utils import truncate

    return ProviderResult(
        title=url,
        url=url,
        snippet=truncate(content, 500),
        provider=provider,
        score=0.7,
        source_type="primary",
    )


async def _collect_thread_refs(
    sources,
    *,
    depth: int,
    max_fetches: int,
    client: httpx.AsyncClient | None,
):
    if depth <= 0 or max_fetches <= 0:
        return []
    thread_reader = ThreadReader(client=client)
    try:
        return await thread_reader.collect_refs(sources, max_fetches=max_fetches, depth=depth)
    finally:
        if client is None:
            await thread_reader.close()


def _content_artifacts(fetches) -> list[ContentArtifact]:
    artifacts: list[ContentArtifact] = []
    for fetch in fetches.values():
        for key, value in fetch.artifacts.items():
            artifacts.append(
                ContentArtifact(
                    source_url=fetch.url,
                    provider=fetch.provider,
                    kind=key,
                    url=value if value.startswith("http") else None,
                    path=value if not value.startswith("http") else None,
                )
            )
    return artifacts
