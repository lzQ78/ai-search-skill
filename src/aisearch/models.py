from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


Confidence = Literal["high", "medium", "low"]
SourceType = Literal["primary", "secondary", "ai_synthesis", "unknown"]
RunStatus = Literal["ok", "skipped", "error"]
Freshness = Literal["pd", "pw", "pm", "py"]


class Profile(str, Enum):
    quick = "quick"
    balanced = "balanced"
    deep = "deep"


class QueryType(str, Enum):
    factual = "factual"
    status = "status"
    comparison = "comparison"
    tutorial = "tutorial"
    exploratory = "exploratory"
    resource = "resource"
    general = "general"
    news = "news"
    technical = "technical"
    academic = "academic"
    url = "url"


class ProviderStatus(BaseModel):
    name: str
    env_var: str | None = None
    available: bool
    capabilities: list[str] = Field(default_factory=list)
    reason: str | None = None


class QueryPlan(BaseModel):
    query: str
    query_type: QueryType
    intent: QueryType
    profile: Profile
    time_sensitive: bool
    freshness: Freshness | None = None
    angles: list[str]
    max_search_providers: int
    fetch_limit: int


class ProviderResult(BaseModel):
    title: str
    url: str
    snippet: str = ""
    provider: str
    score: float = 0.0
    published_at: str | None = None
    source_type: SourceType = "unknown"
    raw: dict = Field(default_factory=dict)


class FetchResult(BaseModel):
    url: str
    provider: str
    success: bool
    title: str | None = None
    content: str = ""
    error: str | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)


class Source(BaseModel):
    id: str
    title: str
    url: str
    provider: str
    source_type: SourceType
    published_at: str | None = None
    fetched: bool = False
    score: float = 0.0
    snippet: str = ""
    content_preview: str = ""


class Claim(BaseModel):
    text: str
    confidence: Confidence
    source_ids: list[str] = Field(default_factory=list)
    conflict_ids: list[str] = Field(default_factory=list)


class Conflict(BaseModel):
    id: str
    description: str
    source_ids: list[str] = Field(default_factory=list)


class ThreadReference(BaseModel):
    source_url: str
    ref_type: str
    url: str
    context: str = ""


class ContentArtifact(BaseModel):
    source_url: str
    provider: str
    kind: str
    url: str | None = None
    path: str | None = None


class ProviderRun(BaseModel):
    provider: str
    action: Literal["search", "fetch", "synthesis"]
    status: RunStatus
    results_count: int = 0
    duration_ms: int = 0
    error: str | None = None


class ResearchOutput(BaseModel):
    schema_version: str = "1.1"
    query: str
    profile: Profile
    intent: QueryType | None = None
    plan: QueryPlan | None = None
    confidence: Confidence
    claims: list[Claim] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    thread_refs: list[ThreadReference] = Field(default_factory=list)
    content_artifacts: list[ContentArtifact] = Field(default_factory=list)
    provider_runs: list[ProviderRun] = Field(default_factory=list)


class SearchOutput(BaseModel):
    schema_version: str = "1.0"
    query: str
    results: list[ProviderResult] = Field(default_factory=list)
    provider_runs: list[ProviderRun] = Field(default_factory=list)


class FetchOutput(BaseModel):
    schema_version: str = "1.0"
    url: str
    result: FetchResult | None = None
    provider_runs: list[ProviderRun] = Field(default_factory=list)
