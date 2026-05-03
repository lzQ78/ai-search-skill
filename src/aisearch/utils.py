from __future__ import annotations

import re
from hashlib import sha1
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
}


def stable_id(prefix: str, value: str, length: int = 10) -> str:
    return f"{prefix}_{sha1(value.encode('utf-8')).hexdigest()[:length]}"


def canonical_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip()

    query = urlencode(
        sorted((k, v) for k, v in parse_qsl(parsed.query) if k not in TRACKING_PARAMS)
    )
    path = parsed.path.rstrip("/") or "/"
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            query,
            "",
        )
    )


def domain_of(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower()


def truncate(text: str, limit: int = 1200) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def looks_like_url(text: str) -> bool:
    return bool(re.match(r"^https?://", text.strip(), re.IGNORECASE))


def years_in(text: str) -> set[str]:
    return set(re.findall(r"\b(?:19|20)\d{2}\b", text or ""))

