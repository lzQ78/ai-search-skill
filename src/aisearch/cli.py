from __future__ import annotations

import asyncio
from enum import Enum
from typing import Annotated

import typer

from .config import load_settings
from .models import Profile, QueryType
from .orchestrator import run_fetch, run_research, run_search
from .providers import build_providers
from .publisher import to_json


class OutputFormat(str, Enum):
    json = "json"


class IntentOption(str, Enum):
    auto = "auto"
    factual = "factual"
    status = "status"
    comparison = "comparison"
    tutorial = "tutorial"
    exploratory = "exploratory"
    news = "news"
    resource = "resource"
    technical = "technical"
    academic = "academic"


class ContentFallbackOption(str, Enum):
    auto = "auto"
    off = "off"
    mineru = "mineru"


app = typer.Typer(
    no_args_is_help=True,
    help="Multi-provider search orchestration for AI agent skills.",
)


@app.command()
def doctor() -> None:
    """Show provider availability and local configuration state."""
    settings = load_settings()
    providers = build_providers(settings)
    try:
        data = {
            "schema_version": "1.0",
            "providers": [provider.status().model_dump(mode="json") for provider in providers.values()],
        }
        typer.echo(to_json(data))
    finally:
        asyncio.run(_close(providers))


@app.command("providers")
def providers_cmd() -> None:
    """List provider capabilities."""
    settings = load_settings()
    providers = build_providers(settings)
    try:
        data = {
            "schema_version": "1.0",
            "providers": [provider.status().model_dump(mode="json") for provider in providers.values()],
        }
        typer.echo(to_json(data))
    finally:
        asyncio.run(_close(providers))


@app.command()
def research(
    query: Annotated[str, typer.Option("--query", "-q")],
    profile: Annotated[Profile, typer.Option("--profile")] = Profile.balanced,
    providers: Annotated[str | None, typer.Option("--providers")] = None,
    intent: Annotated[IntentOption, typer.Option("--intent")] = IntentOption.auto,
    domain_boost: Annotated[str | None, typer.Option("--domain-boost")] = None,
    thread_depth: Annotated[int, typer.Option("--thread-depth", min=0, max=3)] = 0,
    max_thread_fetches: Annotated[int | None, typer.Option("--max-thread-fetches", min=0)] = None,
    content_fallback: Annotated[
        ContentFallbackOption, typer.Option("--content-fallback")
    ] = ContentFallbackOption.auto,
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.json,
) -> None:
    """Run the full planner, search, fetch, verification, and JSON publish flow."""
    provider_names = _split_csv(providers)
    boost_domains = _split_csv(domain_boost)
    settings = load_settings()
    output = asyncio.run(
        run_research(
            settings,
            query=query,
            profile=profile,
            provider_names=provider_names,
            intent=None if intent == IntentOption.auto else QueryType(intent.value),
            domain_boosts=boost_domains,
            thread_depth=thread_depth,
            max_thread_fetches=max_thread_fetches,
            content_fallback=content_fallback.value,
        )
    )
    _emit(output, format)


@app.command()
def search(
    query: Annotated[str, typer.Option("--query", "-q")],
    providers: Annotated[str | None, typer.Option("--providers")] = None,
    max_results: Annotated[int, typer.Option("--max-results")] = 5,
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.json,
) -> None:
    """Run provider search only, without source verification."""
    provider_names = _split_csv(providers)
    settings = load_settings()
    output = asyncio.run(
        run_search(
            settings,
            query=query,
            provider_names=provider_names,
            max_results=max_results,
        )
    )
    _emit(output, format)


@app.command()
def fetch(
    url: Annotated[str, typer.Option("--url")],
    content_fallback: Annotated[
        ContentFallbackOption, typer.Option("--content-fallback")
    ] = ContentFallbackOption.auto,
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.json,
) -> None:
    """Fetch a URL through Firecrawl, Jina, Tavily, then Exa fallback."""
    settings = load_settings()
    output = asyncio.run(run_fetch(settings, url=url, content_fallback=content_fallback.value))
    _emit(output, format)


@app.command()
def init() -> None:
    """Print local setup guidance. This command does not write files."""
    typer.echo(
        "Copy .env.example to .env, fill provider keys, then run: python -m aisearch doctor"
    )


async def _close(providers) -> None:
    for provider in providers.values():
        await provider.close()


def _split_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [part.strip().lower() for part in value.split(",") if part.strip()]


def _emit(model, format: OutputFormat) -> None:
    if format != OutputFormat.json:
        raise typer.BadParameter("Only json output is supported in V1.")
    typer.echo(to_json(model))


def main() -> None:
    app()
