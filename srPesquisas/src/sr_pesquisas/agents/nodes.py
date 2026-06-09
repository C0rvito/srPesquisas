from __future__ import annotations

import json
import logging
import os
import requests
import pymupdf
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_ollama import ChatOllama

from sr_pesquisas.agents.state import ResearchState
from sr_pesquisas.config import settings
from sr_pesquisas.database.engine import db_session
from sr_pesquisas.database.repository import ArticleRepository, SessionRepository
from sr_pesquisas.search.orchestrator import SearchOrchestrator
from sr_pesquisas.ui.tracer import trace_step
from sr_pesquisas.utils.data_processing import rank_by_citations
from sr_pesquisas.utils.schemas import ArticleData

logger = logging.getLogger(__name__)

def _llm(model: str, temperature: float = 0.0, num_ctx: int | None = None) -> ChatOllama:
    kwargs = {
        "base_url": settings.ollama_base_url,
        "model": model,
        "temperature": temperature,
    }
    if num_ctx:
        kwargs["num_ctx"] = num_ctx
    return ChatOllama(**kwargs)

@trace_step("Query Planning")
def query_planner_node(state: ResearchState) -> dict[str, Any]:
    query = state.get("query", "")
    llm = _llm(settings.ollama_summary_model, temperature=0.2)
    prompt = f"""You are a search query expert. The user wants to research: "{query}".
Generate exactly 3 diverse academic search queries in English to maximize recall on platforms like Google Scholar.
Return ONLY a JSON array of 3 strings. Example: ["query 1", "query 2", "query 3"]."""
    
    try:
        resp = llm.invoke([HumanMessage(content=prompt)])
        raw = resp.content.strip("` \n").replace("json\n", "")
        queries = json.loads(raw)
        if not isinstance(queries, list):
            queries = [query]
    except Exception:
        queries = [query]
        
    return {"planned_queries": queries, "step": "planned"}

@trace_step("Multi-source Literature Search")
def search_node(state: ResearchState) -> dict[str, Any]:
    original_query = state.get("query", "")
    queries = state.get("planned_queries", [original_query])
    orchestrator = SearchOrchestrator()
    result = orchestrator.run(original_query, queries)
    return {"search_result": result, "step": "searched"}

@trace_step("Fetch Full Texts (PDF)")
def fetch_full_texts_node(state: ResearchState) -> dict[str, Any]:
    search_result = state.get("search_result")
    if not search_result or not search_result.top_n:
        return {"step": "fetch_skipped"}
        
    scratch_dir = Path("./data/scratch")
    scratch_dir.mkdir(parents=True, exist_ok=True)
    
    updated_top_n = []
    # Mocked downloading for now, in a real scenario we'd use Unpaywall or the OA link from OpenAlex.
    # We will simulate PDF extraction if a local PDF was magically there, or just skip gracefully.
    for art in search_result.top_n:
        # In a real heavy implementation, we would download the PDF here.
        # For now, we just pass the article forward. If we had a PDF, we'd use pymupdf:
        # doc = pymupdf.open(pdf_path)
        # text = chr(12).join([page.get_text() for page in doc])
        art.full_text = art.abstract # Fallback to abstract if PDF fails
        updated_top_n.append(art)
        
    search_result.top_n = updated_top_n
    return {"search_result": search_result, "step": "fetched_texts"}

@trace_step("Vision Extraction (Graphs & Charts)")
def vision_extraction_node(state: ResearchState) -> dict[str, Any]:
    search_result = state.get("search_result")
    if not search_result or not hasattr(settings, 'ollama_vision_model'):
        return {"step": "vision_skipped"}
        
    # In a full implementation, we would send extracted images from pymupdf to the vision model here.
    # llm_vision = _llm(settings.ollama_vision_model)
    return {"step": "vision_completed"}

@trace_step("Deep AI Ranking")
def ranking_node(state: ResearchState) -> dict[str, Any]:
    search_result = state.get("search_result")
    if not search_result:
        return {"step": "ranking_skipped"}

    candidates = search_result.top_n
    
    articles_summary = [
        {
            "index": i,
            "title": a.title,
            "text_snippet": (a.full_text[:1000] + "...") if a.full_text else "No text"
        }
        for i, a in enumerate(candidates)
    ]
    
    prompt = f"""You are a scientific expert. Rank these articles based strictly on relevance to the user query: "{state.get('query')}".
Return ONLY a JSON array of integers representing the re-ranked indices (0-based). Example: [2, 0, 1]
Articles: {json.dumps(articles_summary, indent=2)}"""

    try:
        # Using massive num_ctx for deep ranking
        llm = _llm(settings.ollama_ranking_model, num_ctx=getattr(settings, 'ollama_num_ctx', 32000))
        resp = llm.invoke([HumanMessage(content=prompt)])
        raw = resp.content.strip("` \n").replace("json\n", "")
        indices = json.loads(raw)
        ranked = [candidates[i] for i in indices if 0 <= i < len(candidates)]
        for a in candidates:
            if a not in ranked:
                ranked.append(a)
    except Exception:
        ranked = candidates

    return {"ranked_articles": ranked, "step": "ranked"}

@trace_step("Deep Summarisation")
def summarise_node(state: ResearchState) -> dict[str, Any]:
    articles = state.get("ranked_articles")
    if not articles:
        return {"step": "summarise_skipped"}

    llm = _llm(settings.ollama_summary_model, temperature=0.2, num_ctx=getattr(settings, 'ollama_num_ctx', 32000))
    enriched = []

    for art in articles:
        prompt = f"""Summarise the following article in relation to: "{state.get('query')}".
Title: {art.title}
Text: {art.full_text[:3000] if art.full_text else art.abstract}

Respond ONLY with valid JSON: {{"summary": "...", "relevance_score": <int 0-100>}}"""
        try:
            resp = llm.invoke([HumanMessage(content=prompt)])
            raw = resp.content.strip("` \n").replace("json\n", "")
            data = json.loads(raw)
            art.ai_summary = data.get("summary")
            art.relevance_score = int(data.get("relevance_score", 0))
        except Exception:
            pass
        enriched.append(art)

    return {"enriched_articles": enriched, "step": "summarised"}

@trace_step("Database Persistence")
def persist_node(state: ResearchState) -> dict[str, Any]:
    articles_to_save = state.get("enriched_articles") or state.get("ranked_articles")
    if not articles_to_save:
        return {"step": "persist_skipped"}

    with db_session() as session:
        sess_repo = SessionRepository(session)
        art_repo = ArticleRepository(session)
        research_session = sess_repo.create(query=state.get("query"))

        for rank, art in enumerate(articles_to_save, start=1):
            db_article = art_repo.upsert(art)
            sess_repo.add_article(research_session, db_article, rank=rank)
            if art.ai_summary:
                art_repo.update_ai_fields(db_article.id, summary=art.ai_summary, score=art.relevance_score or 0)

        db_id = research_session.id

    return {"db_session_id": db_id, "step": "persisted"}
