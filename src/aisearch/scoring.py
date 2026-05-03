from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from .models import QueryType


INTENT_WEIGHTS = {
    QueryType.factual: {"keyword": 0.4, "freshness": 0.1, "authority": 0.5},
    QueryType.status: {"keyword": 0.3, "freshness": 0.5, "authority": 0.2},
    QueryType.comparison: {"keyword": 0.4, "freshness": 0.2, "authority": 0.4},
    QueryType.tutorial: {"keyword": 0.4, "freshness": 0.1, "authority": 0.5},
    QueryType.exploratory: {"keyword": 0.3, "freshness": 0.2, "authority": 0.5},
    QueryType.general: {"keyword": 0.35, "freshness": 0.2, "authority": 0.45},
    QueryType.news: {"keyword": 0.3, "freshness": 0.6, "authority": 0.1},
    QueryType.resource: {"keyword": 0.5, "freshness": 0.1, "authority": 0.4},
    QueryType.technical: {"keyword": 0.35, "freshness": 0.15, "authority": 0.5},
    QueryType.academic: {"keyword": 0.3, "freshness": 0.15, "authority": 0.55},
    QueryType.url: {"keyword": 0.2, "freshness": 0.1, "authority": 0.7},
}


DOMAIN_SCORES = {
    "github.com": 1.0,
    "stackoverflow.com": 1.0,
    "developer.mozilla.org": 1.0,
    "wikipedia.org": 1.0,
    "arxiv.org": 1.0,
    "docs.python.org": 1.0,
    "nodejs.org": 1.0,
    "react.dev": 1.0,
    "nextjs.org": 1.0,
    "openai.com": 1.0,
    "anthropic.com": 1.0,
    "news.ycombinator.com": 0.8,
    "reddit.com": 0.75,
    "dev.to": 0.75,
    "infoq.com": 0.75,
    "medium.com": 0.6,
    "hackernoon.com": 0.6,
}


def composite_score(
    *,
    query: str,
    title: str,
    snippet: str,
    content_preview: str,
    url: str,
    published_at: str | None,
    intent: QueryType,
    domain_boosts: set[str] | None = None,
) -> float:
    weights = INTENT_WEIGHTS.get(intent, INTENT_WEIGHTS[QueryType.general])
    keyword = keyword_score(query, f"{title} {snippet} {content_preview}")
    freshness = freshness_score(published_at, f"{title} {snippet} {content_preview}")
    authority = authority_score(url, domain_boosts or set())
    score = (
        weights["keyword"] * keyword
        + weights["freshness"] * freshness
        + weights["authority"] * authority
    )
    return round(max(0.0, min(score, 1.0)), 4)


def keyword_score(query: str, text: str) -> float:
    terms = {
        token
        for token in re.findall(r"[\w\u4e00-\u9fff]+", query.lower())
        if len(token) > 1
    }
    if not terms:
        return 0.5
    lowered = text.lower()
    matches = sum(1 for term in terms if term in lowered)
    return min(1.0, matches / len(terms))


def freshness_score(published_at: str | None, text: str = "") -> float:
    if published_at:
        parsed = _parse_date(published_at)
        if parsed:
            days_old = (datetime.now(timezone.utc) - parsed).days
            if days_old <= 1:
                return 1.0
            if days_old <= 7:
                return 0.9
            if days_old <= 30:
                return 0.7
            if days_old <= 90:
                return 0.5
            if days_old <= 365:
                return 0.3
            return 0.1

    years = [int(year) for year in re.findall(r"\b(20\d{2}|19\d{2})\b", text)]
    if years:
        latest = max(years)
        diff = datetime.now(timezone.utc).year - latest
        if diff <= 0:
            return 0.9
        if diff == 1:
            return 0.6
        if diff <= 3:
            return 0.4
        return 0.2
    return 0.5


def authority_score(url: str, domain_boosts: set[str] | None = None) -> float:
    domain_boosts = domain_boosts or set()
    host = _hostname(url)
    if not host:
        return 0.3

    score = 0.4
    for known, known_score in DOMAIN_SCORES.items():
        if host == known or host.endswith("." + known):
            score = known_score
            break
    if host.startswith("docs.") or ".docs." in host:
        score = max(score, 0.85)

    for boost in domain_boosts:
        boost = boost.lower().removeprefix("www.")
        if host == boost or host.endswith("." + boost):
            score = min(1.0, score + 0.2)
            break
    return round(score, 4)


def _hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


def _parse_date(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    text = text.removesuffix("Z") + ("+00:00" if text.endswith("Z") else "")
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
