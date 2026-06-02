from __future__ import annotations

import pytest
from litscout.utils.data_processing import rank_by_citations
from litscout.utils.schemas import ArticleData


@pytest.fixture
def mock_articles() -> list[ArticleData]:
    """Fixture providing a list of articles for testing."""
    return [
        ArticleData(
            title="Article A",
            citation_count=10,
            doi="10.1001/a",
            source="source1"
        ),
        ArticleData(
            title="Article A",  # Duplicate by title (normalized)
            citation_count=5,
            doi=None,
            source="source2"
        ),
        ArticleData(
            title="Article B",
            citation_count=20,
            doi="10.1001/b",
            source="source1"
        ),
        ArticleData(
            title="Article C",
            citation_count=15,
            doi="10.1001/b",  # Duplicate by DOI
            source="source2"
        ),
        ArticleData(
            title="Unique Article",
            citation_count=2,
            doi="10.1001/u",
            source="source1"
        ),
    ]


def test_rank_by_citations_deduplication(mock_articles: list[ArticleData]):
    """Test that articles are correctly deduplicated by DOI and Title."""
    # We expect:
    # 1. Article B (20 citations)
    # 2. Article A (10 citations)
    # 3. Unique Article (2 citations)
    # Article C is dropped because it shares DOI with B.
    # The second Article A is dropped because it shares title with the first A.
    
    ranked = rank_by_citations(mock_articles, top_n=10)
    
    assert len(ranked) == 3
    assert ranked[0].title == "Article B"
    assert ranked[1].title == "Article A"
    assert ranked[2].title == "Unique Article"


def test_rank_by_citations_limit(mock_articles: list[ArticleData]):
    """Test that the top_n limit is respected."""
    ranked = rank_by_citations(mock_articles, top_n=2)
    assert len(ranked) == 2
    assert ranked[0].citation_count == 20
    assert ranked[1].citation_count == 10


def test_rank_by_citations_empty_list():
    """Test with an empty article list."""
    assert rank_by_citations([], top_n=10) == []
