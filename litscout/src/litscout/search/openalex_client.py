from __future__ import annotations

import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from litscout.utils.schemas import ArticleData

logger = logging.getLogger(__name__)


class OpenAlexClient:
    """Client for OpenAlex REST API."""

    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, email: str | None = None):
        """
        Initialize the client.
        Providing an email puts you in the 'polite pool' for faster requests.
        """
        self.headers = {}
        if email:
            self.headers["User-Agent"] = f"LitScout/0.1.0 (mailto:{email})"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search(self, query: str, limit: int = 20) -> list[ArticleData]:
        """Search OpenAlex for a query."""
        logger.info("[OpenAlex] Searching for: %r", query)
        params = {
            "search": query,
            "per_page": limit,
            "sort": "cited_by_count:desc"
        }
        
        articles = []
        try:
            with httpx.Client(headers=self.headers, timeout=30.0) as client:
                resp = client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                
                for work in data.get("results", []):
                    # Extract authors
                    authors = [
                        m.get("author", {}).get("display_name") 
                        for m in work.get("authorships", [])
                        if m.get("author", {}).get("display_name")
                    ]
                    
                    # Extract venue
                    location = work.get("primary_location", {}) or {}
                    source = location.get("source") or {}
                    venue = source.get("display_name")
                    
                    article = ArticleData(
                        title=work.get("display_name") or "Unknown Title",
                        authors=authors,
                        year=work.get("publication_year"),
                        venue=venue,
                        abstract=None, # OpenAlex abstract is inverted index, needs processing
                        doi=work.get("doi"),
                        openalex_id=work.get("id"),
                        citation_count=work.get("cited_by_count", 0),
                        source="openalex"
                    )
                    articles.append(article)
                    
            logger.info("[OpenAlex] Found %d articles", len(articles))
        except Exception as exc:
            logger.error("[OpenAlex] Search failed: %s", exc)
            
        return articles
