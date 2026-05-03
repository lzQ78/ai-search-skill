from __future__ import annotations

import time
from abc import ABC
from typing import Any

import httpx

from ..config import Settings
from ..models import FetchResult, Freshness, ProviderResult, ProviderRun, ProviderStatus, QueryType


class ProviderError(RuntimeError):
    pass


class BaseProvider(ABC):
    name = "base"
    env_var: str | None = None
    capabilities: tuple[str, ...] = ()
    requires_key = True

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self._external_client = client is not None
        self._client = client

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            timeout = httpx.Timeout(self.settings.request_timeout, connect=6.0)
            self._client = httpx.AsyncClient(timeout=timeout)
        return self._client

    @property
    def api_key(self) -> str | None:
        return self.settings.key_for(self.name)

    @property
    def available(self) -> bool:
        return bool(self.api_key) or not self.requires_key

    def status(self) -> ProviderStatus:
        reason = None if self.available else f"missing {self.env_var}"
        return ProviderStatus(
            name=self.name,
            env_var=self.env_var,
            available=self.available,
            capabilities=list(self.capabilities),
            reason=reason,
        )

    async def close(self) -> None:
        if self._client is not None and not self._external_client:
            await self._client.aclose()

    async def search(self, query: str, max_results: int = 5) -> list[ProviderResult]:
        raise NotImplementedError

    async def search_with_context(
        self,
        query: str,
        max_results: int = 5,
        intent: QueryType | None = None,
        freshness: Freshness | None = None,
        domain_boost: list[str] | None = None,
        profile: str | None = None,
    ) -> list[ProviderResult]:
        return await self.search(query, max_results=max_results)

    async def fetch(self, url: str) -> FetchResult:
        raise NotImplementedError

    async def timed_search(
        self,
        query: str,
        max_results: int = 5,
        intent: QueryType | None = None,
        freshness: Freshness | None = None,
        domain_boost: list[str] | None = None,
        profile: str | None = None,
    ) -> tuple[list[ProviderResult], ProviderRun]:
        start = time.perf_counter()
        try:
            if not self.available:
                return [], self._run("search", "skipped", 0, start, f"missing {self.env_var}")
            results = await self.search_with_context(
                query,
                max_results=max_results,
                intent=intent,
                freshness=freshness,
                domain_boost=domain_boost,
                profile=profile,
            )
            return results, self._run("search", "ok", len(results), start)
        except Exception as exc:
            return [], self._run("search", "error", 0, start, _error_text(exc))

    async def timed_fetch(self, url: str) -> tuple[FetchResult | None, ProviderRun]:
        start = time.perf_counter()
        try:
            if not self.available:
                return None, self._run("fetch", "skipped", 0, start, f"missing {self.env_var}")
            result = await self.fetch(url)
            count = 1 if result.success else 0
            status = "ok" if result.success else "error"
            return result, self._run("fetch", status, count, start, result.error)
        except Exception as exc:
            return None, self._run("fetch", "error", 0, start, _error_text(exc))

    def _run(
        self,
        action: str,
        status: str,
        count: int,
        start: float,
        error: str | None = None,
    ) -> ProviderRun:
        return ProviderRun(
            provider=self.name,
            action=action,  # type: ignore[arg-type]
            status=status,  # type: ignore[arg-type]
            results_count=count,
            duration_ms=int((time.perf_counter() - start) * 1000),
            error=error,
        )

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if extra:
            headers.update(extra)
        return headers

    async def _json_post(
        self, url: str, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        response = await self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


def text_from(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(text_from(item) for item in value)
    if isinstance(value, dict):
        return " ".join(text_from(item) for item in value.values())
    return str(value)


def _error_text(exc: Exception) -> str:
    text = str(exc).strip()
    return text or exc.__class__.__name__
