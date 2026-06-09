from __future__ import annotations

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Ollama / LLM
    ollama_base_url: str = "http://localhost:11434"
    ollama_ranking_model: str = "llama3.3:70b"
    ollama_summary_model: str = "llama3.3:70b"
    ollama_vision_model: str = "llama3.2-vision:90b"
    ollama_num_ctx: int = 64000  # Massive context for full PDFs

    # Search Configuration
    top_n_ranked: int = 10

    # Database
    database_url: str = "sqlite:///./data/sr_pesquisas.db"


settings = Settings()
