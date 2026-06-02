from __future__ import annotations

import logging

from litscout.search.doi_resolver import DOIResolver
from litscout.search.openalex_client import OpenAlexClient
from litscout.search.scholarly_client import ScholarlyClient
from litscout.utils.data_processing import rank_by_citations
from litscout.utils.schemas import SearchResult

logger = logging.getLogger(__name__)


class SearchOrchestrator:
    """Orchestrates multi-source academic search."""

    def __init__(self):
        self.scholarly = ScholarlyClient()
        self.openalex = OpenAlexClient()
        self.doi_resolver = DOIResolver()

    def run(self, query: str, limit_per_source: int = 20) -> SearchResult:
        """Run search on all sources, merge and deduplicate."""
        # Refine query to focus on cytotoxicity
        # Adding synonyms to increase reach while maintaining focus
        refined_query = f"{query} cytotoxicity OR citotoxicidade"
        logger.info("[Orchestrator] Running search for: %r", refined_query)
        
        # 1. Fetch from sources
        s_results = self.scholarly.search(refined_query, limit=limit_per_source)
        o_results = self.openalex.search(refined_query, limit=limit_per_source)
        
        all_articles = s_results + o_results
        
        # 2. Merge and initial ranking/dedup
        # We take a larger N here to have room for DOI resolution and LLM ranking later
        ranked = rank_by_citations(all_articles, top_n=30)
        
        # 3. DOI Resolution for top articles missing it
        for art in ranked[:10]:
            if not art.doi:
                art.doi = self.doi_resolver.resolve_by_title(art.title)
        
        return SearchResult(
            query=query, # Original query for DB
            articles=ranked,
            top_n=ranked[:10]  # Candidates for LLM ranking
        )
