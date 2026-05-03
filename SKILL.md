---
name: ai-search
description: >
  Use this skill when a task needs web search, current information, source
  verification, product or GitHub project research, news checks, or comparison
  across multiple public sources. It calls the local aisearch CLI and returns a
  JSON evidence bundle for the agent to synthesize.
---

# AI Search

Use this skill as the evidence layer for web-backed answers.

It should be used for:

- current or time-sensitive information;
- fact checking across multiple public sources;
- project, product, library, or GitHub research;
- news and release checks;
- comparisons and recommendation research;
- direct URL research or source extraction.

## Required Setup

Run once from this repository:

```bash
python -m pip install -e .
cp .env.example .env
```

On Windows PowerShell:

```powershell
python -m pip install -e .
Copy-Item .env.example .env
```

Fill any provider keys you want to use in `.env`. Missing keys are allowed.

Check provider state:

```bash
python -m aisearch doctor
```

## Default Command

Run from the repository root:

```bash
python -m aisearch research --query "<query>" --format json
```

If the package has not been installed, use the local shim:

```bash
python aisearch.py research --query "<query>" --format json
```

## Useful Controls

```bash
python -m aisearch research --query "<query>" --profile deep --format json
python -m aisearch research --query "<query>" --intent comparison --domain-boost github.com --format json
python -m aisearch research --query "<github issue url>" --thread-depth 1 --format json
python -m aisearch fetch --url "<url>" --content-fallback auto --format json
```

## How To Use The JSON

- At the start of the final answer, include a Chinese diagnostics block built from
  `provider_runs`.
- Use this format:

```text
AI Search Skill 使用情况：
- 状态：已使用
- 成功搜索：<ok search providers, or 无>
- 成功抓取：<ok fetch providers, or 无>
- 跳过：<skipped providers and reasons, or 无>
- 报错：<errored providers and error text, or 无>
- 未使用：<available but unused providers, or 无>
```

- If no provider produced search or fetch results, set `成功搜索：无` and
  `成功抓取：无`, then state `未获得可用证据` before answering.
- If providers were skipped because keys are missing, list them under `跳过`.
- If providers errored, list them under `报错`.
- Treat `sources` as evidence, not final prose.
- Prefer fetched sources over snippets.
- Do not use Perplexity-only evidence for high-confidence claims.
- Treat `thread_refs` as leads unless the referenced pages are fetched.
- Include `content_artifacts` when fallback extraction produced traceable artifacts.
- If `conflicts` is non-empty, explain the conflict before giving a conclusion.
- If `confidence` is `low`, say what evidence is missing.

## Profiles

- `quick`: lower cost, fewer providers, top 2 fetches.
- `balanced`: default, at most 4 search providers, top 5 fetches.
- `deep`: broader provider use, top 10 fetches.
