from __future__ import annotations

import logging

from sr_pesquisas.search.doi_resolver import DOIResolver
from sr_pesquisas.search.openalex_client import OpenAlexClient
from sr_pesquisas.search.scholarly_client import ScholarlyClient
from sr_pesquisas.utils.data_processing import rank_by_citations
from sr_pesquisas.utils.schemas import SearchResult

logger = logging.getLogger(__name__)


class SearchOrchestrator:
    """Orchestrates multi-source academic search."""

    def __init__(self):
        self.scholarly = ScholarlyClient()
        self.openalex = OpenAlexClient()
        self.doi_resolver = DOIResolver()

    def run(self, original_query: str, search_queries: list[str], limit_per_source: int = 15) -> SearchResult:
        """Run search on all sources using planned queries, merge and deduplicate."""
        all_articles = []
        for q in search_queries:
            logger.info("[Orchestrator] Running search for: %r", q)
            # 1. Fetch from sources
            s_results = self.scholarly.search(q, limit=limit_per_source)
            o_results = self.openalex.search(q, limit=limit_per_source)
            all_articles.extend(s_results + o_results)
        
        # 2. Merge and initial ranking/dedup
        # We take a larger N here (e.g. 50) since we will fetch PDFs later
        ranked = rank_by_citations(all_articles, top_n=50)
        
        # 3. DOI Resolution for top articles missing it
        # Try to resolve DOI for top 20 since we'll try to download PDFs
        for art in ranked[:20]:
            if not art.doi:
                art.doi = self.doi_resolver.resolve_by_title(art.title)
        
        return SearchResult(
            query=original_query, # Original query for DB
            articles=ranked,
            top_n=ranked[:20]  # Candidates for PDF fetching
        )
