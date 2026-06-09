from __future__ import annotations

import polars as pl

from sr_pesquisas.utils.schemas import ArticleData


def rank_by_citations(articles: list[ArticleData], top_n: int = 10) -> list[ArticleData]:
    """
    Deduplicate and rank articles by citation count using Polars.
    
    Priority for deduplication:
    1. DOI
    2. Title (normalized)
    """
    if not articles:
        return []

    # Convert to list of dicts for Polars
    data = [a.model_dump() for a in articles]
    df = pl.DataFrame(data)

    # Normalize titles for better deduplication
    df = df.with_columns(
        pl.col("title").str.to_lowercase().str.strip_chars().alias("norm_title")
    )

    # Deduplicate by DOI (if present)
    df_doi = df.filter(pl.col("doi").is_not_null()).unique(subset=["doi"], keep="any")
    df_no_doi = df.filter(pl.col("doi").is_null())
    
    df = pl.concat([df_doi, df_no_doi])

    # Deduplicate by title
    df = df.unique(subset=["norm_title"], keep="any")

    # Sort and take top N
    df = df.sort("citation_count", descending=True).head(top_n)

    # Convert back to ArticleData
    ranked_dicts = df.to_dicts()
    return [ArticleData(**d) for d in ranked_dicts]
