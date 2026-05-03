from aisearch.models import FetchResult, ProviderResult, QueryType
from aisearch.scoring import authority_score
from aisearch.utils import canonical_url
from aisearch.verifier import Verifier


def test_canonical_url_removes_tracking_params():
    assert (
        canonical_url("https://Example.com/path/?utm_source=x&b=2&a=1#frag")
        == "https://example.com/path?a=1&b=2"
    )


def test_verifier_dedupes_and_allows_high_confidence_with_two_domains_and_fetch():
    results = [
        ProviderResult(
            title="A",
            url="https://a.example/news?utm_source=x",
            snippet="Python 2026 release notes",
            provider="tavily",
            score=0.8,
            source_type="secondary",
        ),
        ProviderResult(
            title="A duplicate",
            url="https://a.example/news",
            snippet="duplicate",
            provider="brave",
            score=0.2,
            source_type="secondary",
        ),
        ProviderResult(
            title="B",
            url="https://b.example/news",
            snippet="Python 2026 release notes",
            provider="brave",
            score=0.7,
            source_type="secondary",
        ),
    ]
    fetches = {
        "https://a.example/news": FetchResult(
            url="https://a.example/news",
            provider="jina",
            success=True,
            content="original source content",
        )
    }
    verifier = Verifier()

    sources = verifier.build_sources(results, fetches)
    conflicts = verifier.detect_conflicts(sources)

    assert len(sources) == 2
    assert verifier.confidence_for(sources, conflicts) == "high"


def test_perplexity_alone_cannot_be_high_confidence():
    result = ProviderResult(
        title="Perplexity synthesis",
        url="perplexity://synthesis/test",
        snippet="answer",
        provider="perplexity",
        score=0.9,
        source_type="ai_synthesis",
    )
    verifier = Verifier()

    sources = verifier.build_sources([result], {})

    assert verifier.confidence_for(sources, []) == "low"


def test_conflict_detection_flags_different_years():
    results = [
        ProviderResult(
            title="Release in 2025",
            url="https://a.example/item",
            snippet="The product launched in 2025.",
            provider="tavily",
            score=0.8,
            source_type="secondary",
        ),
        ProviderResult(
            title="Release in 2026",
            url="https://b.example/item",
            snippet="The product launched in 2026.",
            provider="brave",
            score=0.8,
            source_type="secondary",
        ),
    ]
    verifier = Verifier()

    sources = verifier.build_sources(results, {})
    conflicts = verifier.detect_conflicts(sources)

    assert len(conflicts) == 1
    assert set(conflicts[0].source_ids) == {"s1", "s2"}


def test_authority_score_supports_domain_boost():
    assert authority_score("https://unknown.example/post") == 0.4
    assert authority_score("https://unknown.example/post", {"unknown.example"}) == 0.6


def test_verifier_uses_intent_scoring_inputs():
    results = [
        ProviderResult(
            title="Official docs",
            url="https://docs.python.org/3/library/asyncio.html",
            snippet="asyncio Python official documentation",
            provider="brave",
            score=0.5,
            source_type="secondary",
        )
    ]

    sources = Verifier().build_sources(
        results,
        {},
        query="Python asyncio documentation",
        intent=QueryType.resource,
        domain_boosts={"python.org"},
    )

    assert sources[0].score > 0.7
