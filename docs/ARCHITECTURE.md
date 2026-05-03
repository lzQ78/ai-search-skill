# Architecture

AI Search Skill is built as a small evidence pipeline.

The CLI receives a query, creates a query plan, routes the plan to available
providers, fetches original pages, verifies and scores evidence, and publishes a
stable JSON bundle.

## Data Flow

```text
query
  -> planner
  -> router
  -> providers
  -> reader
  -> verifier + scoring
  -> thread reader
  -> JSON output
```

## Core Modules

| Module | Responsibility |
|---|---|
| `SKILL.md` | Root agent skill instructions and default command contract. |
| `cli.py` | Parses commands and options with Typer. |
| `config.py` | Loads `.env` and provider credentials. |
| `models.py` | Defines Pydantic contracts for plans, sources, claims, conflicts, and outputs. |
| `planner.py` | Detects intent, expands query angles, sets freshness and budgets. |
| `router.py` | Chooses provider order for each intent. |
| `orchestrator.py` | Coordinates the full research/search/fetch flow. |
| `reader.py` | Fetches pages with fallback order and limited concurrency. |
| `verifier.py` | Deduplicates results, builds sources, detects conflicts, and assigns confidence. |
| `scoring.py` | Computes keyword, freshness, authority, and boosted domain scores. |
| `thread_reader.py` | Extracts references from GitHub issues, PRs, and thread-like pages. |
| `providers/` | Contains one adapter per external provider. |

## Research Flow

1. `build_plan()` classifies the query into an intent.
2. The plan creates query angles and search/fetch budgets.
3. `select_search_providers()` chooses providers that match the intent and are
   available locally.
4. Providers run search calls concurrently.
5. Search results are deduplicated by canonical URL.
6. `Reader` fetches top source URLs with a bounded concurrency limit.
7. `Verifier` builds `Source` records, assigns confidence, and flags simple
   conflicts.
8. `ThreadReader` optionally extracts issue, PR, commit, and external references.
9. `ResearchOutput` is serialized as JSON.

## Intent Model

The planner supports these intents:

| Intent | Typical query |
|---|---|
| `factual` | What is X? Definition of X. |
| `status` | Latest progress, roadmap, current state. |
| `comparison` | X vs Y, differences, tradeoffs. |
| `tutorial` | How to do X, guide, walkthrough. |
| `exploratory` | Landscape, ecosystem, deep dive. |
| `news` | This week, breaking news, announcements. |
| `resource` | Official docs, GitHub, homepage, download. |
| `technical` | API, SDK, framework, package, release. |
| `academic` | Paper, benchmark, arXiv, study. |
| `url` | Direct URL fetch/research. |

Intent affects query expansion, freshness, provider routing, and source scoring.

## Provider Contract

Every provider adapter inherits from `BaseProvider`.

Search providers return `ProviderResult` objects:

```text
title, url, snippet, provider, score, published_at, source_type, raw
```

Fetch providers return `FetchResult` objects:

```text
url, provider, success, title, content, error, artifacts
```

Provider failures are captured as `ProviderRun` records. They should not crash a full
research run unless the error is outside provider execution.

## Confidence Model

Confidence is intentionally conservative:

- `low`: no independent non-AI source, or only one independent domain.
- `medium`: multiple domains but no fetched source, or detected conflicts.
- `high`: at least two independent non-AI domains and at least one fetched source,
  with no detected conflict.

Perplexity results are marked `ai_synthesis`. They can help discovery, but they do
not count as independent proof.

## Extension Points

To add a provider:

1. Create a new adapter in `src/aisearch/providers/`.
2. Implement `search()`, `fetch()`, or both.
3. Register it in `providers/__init__.py`.
4. Add the key name in `config.py`.
5. Add routing rules in `router.py`.
6. Add tests for parsing, payload shape, and skip behavior.

To add a new intent:

1. Add it to `QueryType`.
2. Add detection and query expansion in `planner.py`.
3. Add routing in `router.py`.
4. Add weights in `scoring.py`.
5. Add planner and CLI tests.

## Output Stability

The main public interface is `ResearchOutput`.

Existing fields should not be removed without a schema version bump and migration
note. New data should be added as optional or defaulted fields when possible.
