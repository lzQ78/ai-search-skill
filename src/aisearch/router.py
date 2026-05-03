from __future__ import annotations

from .models import QueryPlan, QueryType


ROUTES = {
    QueryType.url: ["firecrawl", "jina", "tavily", "exa"],
    QueryType.factual: ["brave", "exa", "tavily", "jina", "perplexity"],
    QueryType.status: ["tavily", "brave", "exa", "perplexity", "jina"],
    QueryType.comparison: ["exa", "tavily", "brave", "jina", "perplexity"],
    QueryType.tutorial: ["brave", "exa", "tavily", "jina", "perplexity"],
    QueryType.exploratory: ["exa", "tavily", "brave", "jina", "perplexity"],
    QueryType.resource: ["brave", "exa", "jina", "tavily", "perplexity"],
    QueryType.news: ["tavily", "brave", "exa", "perplexity", "jina"],
    QueryType.technical: ["brave", "exa", "tavily", "jina", "perplexity"],
    QueryType.academic: ["exa", "jina", "brave", "tavily", "perplexity"],
    QueryType.general: ["exa", "tavily", "brave", "jina", "perplexity"],
}


def select_search_providers(plan: QueryPlan, available: set[str]) -> list[str]:
    route = ROUTES[plan.query_type]
    selected = [name for name in route if name in available]
    return selected[: plan.max_search_providers]


def fetch_provider_order(available: set[str]) -> list[str]:
    return [name for name in ["firecrawl", "jina", "tavily", "exa"] if name in available]
