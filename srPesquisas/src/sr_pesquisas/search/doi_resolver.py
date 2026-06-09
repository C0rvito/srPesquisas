from __future__ import annotations

import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class DOIResolver:
    """Resolves DOIs for articles using Crossref."""

    CROSSREF_URL = "https://api.crossref.org/works"

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def resolve_by_title(self, title: str) -> str | None:
        """Attempt to find a DOI for a given title using Crossref."""
        if not title:
            return None
            
        params = {
            "query.bibliographic": title,
            "rows": 1
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(self.CROSSREF_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                
                items = data.get("message", {}).get("items", [])
                if items:
                    best_match = items[0]
                    # Simple title similarity check (heuristic)
                    match_title = best_match.get("title", [""])[0]
                    t1, t2 = match_title.lower()[:50], title.lower()[:50]
                    if t1 in title.lower() or t2 in match_title.lower():
                        doi = best_match.get("DOI")
                        if doi:
                            return f"https://doi.org/{doi}" if not doi.startswith("http") else doi
                            
        except Exception as exc:
            logger.debug("[DOIResolver] Failed for %r: %s", title[:50], exc)
            
        return None
