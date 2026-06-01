from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from litscout.database.models import Article, ResearchSession, SessionArticle
from litscout.utils.schemas import ArticleData


class ArticleRepository:
    """CRUD operations for Articles."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_doi(self, doi: str) -> Article | None:
        return self.session.execute(select(Article).where(Article.doi == doi)).scalar_one_or_none()

    def get_by_scholar_id(self, scholar_id: str) -> Article | None:
        return self.session.execute(
            select(Article).where(Article.scholar_id == scholar_id)
        ).scalar_one_or_none()

    def upsert(self, data: ArticleData) -> Article:
        """Insert or update an article based on DOI or Scholar ID."""
        article = None
        if data.doi:
            article = self.get_by_doi(data.doi)
        if not article and data.scholar_id:
            article = self.get_by_scholar_id(data.scholar_id)

        if article:
            # Update existing
            article.citation_count = max(article.citation_count, data.citation_count)
            if data.abstract and not article.abstract:
                article.abstract = data.abstract
            if data.ai_summary:
                article.ai_summary = data.ai_summary
            if data.relevance_score:
                article.relevance_score = data.relevance_score
        else:
            # Create new
            article = Article(
                title=data.title,
                authors=json.dumps(data.authors),
                year=data.year,
                venue=data.venue,
                abstract=data.abstract,
                doi=data.doi,
                scholar_id=data.scholar_id,
                openalex_id=data.openalex_id,
                citation_count=data.citation_count,
                ai_summary=data.ai_summary,
                relevance_score=data.relevance_score,
                source=data.source,
            )
            self.session.add(article)

        self.session.flush()
        return article

    def update_ai_fields(self, article_id: int, summary: str, score: int) -> None:
        article = self.session.get(Article, article_id)
        if article:
            article.ai_summary = summary
            article.relevance_score = score


class SessionRepository:
    """CRUD operations for ResearchSessions."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, query: str, notes: str | None = None) -> ResearchSession:
        db_session = ResearchSession(query=query, notes=notes)
        self.session.add(db_session)
        self.session.flush()
        return db_session

    def add_article(self, research_session: ResearchSession, article: Article, rank: int) -> None:
        """Link an article to a session with a specific rank."""
        link = SessionArticle(
            session_id=research_session.id,
            article_id=article.id,
            rank=rank
        )
        self.session.add(link)

    def get_with_articles(self, session_id: int) -> ResearchSession | None:
        return self.session.get(ResearchSession, session_id)

    def list_all(self, limit: int = 20) -> list[ResearchSession]:
        return list(
            self.session.execute(
                select(ResearchSession).order_by(ResearchSession.created_at.desc()).limit(limit)
            ).scalars().all()
        )
