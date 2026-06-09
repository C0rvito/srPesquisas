from __future__ import annotations

import pytest
from sqlalchemy import select
from sr_pesquisas.database.engine import SessionLocal, init_db
from sr_pesquisas.database.models import Article, ResearchSession
from sr_pesquisas.database.repository import ArticleRepository, SessionRepository
from sr_pesquisas.utils.schemas import ArticleData


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Initialize the database for testing. Use in-memory SQLite if preferred, 
    but here we follow the project's config (which might be a local test.db)."""
    # For testing, we could override settings.database_url to sqlite:///:memory:
    init_db()


@pytest.fixture
def db():
    """Provide a database session for each test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_article_repository_upsert(db):
    """Test inserting and updating articles in the repository."""
    repo = ArticleRepository(db)
    
    data = ArticleData(
        title="Test Article",
        authors=["Author 1"],
        citation_count=5,
        doi="10.1234/test",
        source="test"
    )
    
    # 1. Insert
    article = repo.upsert(data)
    assert article.id is not None
    assert article.title == "Test Article"
    
    # 2. Update (increase citations)
    data.citation_count = 10
    updated = repo.upsert(data)
    assert updated.id == article.id
    assert updated.citation_count == 10


def test_session_repository(db):
    """Test creating a session and adding articles to it."""
    art_repo = ArticleRepository(db)
    sess_repo = SessionRepository(db)
    
    # Create article
    art_data = ArticleData(title="Session Article", doi="10.5555/sess", source="test")
    article = art_repo.upsert(art_data)
    
    # Create session
    session = sess_repo.create(query="AI in medicine")
    assert session.id is not None
    
    # Link article to session
    sess_repo.add_article(session, article, rank=1)
    
    # Verify link
    db.refresh(session)
    assert len(session.articles) == 1
    assert session.articles[0].title == "Session Article"
