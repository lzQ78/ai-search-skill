# Install As A Skill

The repository root is the official skill directory.

Install or symlink the whole `ai-search-skill/` directory into your agent's skill
directory. Do not copy only `SKILL.md`; the skill needs the local CLI, source code,
and `.env` configuration next to it.

## Prepare The Repository

Run once inside the repository:

```bash
python -m pip install -e .
cp .env.example .env
python -m aisearch doctor
```

PowerShell:

```powershell
python -m pip install -e .
Copy-Item .env.example .env
python -m aisearch doctor
```

Fill any provider keys you want to use in `.env`. Missing keys are allowed.

When the skill is used, the agent should start its final answer with a Chinese
`AI Search Skill 使用情况` diagnostics block based on `provider_runs`. If keys are
missing, expired, or providers fail, that block should make the issue visible.

## Cursor

Project-local install:

```bash
mkdir -p .cursor/skills
ln -s /absolute/path/to/ai-search-skill .cursor/skills/ai-search
```

PowerShell:

```powershell
New-Item -ItemType Directory -Force .cursor\skills
New-Item -ItemType SymbolicLink -Path .cursor\skills\ai-search -Target C:\absolute\path\to\ai-search-skill
```

Copy fallback:

```text
.cursor/skills/ai-search/
└── SKILL.md
```

The copied directory should include the whole repository, not only `SKILL.md`.

## Claude Code

Project-local install:

```bash
mkdir -p .claude/skills
ln -s /absolute/path/to/ai-search-skill .claude/skills/ai-search
```

Copy fallback:

```text
.claude/skills/ai-search/
└── SKILL.md
```

The copied directory should include the whole repository.

## Codex

Project-local install:

```bash
mkdir -p .codex/skills
ln -s /absolute/path/to/ai-search-skill .codex/skills/ai-search
```

Copy fallback:

```text
.codex/skills/ai-search/
└── SKILL.md
```

The copied directory should include the whole repository.
