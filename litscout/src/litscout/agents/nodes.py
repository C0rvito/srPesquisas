"""
Agent nodes for the LangGraph research pipeline.

Each function is a node: (state) -> partial state update dict.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_ollama import ChatOllama

from litscout.agents.state import ResearchState
from litscout.config import settings
from litscout.database.engine import db_session
from litscout.database.repository import ArticleRepository, SessionRepository
from litscout.search.orchestrator import SearchOrchestrator
from litscout.utils.data_processing import rank_by_citations
from litscout.utils.schemas import ArticleData

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: build LLM instances
# ---------------------------------------------------------------------------

def _llm(model: str, temperature: float = 0.0) -> ChatOllama:
    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=model,
        temperature=temperature,
    )


# ---------------------------------------------------------------------------
# Node 1: Search
# ---------------------------------------------------------------------------

def search_node(state: ResearchState) -> dict[str, Any]:
    """Run multi-source search and populate state.search_result."""
    logger.info("[search_node] query=%r", state.query)
    orchestrator = SearchOrchestrator()
    result = orchestrator.run(state.query)
    return {
        "search_result": result,
        "step": "searched",
        "messages": [
            AIMessage(content=f"Search complete: {len(result.articles)} articles found.")
        ],
    }


# ---------------------------------------------------------------------------
# Node 2: Ranking (LLM-assisted, falls back to pure citation ranking)
# ---------------------------------------------------------------------------

_RANKING_PROMPT = """\
You are a scientific literature expert.
Below are the top {n} academic articles retrieved for the query: "{query}".
They are already sorted by citation count. Your task:

1. Confirm or adjust the ranking considering RELEVANCE to the query AND citation count.
2. Return ONLY a JSON array of integers representing the re-ranked indices (0-based).
   Example for 5 articles: [2, 0, 4, 1, 3]

Articles:
{articles_json}

Return ONLY the JSON array, nothing else.
"""


def ranking_node(state: ResearchState) -> dict[str, Any]:
    """Rank top-N articles using LLM; falls back to citation-only ranking."""
    if not state.search_result:
        return {"step": "ranking_skipped", "errors": ["No search result available"]}

    candidates = state.search_result.top_n or rank_by_citations(
        state.search_result.articles, top_n=settings.top_n_ranked
    )

    articles_summary = [
        {
            "index": i,
            "title": a.title,
            "year": a.year,
            "citations": a.citation_count,
            "venue": a.venue
        }
        for i, a in enumerate(candidates)
    ]

    try:
        llm = _llm(settings.ollama_ranking_model)
        prompt = _RANKING_PROMPT.format(
            n=len(candidates),
            query=state.query,
            articles_json=json.dumps(articles_summary, indent=2),
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        indices = json.loads(raw)
        ranked = [candidates[i] for i in indices if 0 <= i < len(candidates)]
        # Ensure all originals are present (safety)
        seen = {id(a) for a in ranked}
        for a in candidates:
            if id(a) not in seen:
                ranked.append(a)
        logger.info("[ranking_node] LLM re-ranking applied")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[ranking_node] LLM ranking failed (%s); using citation order", exc)
        ranked = candidates

    return {
        "ranked_articles": ranked,
        "step": "ranked",
        "messages": [AIMessage(content=f"Ranking complete: top {len(ranked)} articles selected.")],
    }


# ---------------------------------------------------------------------------
# Node 3: Summarisation / enrichment
# ---------------------------------------------------------------------------

_SUMMARY_PROMPT = """\
You are a research assistant. Summarise the following academic article in 2-3 sentences,
focusing on methodology and key findings relevant to: "{query}".
Also rate its relevance (0-100) to the query.

Title: {title}
Authors: {authors}
Year: {year}
Abstract: {abstract}

Respond ONLY with valid JSON:
{{"summary": "...", "relevance_score": <int 0-100>}}
"""


def summarise_node(state: ResearchState) -> dict[str, Any]:
    """Generate AI summaries for ranked articles."""
    articles = state.ranked_articles
    if not articles:
        return {"step": "summarise_skipped"}

    llm = _llm(settings.ollama_summary_model, temperature=0.2)
    enriched: list[ArticleData] = []

    for art in articles:
        try:
            prompt = _SUMMARY_PROMPT.format(
                query=state.query,
                title=art.title,
                authors=", ".join(art.authors[:5]),
                year=art.year or "unknown",
                abstract=art.abstract or "Not available.",
            )
            resp = llm.invoke([HumanMessage(content=prompt)])
            data = json.loads(resp.content.strip())
            enriched.append(
                art.model_copy(
                    update={
                        "ai_summary": data.get("summary"),
                        "relevance_score": int(data.get("relevance_score", 0)),
                    }
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[summarise_node] Failed for %r: %s", art.title[:40], exc)
            enriched.append(art)

    return {
        "enriched_articles": enriched,
        "step": "summarised",
        "messages": [AIMessage(content=f"Summaries generated for {len(enriched)} articles.")],
    }


# ---------------------------------------------------------------------------
# Node 4: Persist to database
# ---------------------------------------------------------------------------

def persist_node(state: ResearchState) -> dict[str, Any]:
    """Save the research session and all enriched articles to the database."""
    articles_to_save = state.enriched_articles or state.ranked_articles
    if not articles_to_save:
        return {"step": "persist_skipped", "errors": ["Nothing to persist"]}

    with db_session() as session:
        sess_repo = SessionRepository(session)
        art_repo = ArticleRepository(session)

        research_session = sess_repo.create(query=state.query)

        for rank, art in enumerate(articles_to_save, start=1):
            db_article = art_repo.upsert(art)
            sess_repo.add_article(research_session, db_article, rank=rank)
            if art.ai_summary:
                art_repo.update_ai_fields(
                    db_article.id,
                    summary=art.ai_summary,
                    score=art.relevance_score or 0,
                )

        db_id = research_session.id

    logger.info("[persist_node] Saved %d articles to session %d", len(articles_to_save), db_id)
    return {
        "db_session_id": db_id,
        "step": "persisted",
        "messages": [
            AIMessage(content=f"Saved {len(articles_to_save)} articles to DB (session #{db_id}).")
        ],
    }
