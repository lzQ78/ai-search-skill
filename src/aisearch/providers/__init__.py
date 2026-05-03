from __future__ import annotations

import httpx

from ..config import Settings
from .base import BaseProvider
from .brave import BraveProvider
from .exa import ExaProvider
from .firecrawl import FirecrawlProvider
from .jina import JinaProvider
from .mineru import MinerUProvider
from .perplexity import PerplexityProvider
from .tavily import TavilyProvider


PROVIDER_CLASSES: dict[str, type[BaseProvider]] = {
    "tavily": TavilyProvider,
    "brave": BraveProvider,
    "exa": ExaProvider,
    "firecrawl": FirecrawlProvider,
    "jina": JinaProvider,
    "mineru": MinerUProvider,
    "perplexity": PerplexityProvider,
}


def build_providers(
    settings: Settings, client: httpx.AsyncClient | None = None
) -> dict[str, BaseProvider]:
    return {
        name: provider_cls(settings, client=client)
        for name, provider_cls in PROVIDER_CLASSES.items()
    }
