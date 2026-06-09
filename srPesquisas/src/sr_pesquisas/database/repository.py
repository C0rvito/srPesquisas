from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from sr_pesquisas.database.models import Article, Interaction, ResearchSession, SessionArticle
from sr_pesquisas.utils.schemas import ArticleData


class ArticleRepository:
    """Operações CRUD para Artigos."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_doi(self, doi: str) -> Article | None:
        return self.session.execute(select(Article).where(Article.doi == doi)).scalar_one_or_none()

    def get_by_scholar_id(self, scholar_id: str) -> Article | None:
        return self.session.execute(
            select(Article).where(Article.scholar_id == scholar_id)
        ).scalar_one_or_none()

    def upsert(self, data: ArticleData) -> Article:
        """Insere ou atualiza um artigo baseado no DOI ou ID do Scholar."""
        article = None
        if data.doi:
            article = self.get_by_doi(data.doi)
        if not article and data.scholar_id:
            article = self.get_by_scholar_id(data.scholar_id)

        if article:
            # Atualiza existente
            article.citation_count = max(article.citation_count, data.citation_count)
            if data.abstract and not article.abstract:
                article.abstract = data.abstract
            if data.ai_summary:
                article.ai_summary = data.ai_summary
            if data.relevance_score:
                article.relevance_score = data.relevance_score
        else:
            # Cria novo
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

    def search_all_articles(self, keyword: str, limit: int = 50) -> list[Article]:
        """Busca artigos em todas as sessões por título, abstract ou resumo."""
        search_filter = f"%{keyword}%"
        return list(
            self.session.execute(
                select(Article)
                .where(
                    (Article.title.ilike(search_filter)) |
                    (Article.abstract.ilike(search_filter)) |
                    (Article.ai_summary.ilike(search_filter)) |
                    (Article.authors.ilike(search_filter))
                )
                .order_by(Article.citation_count.desc())
                .limit(limit)
            ).scalars().all()
        )

    def get_all_articles(self) -> list[dict]:
        """Retorna todos os artigos com suas respectivas queries de sessão para o navegador."""
        result = self.session.execute(
            select(Article, ResearchSession.query)
            .join(SessionArticle, Article.id == SessionArticle.article_id)
            .join(ResearchSession, ResearchSession.id == SessionArticle.session_id)
        ).all()
        
        articles_data = []
        for art, query in result:
            articles_data.append({
                "id": art.id,
                "title": art.title,
                "authors": art.authors or "[]",
                "year": art.year,
                "citation_count": art.citation_count,
                "source": art.source,
                "compound": query  # Adiciona o composto associado
            })
        return articles_data


class SessionRepository:
    """Operações CRUD para ResearchSessions."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, query: str, notes: str | None = None) -> ResearchSession:
        db_session = ResearchSession(query=query, notes=notes)
        self.session.add(db_session)
        self.session.flush()
        return db_session

    def add_article(self, research_session: ResearchSession, article: Article, rank: int) -> None:
        """Vincula um artigo a uma sessão com um ranking específico."""
        link = SessionArticle(
            session_id=research_session.id,
            article_id=article.id,
            rank=rank
        )
        self.session.add(link)
        self.session.flush()
        # Expira para atualizar relacionamentos
        self.session.expire(research_session, ["articles"])

    def update_analysis_path(self, session_id: int, path: str) -> None:
        """Atualiza o caminho do arquivo de análise técnica em bib/."""
        db_session = self.session.get(ResearchSession, session_id)
        if db_session:
            db_session.analysis_path = path
            self.session.flush()

    def get_with_articles(self, session_id: int) -> ResearchSession | None:
        """Busca uma sessão e seus artigos."""
        return self.session.execute(
            select(ResearchSession)
            .where(ResearchSession.id == session_id)
        ).scalar_one_or_none()

    def get_session_articles(self, session_id: int) -> list[tuple[Article, int]]:
        """Busca todos os artigos de uma sessão com seus rankings."""
        result = self.session.execute(
            select(Article, SessionArticle.rank)
            .join(SessionArticle, Article.id == SessionArticle.article_id)
            .where(SessionArticle.session_id == session_id)
            .order_by(SessionArticle.rank)
        ).all()
        return [(row[0], row[1]) for row in result]

    def list_all(self, limit: int = 20) -> list[ResearchSession]:
        return list(
            self.session.execute(
                select(ResearchSession).order_by(ResearchSession.created_at.desc()).limit(limit)
            ).scalars().all()
        )


class InteractionRepository:
    """Operações CRUD para interações/perguntas à base de conhecimento."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, question: str, answer: str, file_path: str | None = None) -> Interaction:
        interaction = Interaction(question=question, answer=answer, file_path=file_path)
        self.session.add(interaction)
        self.session.flush()
        return interaction

    def list_all(self, limit: int = 20) -> list[Interaction]:
        return list(
            self.session.execute(
                select(Interaction).order_by(Interaction.created_at.desc()).limit(limit)
            ).scalars().all()
        )
