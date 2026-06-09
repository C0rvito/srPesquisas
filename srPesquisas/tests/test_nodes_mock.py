import pytest
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

from sr_pesquisas.agents.nodes import (
    query_planner_node,
    search_node,
    ranking_node,
    summarise_node,
)
from sr_pesquisas.utils.schemas import ArticleData, SearchResult


@pytest.fixture
def mock_search_result():
    """Fixture to provide a synthetic search result state."""
    articles = [
        ArticleData(title="Paper A: Cytotoxicity", abstract="Tests...", citation_count=100),
        ArticleData(title="Paper B: Irrelevant", abstract="Nothing...", citation_count=5),
        ArticleData(title="Paper C: High toxicity", abstract="More tests...", citation_count=50)
    ]
    return SearchResult(query="Test compound", articles=articles, top_n=articles)

@pytest.fixture
def mock_research_state(mock_search_result):
    """Fixture providing a base research state."""
    return {
        "query": "Test compound",
        "planned_queries": ["query 1"],
        "search_result": mock_search_result,
        "ranked_articles": None,
        "enriched_articles": None,
        "errors": [],
        "messages": []
    }

def test_query_planner_mocked(mocker, mock_research_state):
    """Isolates the LLM call in the query planner."""
    # Mock ChatOllama inside the _llm helper
    mock_chat_ollama = MagicMock()
    # Simulate the LLM returning a valid JSON array string
    mock_chat_ollama.invoke.return_value = AIMessage(content='["test 1", "test 2", "test 3"]')
    mocker.patch('sr_pesquisas.agents.nodes.ChatOllama', return_value=mock_chat_ollama)

    result_state = query_planner_node(mock_research_state)

    assert "planned_queries" in result_state
    assert len(result_state["planned_queries"]) == 3
    assert result_state["planned_queries"] == ["test 1", "test 2", "test 3"]
    assert result_state["step"] == "planned"
    mock_chat_ollama.invoke.assert_called_once()


def test_search_node_mocked(mocker, mock_research_state):
    """Isolates the external API calls by mocking SearchOrchestrator."""
    mock_orchestrator_instance = MagicMock()
    # Setup what the orchestrator should return
    mock_orchestrator_instance.run.return_value = mock_research_state["search_result"]
    mocker.patch('sr_pesquisas.agents.nodes.SearchOrchestrator', return_value=mock_orchestrator_instance)

    result_state = search_node(mock_research_state)

    assert "search_result" in result_state
    assert len(result_state["search_result"].articles) == 3
    assert result_state["step"] == "searched"
    mock_orchestrator_instance.run.assert_called_once_with("Test compound", ["query 1"])


def test_ranking_node_mocked(mocker, mock_research_state):
    """Isolates the deep ranking LLM to prevent burning VRAM."""
    mock_chat_ollama = MagicMock()
    # The LLM ranks Paper C (index 2), Paper A (index 0), Paper B (index 1)
    mock_chat_ollama.invoke.return_value = AIMessage(content='[2, 0, 1]')
    mocker.patch('sr_pesquisas.agents.nodes.ChatOllama', return_value=mock_chat_ollama)

    result_state = ranking_node(mock_research_state)

    assert "ranked_articles" in result_state
    assert len(result_state["ranked_articles"]) == 3
    # Check if they were reordered according to the mock LLM output
    assert result_state["ranked_articles"][0].title == "Paper C: High toxicity"
    assert result_state["ranked_articles"][1].title == "Paper A: Cytotoxicity"
    assert result_state["ranked_articles"][2].title == "Paper B: Irrelevant"
    assert result_state["step"] == "ranked"
    mock_chat_ollama.invoke.assert_called_once()
