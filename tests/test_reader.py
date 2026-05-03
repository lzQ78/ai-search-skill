from aisearch.models import FetchResult, ProviderRun
from aisearch.reader import Reader


class FakeFetchProvider:
    def __init__(self, name, success):
        self.name = name
        self.available = True
        self.capabilities = ("fetch",)
        self.success = success

    async def timed_fetch(self, url):
        result = FetchResult(
            url=url,
            provider=self.name,
            success=self.success,
            content="ok" if self.success else "",
            error=None if self.success else "failed",
        )
        run = ProviderRun(
            provider=self.name,
            action="fetch",
            status="ok" if self.success else "error",
            results_count=1 if self.success else 0,
        )
        return result, run


def test_reader_falls_back_from_firecrawl_to_jina():
    import asyncio

    reader = Reader(
        {
            "firecrawl": FakeFetchProvider("firecrawl", False),
            "jina": FakeFetchProvider("jina", True),
        }
    )

    result, runs = asyncio.run(reader.fetch_url("https://example.com"))

    assert result is not None
    assert result.provider == "jina"
    assert [run.provider for run in runs] == ["firecrawl", "jina"]


def test_reader_prefers_mineru_for_anti_bot_domains():
    import asyncio

    reader = Reader(
        {
            "firecrawl": FakeFetchProvider("firecrawl", True),
            "mineru": FakeFetchProvider("mineru", True),
        }
    )

    result, runs = asyncio.run(reader.fetch_url("https://mp.weixin.qq.com/s/example"))

    assert result is not None
    assert result.provider == "mineru"
    assert [run.provider for run in runs] == ["mineru"]


def test_reader_fetch_many_dedupes_urls():
    import asyncio

    reader = Reader({"jina": FakeFetchProvider("jina", True)}, concurrency=2)

    fetched, runs = asyncio.run(
        reader.fetch_many(
            [
                "https://example.com/a?utm_source=x",
                "https://example.com/a",
                "https://example.com/b",
            ],
            limit=5,
        )
    )

    assert sorted(fetched) == ["https://example.com/a", "https://example.com/b"]
    assert len(runs) == 2
