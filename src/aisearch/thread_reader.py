from __future__ import annotations

import os
import re
from urllib.parse import urlparse

import httpx

from .models import Source, ThreadReference


GITHUB_REF_RE = re.compile(
    r"https?://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/(issues|pull)/(\d+)"
)
ISSUE_REF_RE = re.compile(
    r"(?:^|[\s(])(?:([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+))?#(\d+)(?=[\s).,;:!?]|$)"
)
COMMIT_RE = re.compile(
    r"https?://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/commit/([0-9a-f]{7,40})",
    re.IGNORECASE,
)
URL_RE = re.compile(r"(?<!\S)(https?://[^\s<>\[\]()]+)")


class ThreadReader:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client
        self._external_client = client is not None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=6.0))
        return self._client

    async def close(self) -> None:
        if self._client is not None and not self._external_client:
            await self._client.aclose()

    async def collect_refs(
        self,
        sources: list[Source],
        *,
        max_fetches: int = 3,
        depth: int = 1,
    ) -> list[ThreadReference]:
        if depth <= 0 or max_fetches <= 0:
            return []

        queue = [source.url for source in sources if _is_thread_candidate(source.url)]
        seen = set()
        collected: list[ThreadReference] = []

        for _ in range(depth):
            next_queue: list[str] = []
            for url in queue:
                if len(seen) >= max_fetches:
                    return _dedupe_refs(collected)
                if url in seen:
                    continue
                seen.add(url)
                refs = await self.fetch_refs(url)
                collected.extend(refs)
                next_queue.extend(ref.url for ref in refs if _is_thread_candidate(ref.url))
            queue = next_queue
            if not queue:
                break

        return _dedupe_refs(collected)

    async def fetch_refs(self, url: str) -> list[ThreadReference]:
        parsed = _parse_github_url(url)
        if parsed:
            return await self._fetch_github_refs(url, parsed)
        return await self._fetch_web_refs(url)

    async def _fetch_github_refs(self, source_url: str, parsed: dict[str, str]) -> list[ThreadReference]:
        owner = parsed["owner"]
        repo = parsed["repo"]
        number = parsed["number"]
        repo_context = f"{owner}/{repo}"
        base = f"https://api.github.com/repos/{owner}/{repo}"
        headers = {"Accept": "application/vnd.github+json"}
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        texts: list[str] = []
        issue = await self._get_json(f"{base}/issues/{number}", headers=headers)
        if isinstance(issue, dict):
            texts.extend([issue.get("body") or "", issue.get("title") or ""])

        comments = await self._get_json(
            f"{base}/issues/{number}/comments",
            headers=headers,
            params={"per_page": "100"},
        )
        if isinstance(comments, list):
            texts.extend(comment.get("body") or "" for comment in comments if isinstance(comment, dict))

        timeline = await self._get_json(
            f"{base}/issues/{number}/timeline",
            headers=headers,
            params={"per_page": "100"},
        )
        if isinstance(timeline, list):
            for event in timeline:
                if not isinstance(event, dict):
                    continue
                source = event.get("source") or {}
                issue_ref = source.get("issue") if isinstance(source, dict) else None
                if isinstance(issue_ref, dict) and issue_ref.get("html_url"):
                    texts.append(issue_ref["html_url"])
                commit = event.get("commit_url") or event.get("html_url")
                if commit:
                    texts.append(commit)

        return extract_refs("\n".join(texts), source_url=source_url, repo_context=repo_context)

    async def _fetch_web_refs(self, source_url: str) -> list[ThreadReference]:
        try:
            response = await self.client.get(source_url)
            response.raise_for_status()
        except Exception:
            return []
        return extract_refs(response.text[:100_000], source_url=source_url)

    async def _get_json(
        self,
        url: str,
        headers: dict[str, str],
        params: dict[str, str] | None = None,
    ):
        try:
            response = await self.client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


def extract_refs(
    text: str,
    *,
    source_url: str,
    repo_context: str = "",
) -> list[ThreadReference]:
    refs: list[ThreadReference] = []

    def add(ref_type: str, url: str, context: str = "") -> None:
        refs.append(
            ThreadReference(
                source_url=source_url,
                ref_type=ref_type,
                url=url.rstrip(".,;:!"),
                context=context,
            )
        )

    for match in GITHUB_REF_RE.finditer(text):
        repo = match.group(1)
        kind = "pr" if match.group(2) == "pull" else "issue"
        number = match.group(3)
        add(kind, f"https://github.com/{repo}/{match.group(2)}/{number}", _context(text, match))

    for match in ISSUE_REF_RE.finditer(text):
        repo = match.group(1) or repo_context
        number = match.group(2)
        if repo:
            add("issue", f"https://github.com/{repo}/issues/{number}", _context(text, match))

    for match in COMMIT_RE.finditer(text):
        repo = match.group(1)
        sha = match.group(2)
        add("commit", f"https://github.com/{repo}/commit/{sha}", _context(text, match))

    for match in URL_RE.finditer(text):
        url = match.group(1)
        if "github.com" not in url and not _looks_like_asset(url):
            add("url", url, _context(text, match))

    return _dedupe_refs(refs)


def _parse_github_url(url: str) -> dict[str, str] | None:
    parsed = urlparse(url)
    if parsed.hostname not in {"github.com", "www.github.com"}:
        return None
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 4 or parts[2] not in {"issues", "pull"}:
        return None
    if not parts[3].isdigit():
        return None
    return {"owner": parts[0], "repo": parts[1], "kind": parts[2], "number": parts[3]}


def _is_thread_candidate(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in {"github.com", "www.github.com"}:
        return _parse_github_url(url) is not None
    return (
        host == "news.ycombinator.com"
        or host.endswith("reddit.com")
        or host == "v2ex.com"
    )


def _dedupe_refs(refs: list[ThreadReference]) -> list[ThreadReference]:
    seen = set()
    deduped = []
    for ref in refs:
        key = (ref.source_url, ref.ref_type, ref.url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    return deduped


def _context(text: str, match: re.Match) -> str:
    start = max(0, match.start() - 50)
    end = min(len(text), match.end() + 50)
    return re.sub(r"\s+", " ", text[start:end]).strip()


def _looks_like_asset(url: str) -> bool:
    return bool(re.search(r"\.(png|jpg|jpeg|gif|svg|ico|webp)(?:\?|$)", url, re.I))
