"""SQLAlchemy ORM models for LitScout."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Research Session  (== "database em uso" / "conjunto de pesquisas")
# ---------------------------------------------------------------------------

class ResearchSession(Base):
    """Represents one search run for a given query / compound."""

    __tablename__ = "research_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    articles: Mapped[list[Article]] = relationship(
        "Article",
        secondary="session_articles",
        back_populates="sessions",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<ResearchSession id={self.id} query={self.query!r}>"


# ---------------------------------------------------------------------------
# Article  (general database)
# ---------------------------------------------------------------------------

class Article(Base):
    """Canonical article record stored in the general database."""

    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint("doi", name="uq_articles_doi"),
        UniqueConstraint("scholar_id", name="uq_articles_scholar_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Core metadata
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    authors: Mapped[str | None] = mapped_column(Text, nullable=True)      # JSON list
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    venue: Mapped[str | None] = mapped_column(String(512), nullable=True)  # journal / conf
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Identifiers
    doi: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    scholar_id: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    openalex_id: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Metrics
    citation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # LLM-generated fields
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-100

    # Provenance
    source: Mapped[str] = mapped_column(
        String(64), default="scholarly"
    )  # scholarly | openalex | crossref
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    sessions: Mapped[list[ResearchSession]] = relationship(
        "ResearchSession",
        secondary="session_articles",
        back_populates="articles",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Article id={self.id} citations={self.citation_count} title={self.title[:60]!r}>"


# ---------------------------------------------------------------------------
# Association table: session <-> article
# ---------------------------------------------------------------------------

class SessionArticle(Base):
    """Many-to-many link between ResearchSession and Article."""

    __tablename__ = "session_articles"

    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("research_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True
    )
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)  # rank within session
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
