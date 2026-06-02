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
from litscout.ui.tracer import trace_step
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

@trace_step("Multi-source Literature Search")
def search_node(state: ResearchState) -> dict[str, Any]:
    """Run multi-source search and populate state.search_result."""
    query = state.get("query")
    logger.info("[search_node] query=%r", query)
    orchestrator = SearchOrchestrator()
    result = orchestrator.run(query)
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
You are a scientific literature expert specialized in toxicology and parasitology.
Below are the top {n} academic articles retrieved for the compound: "{query}".

Your task is to re-rank these articles based on a STRICT HIERARCHY:

1. MANDATORY/TOP PRIORITY: The article MUST perform or discuss CYTOTOXICITY ASSAYS (ensaio de cito-toxicidade) using the compound. If an article only mentions the compound but doesn't do cytotoxicity, it should be ranked lower regardless of other factors.
2. SECONDARY BONUS: Among articles that DO cytotoxicity, those that also involve LEISHMANIA research (any species) are the most valuable and must be at the very top.
3. QUALITY: Use citation count and venue as a tie-breaker for articles with similar relevance.

Return ONLY a JSON array of integers representing the re-ranked indices (0-based).
Example: [2, 0, 4, 1, 3]

Articles:
{articles_json}

Return ONLY the JSON array, nothing else.
"""


@trace_step("AI-Powered Ranking (Cytotoxicity First)")
def ranking_node(state: ResearchState) -> dict[str, Any]:
    """Rank top-N articles with strict focus on cytotoxicity as primary filter."""
    search_result = state.get("search_result")
    if not search_result:
        return {"step": "ranking_skipped", "errors": ["No search result available"]}

    candidates = search_result.top_n or rank_by_citations(
        search_result.articles, top_n=settings.top_n_ranked
    )

    articles_summary = [
        {
            "index": i,
            "title": a.title,
            "year": a.year,
            "citations": a.citation_count,
            "venue": a.venue,
            "abstract": (a.abstract[:600] + "...") if a.abstract else "No abstract available"
        }
        for i, a in enumerate(candidates)
    ]

    try:
        llm = _llm(settings.ollama_ranking_model)
        prompt = _RANKING_PROMPT.format(
            n=len(candidates),
            query=state.get("query"),
            articles_json=json.dumps(articles_summary, indent=2),
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.strip("`").replace("json", "").strip()
        indices = json.loads(raw)
        ranked = [candidates[i] for i in indices if 0 <= i < len(candidates)]
        # Ensure all originals are present (safety)
        seen = {id(a) for a in ranked}
        for a in candidates:
            if id(a) not in seen:
                ranked.append(a)
        logger.info("[ranking_node] LLM re-ranking applied (Strict Cytotoxicity focus)")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[ranking_node] LLM ranking failed (%s); using citation order", exc)
        ranked = candidates

    return {
        "ranked_articles": ranked,
        "step": "ranked",
        "messages": [
            AIMessage(content="Ranking complete: enforced strict cytotoxicity-first policy.")
        ],
    }


# ---------------------------------------------------------------------------
# Node 3: Summarisation / enrichment
# ---------------------------------------------------------------------------

_SUMMARY_PROMPT = """\
You are a research assistant. Summarise the following academic article in 2-3 sentences.
Focus specifically on:
1. The CYTOTOXICITY results found for "{query}".
2. If applicable, the effects or findings related to LEISHMANIA.

Title: {title}
Authors: {authors}
Year: {year}
Abstract: {abstract}

Respond ONLY with valid JSON:
{{"summary": "...", "relevance_score": <int 0-100>}}

Note: relevance_score should be higher (80-100) if it includes BOTH cytotoxicity and Leishmania.
"""


@trace_step("AI-Generated Summaries")
def summarise_node(state: ResearchState) -> dict[str, Any]:
    """Generate AI summaries for ranked articles."""
    articles = state.get("ranked_articles")
    if not articles:
        return {"step": "summarise_skipped"}

    llm = _llm(settings.ollama_summary_model, temperature=0.2)
    enriched: list[ArticleData] = []

    for art in articles:
        try:
            prompt = _SUMMARY_PROMPT.format(
                query=state.get("query"),
                title=art.title,
                authors=", ".join(art.authors[:5]),
                year=art.year or "unknown",
                abstract=art.abstract or "Not available.",
            )
            resp = llm.invoke([HumanMessage(content=prompt)])
            raw = resp.content.strip()
            if raw.startswith("```"):
                raw = raw.strip("`").replace("json", "").strip()
            data = json.loads(raw)
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

@trace_step("Database Persistence")
def persist_node(state: ResearchState) -> dict[str, Any]:
    """Save the research session and all enriched articles to the database."""
    articles_to_save = state.get("enriched_articles") or state.get("ranked_articles")
    if not articles_to_save:
        return {"step": "persist_skipped", "errors": ["Nothing to persist"]}

    with db_session() as session:
        sess_repo = SessionRepository(session)
        art_repo = ArticleRepository(session)

        query = state.get("query")
        research_session = sess_repo.create(query=query)

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
