from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage

from sr_pesquisas.utils.schemas import ArticleData, SearchResult


def merge_messages(left: list[BaseMessage], right: list[BaseMessage]) -> list[BaseMessage]:
    """Merger function for messages in the state graph."""
    return left + right


class ResearchState(TypedDict, total=False):
    """The state of the research pipeline."""

    query: str
    planned_queries: list[str]
    search_result: SearchResult | None
    ranked_articles: list[ArticleData] | None
    enriched_articles: list[ArticleData] | None
    db_session_id: int | None
    step: str
    messages: Annotated[list[BaseMessage], merge_messages]
    errors: list[str]
