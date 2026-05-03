from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from .models import FetchResult, ProviderRun
from .providers.base import BaseProvider
from .router import fetch_provider_order
from .utils import canonical_url


ANTI_BOT_DOMAINS = {
    "mp.weixin.qq.com",
    "zhihu.com",
    "zhuanlan.zhihu.com",
    "xiaohongshu.com",
}


class Reader:
    def __init__(
        self,
        providers: dict[str, BaseProvider],
        concurrency: int = 4,
        content_fallback: str = "auto",
    ):
        self.providers = providers
        self.concurrency = max(1, concurrency)
        self.content_fallback = content_fallback

    async def fetch_url(self, url: str) -> tuple[FetchResult | None, list[ProviderRun]]:
        runs: list[ProviderRun] = []
        available = {name for name, provider in self.providers.items() if provider.available}
        if self._prefer_mineru(url):
            result, run = await self._fetch_mineru(url)
            runs.append(run)
            if result and result.success:
                return result, runs

        for name in fetch_provider_order(available):
            provider = self.providers[name]
            if "fetch" not in provider.capabilities:
                continue
            result, run = await provider.timed_fetch(url)
            runs.append(run)
            if result and result.success:
                return result, runs

        if self.content_fallback in {"auto", "mineru"} and not self._prefer_mineru(url):
            result, run = await self._fetch_mineru(url)
            runs.append(run)
            if result and result.success:
                return result, runs
        return None, runs

    async def fetch_many(
        self, urls: list[str], limit: int
    ) -> tuple[dict[str, FetchResult], list[ProviderRun]]:
        ordered_urls: list[str] = []
        seen: set[str] = set()
        for url in urls:
            canon = canonical_url(url)
            if canon in seen:
                continue
            seen.add(canon)
            ordered_urls.append(url)
            if len(ordered_urls) >= limit:
                break

        semaphore = asyncio.Semaphore(self.concurrency)

        async def _bounded_fetch(target: str):
            async with semaphore:
                return target, await self.fetch_url(target)

        gathered = await asyncio.gather(*(_bounded_fetch(url) for url in ordered_urls))
        fetched: dict[str, FetchResult] = {}
        runs: list[ProviderRun] = []
        for url, (result, result_runs) in gathered:
            runs.extend(result_runs)
            if result and result.success:
                fetched[canonical_url(url)] = result
        return fetched, runs

    def _prefer_mineru(self, url: str) -> bool:
        if self.content_fallback not in {"auto", "mineru"}:
            return False
        host = (urlparse(url).hostname or "").lower()
        return any(host == domain or host.endswith("." + domain) for domain in ANTI_BOT_DOMAINS)

    async def _fetch_mineru(self, url: str) -> tuple[FetchResult | None, ProviderRun]:
        provider = self.providers.get("mineru")
        if provider is None:
            return None, ProviderRun(
                provider="mineru",
                action="fetch",
                status="skipped",
                error="provider unavailable",
            )
        return await provider.timed_fetch(url)
