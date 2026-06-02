"""
LangGraph research pipeline.

Graph:  init → search → ranking → summarise → persist → END
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from litscout.agents.nodes import (
    persist_node,
    ranking_node,
    search_node,
    summarise_node,
)
from litscout.agents.state import ResearchState


def build_graph() -> StateGraph:
    """Construct and compile the research pipeline graph."""
    builder = StateGraph(ResearchState)

    # Add nodes
    builder.add_node("search", search_node)
    builder.add_node("ranking", ranking_node)
    builder.add_node("summarise", summarise_node)
    builder.add_node("persist", persist_node)

    # Edges
    builder.add_edge(START, "search")
    builder.add_edge("search", "ranking")
    builder.add_edge("ranking", "summarise")
    builder.add_edge("summarise", "persist")
    builder.add_edge("persist", END)

    return builder.compile()


# Module-level compiled graph (imported by CLI / API)
research_graph = build_graph()


def run_pipeline(query: str) -> dict:
    """Convenience wrapper: run the full pipeline for a query string."""
    initial_state = {"query": query}
    final_state = research_graph.invoke(initial_state)
    return final_state
