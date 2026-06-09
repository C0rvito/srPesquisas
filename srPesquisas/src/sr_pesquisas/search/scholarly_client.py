from __future__ import annotations

import logging

from scholarly import scholarly

from sr_pesquisas.utils.schemas import ArticleData

logger = logging.getLogger(__name__)


class ScholarlyClient:
    """Client for Google Scholar using the scholarly library."""

    def search(self, query: str, limit: int = 20) -> list[ArticleData]:
        """Search Google Scholar for a query."""
        logger.info("[Scholarly] Searching for: %r", query)
        articles = []
        try:
            search_query = scholarly.search_pubs(query)
            for i, pub in enumerate(search_query):
                if i >= limit:
                    break
                
                bib = pub.get("bib", {})
                year_raw = bib.get("pub_year")
                year = int(year_raw) if year_raw and year_raw.isdigit() else None
                
                # Extract citation count safely
                citations = pub.get("num_citations", 0)
                
                article = ArticleData(
                    title=bib.get("title", "Unknown Title"),
                    authors=bib.get("author", []),
                    year=year,
                    venue=bib.get("venue") or bib.get("journal"),
                    abstract=bib.get("abstract"),
                    # Note: scholarly uses 'author_id' for something else usually
                    scholar_id=pub.get("author_id"),
                    citation_count=citations,
                    source="scholarly"
                )
                articles.append(article)
                
            logger.info("[Scholarly] Found %d articles", len(articles))
        except Exception as exc:
            logger.error("[Scholarly] Search failed: %s", exc)
            
        return articles
