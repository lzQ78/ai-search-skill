from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


PROVIDER_ENV = {
    "tavily": "TAVILY_API_KEY",
    "brave": "BRAVE_API_KEY",
    "exa": "EXA_API_KEY",
    "firecrawl": "FIRECRAWL_API_KEY",
    "jina": "JINA_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "mineru": "MINERU_API_TOKEN",
}


class Settings(BaseModel):
    api_keys: dict[str, str] = Field(default_factory=dict)
    request_timeout: float = 30.0
    fetch_concurrency: int = 4
    max_thread_fetches: int = 3

    def key_for(self, provider: str) -> str | None:
        value = self.api_keys.get(provider, "")
        return value or None


def load_settings(dotenv_path: str | Path | None = None) -> Settings:
    path = Path(dotenv_path) if dotenv_path else Path.cwd() / ".env"
    if path.exists():
        load_dotenv(path, override=False)

    keys = {
        provider: os.getenv(env_name, "").strip()
        for provider, env_name in PROVIDER_ENV.items()
    }
    timeout = float(os.getenv("AISEARCH_REQUEST_TIMEOUT", "30"))
    fetch_concurrency = int(os.getenv("AISEARCH_FETCH_CONCURRENCY", "4"))
    max_thread_fetches = int(os.getenv("AISEARCH_MAX_THREAD_FETCHES", "3"))
    return Settings(
        api_keys=keys,
        request_timeout=timeout,
        fetch_concurrency=max(1, fetch_concurrency),
        max_thread_fetches=max(0, max_thread_fetches),
    )
