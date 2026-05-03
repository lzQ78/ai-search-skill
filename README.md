# AI Search Skill

AI Search Skill is a local multi-provider search orchestration CLI for AI agents.

It does not try to be another chatbot answer engine. Its job is to collect evidence:
search several providers, fetch original pages when possible, deduplicate URLs, score
sources, flag simple conflicts, and return a stable JSON bundle that an agent can use
to write a sourced answer.

The project is self-contained. The repository root includes `SKILL.md`, so the repo
itself is the skill directory after setup.

## Why This Exists

AI agents often need current external information, but raw web search is not enough.
Search snippets can be stale, duplicated, vendor-shaped, or model-generated. This
project separates retrieval from synthesis.

The core idea is simple:

1. Plan the query.
2. Search through the best available providers.
3. Fetch original sources where possible.
4. Score evidence by relevance, freshness, authority, and provider signal.
5. Return JSON, not prose.

The agent remains responsible for the final answer. `aisearch` provides the evidence
layer under it.

## What It Does

- Multi-provider search through Tavily, Brave, Exa, Jina, and Perplexity.
- Original page fetching through Firecrawl, Jina, Tavily, Exa, and optional MinerU.
- Query intent detection for factual, status, comparison, tutorial, exploratory,
  news, resource, technical, academic, and URL inputs.
- Profile-based search budgets: `quick`, `balanced`, and `deep`.
- URL canonicalization and deduplication.
- Source scoring with keyword, freshness, authority, domain boost, provider signal,
  and fetch bonus.
- Conflict detection for simple year disagreement across sources.
- GitHub issue/PR thread reference extraction.
- Stable JSON output for downstream agents.

Perplexity is treated as `ai_synthesis`. It can provide leads, but it is not enough
by itself for high-confidence claims.

## Providers

| Provider | Search | Fetch | Notes |
|---|---:|---:|---|
| Tavily | Yes | Yes | General web and freshness-sensitive queries. |
| Brave | Yes | No | Broad web search. |
| Exa | Yes | Yes | Technical, semantic, academic, and resource discovery. |
| Firecrawl | No | Yes | Page scraping fallback. |
| Jina | Yes | Yes | Search requires `JINA_API_KEY`; fetch can run without a key. |
| Perplexity | Yes | No | AI synthesis only; treated as leads. |
| MinerU | No | Yes | Optional fallback for high-friction pages. |

Missing provider keys are allowed. Providers without credentials are skipped unless
they support unauthenticated access.

## Project Structure

```text
ai-search-skill/
├── SKILL.md                # Root skill entry for agent use
├── docs/
│   ├── ARCHITECTURE.md
│   └── INSTALL_SKILL.md
├── src/aisearch/
│   ├── cli.py              # Typer CLI entrypoint
│   ├── config.py           # Environment and provider configuration
│   ├── models.py           # Pydantic output contracts
│   ├── planner.py          # Intent detection, query expansion, budgets
│   ├── router.py           # Provider selection by intent
│   ├── orchestrator.py     # End-to-end research/search/fetch flow
│   ├── reader.py           # Page fetching and fallback order
│   ├── verifier.py         # Deduplication, confidence, conflict checks
│   ├── scoring.py          # Keyword/freshness/authority scoring
│   ├── thread_reader.py    # GitHub/thread reference extraction
│   └── providers/          # Provider adapters
├── examples/
│   └── research-output.example.json
├── tests/
└── pyproject.toml
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the module-level design.

## Installation

Python 3.11 or newer is required.

For normal local use:

```powershell
git clone git@github.com:lzQ78/ai-search-skill.git
cd ai-search-skill
python -m pip install -e .
Copy-Item .env.example .env
```

For development and tests:

```powershell
git clone git@github.com:lzQ78/ai-search-skill.git
cd ai-search-skill
python -m pip install -e .[dev]
Copy-Item .env.example .env
```

On macOS or Linux:

```bash
git clone git@github.com:lzQ78/ai-search-skill.git
cd ai-search-skill
python -m pip install -e .
cp .env.example .env
```

`-e` means editable install. It links the local source tree into the Python
environment, so code changes take effect immediately. `[dev]` only adds development
dependencies such as `pytest`.

If you do not want to install the package itself, you can still run from the repo
root through the shim:

```bash
python aisearch.py doctor
python aisearch.py research --query "latest Python release" --format json
```

You still need the Python dependencies from `pyproject.toml` in your environment.

Fill only the keys you want to use. The template groups variables by purpose and
marks all provider keys as optional:

```env
# Search providers
TAVILY_API_KEY=
BRAVE_API_KEY=
EXA_API_KEY=
JINA_API_KEY=
PERPLEXITY_API_KEY=

# Content fetch and extraction
FIRECRAWL_API_KEY=
MINERU_API_TOKEN=

# Optional GitHub thread enrichment
GITHUB_TOKEN=

# Runtime controls
AISEARCH_REQUEST_TIMEOUT=30
AISEARCH_FETCH_CONCURRENCY=4
AISEARCH_MAX_THREAD_FETCHES=3

