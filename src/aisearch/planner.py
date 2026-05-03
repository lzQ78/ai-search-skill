from __future__ import annotations

import re

from .models import Freshness, Profile, QueryPlan, QueryType
from .utils import looks_like_url


NEWS_KEYWORDS = {
    "news",
    "headline",
    "headlines",
    "announcement",
    "announced",
    "launch",
    "launched",
    "breaking",
    "新闻",
    "消息",
    "发布",
    "宣布",
}

TIME_KEYWORDS = {
    "latest",
    "recent",
    "today",
    "current",
    "now",
    "news",
    "2025",
    "2026",
    "最新",
    "最近",
    "今天",
    "当前",
    "新闻",
}

STATUS_KEYWORDS = {
    "status",
    "progress",
    "roadmap",
    "current state",
    "latest progress",
    "现状",
    "进展",
    "最新进展",
    "当前状态",
}

COMPARISON_KEYWORDS = {
    " vs ",
    " versus ",
    "compare",
    "comparison",
    "difference",
    "differences",
    "better",
    "should i use",
    "对比",
    "比较",
    "区别",
    "差异",
    "哪个好",
    "值不值得",
}

TUTORIAL_KEYWORDS = {
    "how to",
    "tutorial",
    "guide",
    "step by step",
    "walkthrough",
    "怎么",
    "如何",
    "教程",
    "指南",
    "入门",
}

RESOURCE_KEYWORDS = {
    "official",
    "homepage",
    "website",
    "documentation",
    "docs",
    "github",
    "repository",
    "download",
    "官网",
    "官方网站",
    "文档",
    "仓库",
    "源码",
    "下载",
}

FACTUAL_KEYWORDS = {
    "what is",
    "who is",
    "when did",
    "definition",
    "define",
    "meaning",
    "是什么",
    "定义",
    "什么意思",
}

EXPLORATORY_KEYWORDS = {
    "overview",
    "ecosystem",
    "landscape",
    "deep dive",
    "research",
    "analysis",
    "调研",
    "研究",
    "生态",
    "深入",
    "分析",
}

TECH_KEYWORDS = {
    "api",
    "sdk",
    "library",
    "framework",
    "release",
    "version",
    "package",
    "docs",
    "文档",
    "开源",
    "项目",
    "版本",
}

ACADEMIC_KEYWORDS = {
    "paper",
    "arxiv",
    "study",
    "research",
    "benchmark",
    "论文",
    "研究",
    "基准",
}


PROFILE_BUDGETS = {
    Profile.quick: (2, 2),
    Profile.balanced: (4, 5),
    Profile.deep: (6, 10),
}


def build_plan(
    query: str,
    profile: Profile = Profile.balanced,
    intent: QueryType | None = None,
) -> QueryPlan:
    lowered = query.lower()
    time_sensitive = any(keyword in lowered for keyword in TIME_KEYWORDS)

    query_type = intent or _detect_query_type(query, lowered, time_sensitive)
    if looks_like_url(query):
        query_type = QueryType.url
    freshness = _freshness_for(query_type, lowered, profile)

    max_providers, fetch_limit = PROFILE_BUDGETS[profile]
    return QueryPlan(
        query=query,
        query_type=query_type,
        intent=query_type,
        profile=profile,
        time_sensitive=time_sensitive,
        freshness=freshness,
        angles=_angles_for(query, query_type, time_sensitive, profile),
        max_search_providers=max_providers,
        fetch_limit=fetch_limit,
    )


def _detect_query_type(query: str, lowered: str, time_sensitive: bool) -> QueryType:
    padded = f" {lowered} "
    if any(keyword in padded for keyword in COMPARISON_KEYWORDS):
        return QueryType.comparison
    if any(keyword in lowered for keyword in TUTORIAL_KEYWORDS):
        return QueryType.tutorial
    if any(keyword in lowered for keyword in RESOURCE_KEYWORDS):
        return QueryType.resource
    if any(keyword in lowered for keyword in STATUS_KEYWORDS):
        return QueryType.status
    if any(keyword in lowered for keyword in NEWS_KEYWORDS):
        return QueryType.news
    if any(keyword in lowered for keyword in FACTUAL_KEYWORDS):
        return QueryType.factual
    if any(keyword in lowered for keyword in ACADEMIC_KEYWORDS):
        return QueryType.academic
    if any(keyword in lowered for keyword in TECH_KEYWORDS):
        return QueryType.technical
    if time_sensitive:
        return QueryType.status
    if any(keyword in lowered for keyword in EXPLORATORY_KEYWORDS):
        return QueryType.exploratory
    return QueryType.general


def _freshness_for(
    query_type: QueryType, lowered: str, profile: Profile
) -> Freshness | None:
    if query_type == QueryType.news:
        if "today" in lowered or "今天" in lowered or "本日" in lowered:
            return "pd"
        return "pw"
    if query_type == QueryType.status:
        return "pw" if profile == Profile.quick else "pm"
    if query_type in {QueryType.comparison, QueryType.tutorial}:
        return "py"
    return None


def _angles_for(
    query: str, query_type: QueryType, time_sensitive: bool, profile: Profile
) -> list[str]:
    if query_type == QueryType.url:
        return [query]

    angles = [query]
    if profile == Profile.quick:
        return angles

    if query_type == QueryType.factual:
        angles.extend([f"{query} definition", f"{query} explained overview"])
    elif query_type == QueryType.status:
        angles.extend([f"{query} latest 2026", f"{query} official update"])
    elif query_type == QueryType.comparison:
        parts = _comparison_parts(query)
        angles.extend([f"{part} advantages" for part in parts])
        angles.append(f"{query} tradeoffs")
    elif query_type == QueryType.tutorial:
        angles.extend([f"{query} tutorial", f"{query} guide step by step"])
    elif query_type == QueryType.resource:
        angles.extend([f"{query} official documentation", f"{query} GitHub"])
    elif query_type == QueryType.technical:
        angles.extend([f"{query} official documentation", f"{query} GitHub"])
    elif query_type == QueryType.academic:
        angles.extend([f"{query} paper", f"{query} benchmark"])
    elif query_type == QueryType.news or time_sensitive:
        angles.extend([f"{query} latest", f"{query} official"])
    else:
        compact = re.sub(r"\s+", " ", query).strip()
        angles.extend([f"{compact} overview", f"{compact} sources"])

    if profile == Profile.deep:
        angles.append(f"{query} criticism limitations")

    return list(dict.fromkeys(angles))


def _comparison_parts(query: str) -> list[str]:
    normalized = re.sub(r"\s+(?:vs|versus)\s+", " vs ", query, flags=re.IGNORECASE)
    normalized = re.sub(r"\s*(?:和|与|对比|比较|区别)\s*", " vs ", normalized)
    parts = [
        part.strip(" ?？,，")
        for part in normalized.split(" vs ")
        if part.strip(" ?？,，")
    ]
    return parts[:3]
