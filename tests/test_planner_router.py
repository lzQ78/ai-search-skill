from aisearch.models import Profile, QueryType
from aisearch.planner import build_plan
from aisearch.router import select_search_providers


def test_planner_detects_technical_query():
    plan = build_plan("GitHub project API docs", Profile.balanced)

    assert plan.query_type == QueryType.resource
    assert plan.max_search_providers == 4
    assert plan.fetch_limit == 5
    assert plan.intent == QueryType.resource
    assert "GitHub project API docs official documentation" in plan.angles


def test_router_respects_availability_and_budget():
    plan = build_plan("latest AI news", Profile.quick)

    selected = select_search_providers(plan, {"tavily", "brave", "exa"})

    assert selected == ["tavily", "brave"]


def test_planner_detects_comparison_and_sets_year_freshness():
    plan = build_plan("Bun vs Deno", Profile.balanced)

    assert plan.intent == QueryType.comparison
    assert plan.freshness == "py"
    assert "Bun advantages" in plan.angles
    assert "Deno advantages" in plan.angles


def test_planner_detects_status_query():
    plan = build_plan("OpenAI agents latest progress", Profile.deep)

    assert plan.intent == QueryType.status
    assert plan.freshness == "pm"
    assert "OpenAI agents latest progress latest 2026" in plan.angles


def test_planner_allows_explicit_intent_override():
    plan = build_plan("Python", Profile.balanced, intent=QueryType.tutorial)

    assert plan.intent == QueryType.tutorial
    assert "Python tutorial" in plan.angles
