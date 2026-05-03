import asyncio

from aisearch.config import Settings
from aisearch.providers.brave import BraveProvider
from aisearch.providers.exa import ExaProvider
from aisearch.providers.tavily import TavilyProvider
from aisearch.models import QueryType


def test_tavily_parse_results_normalizes_fields():
    provider = TavilyProvider(Settings(api_keys={"tavily": "key"}))
    try:
        results = provider.parse_results(
            {
                "results": [
                    {
                        "title": "Title",
                        "url": "https://example.com",
                        "content": "Snippet",
                        "score": 0.91,
                        "published_date": "2026-01-01",
                    }
                ]
            }
        )
    finally:
        asyncio.run(provider.close())

    assert results[0].provider == "tavily"
    assert results[0].url == "https://example.com"
    assert results[0].published_at == "2026-01-01"


def test_brave_parse_results_normalizes_fields():
    provider = BraveProvider(Settings(api_keys={"brave": "key"}))
    try:
        results = provider.parse_results(
            {
                "web": {
                    "results": [
                        {
                            "title": "Title",
                            "url": "https://example.com",
                            "description": "Snippet",
                        }
                    ]
                }
            }
        )
    finally:
        asyncio.run(provider.close())

    assert results[0].provider == "brave"
    assert results[0].snippet == "Snippet"


def test_exa_search_uses_intent_type_and_freshness(monkeypatch):
    provider = ExaProvider(Settings(api_keys={"exa": "key"}))
    captured = {}

    async def fake_post(url, payload, headers):
        captured["payload"] = payload
        return {"results": []}

    monkeypatch.setattr(provider, "_json_post", fake_post)
    try:
        asyncio.run(
            provider.search_with_context(
                "query",
                intent=QueryType.resource,
                freshness="pw",
                profile="balanced",
            )
        )
    finally:
        asyncio.run(provider.close())

    assert captured["payload"]["type"] == "instant"
    assert "startPublishedDate" in captured["payload"]
    assert captured["payload"]["contents"]["highlights"]["maxCharacters"] == 1200


def test_tavily_search_maps_freshness(monkeypatch):
    provider = TavilyProvider(Settings(api_keys={"tavily": "key"}))
    captured = {}

    async def fake_post(url, payload, headers):
        captured["payload"] = payload
        return {"results": []}

    monkeypatch.setattr(provider, "_json_post", fake_post)
    try:
        asyncio.run(provider.search_with_context("query", freshness="pm"))
    finally:
        asyncio.run(provider.close())

    assert captured["payload"]["time_range"] == "month"
