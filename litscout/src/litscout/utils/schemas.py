from __future__ import annotations

from pydantic import BaseModel, Field


class ArticleData(BaseModel):
    """Data transfer object for academic articles."""

    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    abstract: str | None = None
    doi: str | None = None
    scholar_id: str | None = None
    openalex_id: str | None = None
    citation_count: int = 0
    ai_summary: str | None = None
    relevance_score: int | None = None
    source: str = "unknown"


class SearchResult(BaseModel):
    """Container for search results from multiple sources."""

    query: str
    articles: list[ArticleData] = Field(default_factory=list)
    top_n: list[ArticleData] = Field(default_factory=list)