# Optional outbound proxy
# Use this when the agent process needs explicit public internet access through
# a local proxy, and the proxy is not enabled globally for child processes.
# HTTP_PROXY=http://127.0.0.1:7890
# HTTPS_PROXY=http://127.0.0.1:7890
# ALL_PROXY=http://127.0.0.1:7890
NO_PROXY=127.0.0.1,localhost
```

Check local provider state:

```bash
python -m aisearch doctor
```

## Using As A Skill

This repository has a root `SKILL.md`. After cloning the repo and installing the
Python dependencies, an agent can use the repository itself as the skill directory.

Minimum working flow:

```bash
git clone git@github.com:lzQ78/ai-search-skill.git
cd ai-search-skill
python -m pip install -e .
cp .env.example .env
python -m aisearch doctor
```

Then expose this repository to your agent's skill system.

Install the whole repository directory, not just `SKILL.md`. The skill calls the
local CLI and needs the source tree and `.env` beside it.

See [docs/INSTALL_SKILL.md](docs/INSTALL_SKILL.md) for Cursor, Claude Code, and
Codex install paths.

## CLI Usage

Run full research:

```bash
python -m aisearch research --query "latest Python release" --format json
```

Run a comparison query with explicit scoring boost:

```bash
python -m aisearch research \
  --query "Bun vs Deno" \
  --intent comparison \
  --domain-boost github.com,deno.com,bun.sh \
  --format json
```

Research a GitHub issue and extract thread references:

```bash
python -m aisearch research \
  --query "https://github.com/owner/repo/issues/123" \
  --thread-depth 1 \
  --format json
```

Search only, without fetch and verification:

```bash
python -m aisearch search \
  --query "AI search agents" \
  --providers tavily,brave,exa \
  --format json
```

Fetch one URL:

```bash
python -m aisearch fetch --url "https://example.com" --format json
```

## Research Options

Profiles control cost and depth:

| Profile | Behavior |
|---|---|
| `quick` | Fewer providers, top 2 fetches. |
| `balanced` | Default, at most 4 search providers, top 5 fetches. |
| `deep` | Broader provider use, top 10 fetches. |

Useful options:

| Option | Meaning |
|---|---|
| `--intent auto|factual|status|comparison|tutorial|exploratory|news|resource|technical|academic` | Override automatic intent detection. |
| `--domain-boost github.com,docs.example.com` | Increase authority score for selected domains. |
| `--thread-depth 0|1|2|3` | Follow thread references. |
| `--max-thread-fetches 3` | Limit thread fetches. |
| `--content-fallback auto|off|mineru` | Control fallback extraction. |

Intent affects query expansion, provider routing, freshness handling, and source
scoring.

## Output Contract

`research` returns JSON with this top-level shape:

```json
{
  "schema_version": "1.1",
  "query": "...",
  "profile": "balanced",
  "intent": "status",
  "plan": {},
  "confidence": "high",
  "claims": [],
  "sources": [],
  "conflicts": [],
  "thread_refs": [],
  "content_artifacts": [],
  "provider_runs": []
}
```

Important fields:

| Field | Meaning |
|---|---|
| `plan` | Detected intent, generated query angles, freshness, and budgets. |
| `sources` | Deduplicated evidence candidates. Prefer fetched sources over snippets. |
| `claims` | Minimal evidence summary for the agent. Not final prose. |
| `conflicts` | Simple detected source conflicts. |
| `thread_refs` | References found in GitHub issues, PRs, or thread-like pages. Treat as leads until fetched. |
| `content_artifacts` | Traceable outputs from fallback extractors such as MinerU. |
| `provider_runs` | Per-provider status, timing, and errors. |

## Answer Diagnostics

When an agent uses this skill, the final answer should start with a Chinese
diagnostics block built from `provider_runs`, for example:

```text
AI Search Skill 使用情况：
- 状态：已使用
- 成功搜索：tavily, exa
- 成功抓取：firecrawl, tavily
- 跳过：brave 缺少 BRAVE_API_KEY；perplexity 缺少 PERPLEXITY_API_KEY
- 报错：jina search ConnectTimeout；firecrawl fetch 403
- 未使用：mineru
```

If no provider returned usable evidence, the agent should say that explicitly before
answering:

```text
AI Search Skill 使用情况：
- 状态：已使用，但未获得可用证据
- 成功搜索：无
- 成功抓取：无
- 跳过：brave 缺少 BRAVE_API_KEY
- 报错：jina search ConnectTimeout
- 未使用：无
```

This is intentional. It makes missing keys, expired keys, provider failures, and
empty searches visible to the user.

## Design Principles

- Evidence first. The CLI returns structured data instead of writing the final answer.
- Provider failures are isolated. One failed provider should not fail the whole run.
- AI synthesis is not proof. Model-generated search output is treated as a lead.
- Source fetch matters. Snippets are useful, but fetched pages carry more weight.
- Contracts stay stable. New fields should be additive when possible.
- The root `SKILL.md` is the only official skill entry.

## Tests

```bash
python -m pytest
```

The test suite covers planner routing, provider payloads, reader fallback,
verification, CLI behavior, scoring, and thread reference extraction.

Live provider tests are not enabled by default. Use them only when adding real API
checks:

```bash
RUN_LIVE_SEARCH_TESTS=1 python -m pytest
```

PowerShell:

```powershell
$env:RUN_LIVE_SEARCH_TESTS = "1"
python -m pytest
```

## Current Limits

- Conflict detection is intentionally simple. It catches obvious year disagreement,
  not full claim-level contradiction.
- MinerU support is optional and depends on a valid `MINERU_API_TOKEN`.
- Thread extraction focuses on GitHub issue/PR references first. HN, Reddit, V2EX,
  and generic pages use lighter URL/reference extraction.
- The output is designed for agents. It is not a human-readable report by default.
