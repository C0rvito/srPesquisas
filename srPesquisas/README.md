# 🔬 srPesquisas

AI-powered academic literature scout. Give it a compound (e.g. `Carvacrol`) and it will:

1. Search **Google Scholar** (via `scholarly`) + **OpenAlex** (Nature, Science, Elsevier, etc.)
2. Merge & deduplicate results with **Polars**
3. Rank top-10 by citation count, refined by an **Ollama LLM**
4. Resolve **DOIs** via Crossref + OpenAlex for every top-10 article
5. Generate AI summaries and relevance scores
6. Persist everything to **SQLite** (or Postgres) via **SQLAlchemy**
7. Display results in a beautiful **Rich** terminal UI

---

## Architecture

```
sr_pesquisas/
├── src/sr_pesquisas/
│   ├── config.py                  # Pydantic settings (env / .env)
│   ├── main.py                    # Typer CLI entry point
│   │
│   ├── search/
│   │   ├── scholarly_client.py    # Google Scholar via scholarly
│   │   ├── openalex_client.py     # OpenAlex REST API (free)
│   │   ├── doi_resolver.py        # Crossref + OpenAlex DOI lookup
│   │   └── orchestrator.py        # Merges all sources → SearchResult
│   │
│   ├── agents/
│   │   ├── state.py               # LangGraph ResearchState schema
│   │   ├── nodes.py               # Individual agent node functions
│   │   └── pipeline.py            # LangGraph graph definition
│   │
│   ├── database/
│   │   ├── models.py              # SQLAlchemy ORM (Article, ResearchSession)
│   │   ├── engine.py              # Engine + session factory
│   │   └── repository.py          # CRUD repository layer
│   │
│   ├── ui/
│   │   └── display.py             # All Rich rendering (tables, panels, progress)
│   │
│   └── utils/
│       ├── schemas.py             # Pydantic DTOs (ArticleData, SearchResult)
│       └── data_processing.py     # Polars: ranking, dedup, stats
│
└── tests/
    └── test_data_processing.py
```

### LangGraph Pipeline

```
START → search_node → ranking_node → summarise_node → persist_node → END
```

| Node | Model | Task |
|------|-------|------|
| `search_node` | — | Multi-source fetch via orchestrator |
| `ranking_node` | `llama3.1:8b` | Re-rank top-N considering relevance |
| `summarise_node` | `mistral:7b` | Generate 2-3 sentence summaries + relevance score |
| `persist_node` | — | SQLAlchemy upsert into DB |

### Database Schema

```
research_sessions ──< session_articles >── articles
```

- **articles** — general database (all ever retrieved)
- **research_sessions** — one per `sr_pesquisas search` run
- **session_articles** — many-to-many with rank

---

## Setup

```bash
# 1. Install uv
curl -Lf https://astral.sh/uv/install.sh | sh

# 2. Create venv + install deps
uv venv
uv pip install -e ".[dev]"

# 3. Configure
cp .env.example .env
# edit .env: set OLLAMA_BASE_URL, models, etc.

# 4. Initialise DB
sr_pesquisas db init

# 5. Run Ollama (separate terminal)
ollama serve
ollama pull llama3.1:8b
ollama pull mistral:7b
```

## Usage

```bash
# Search for a compound
sr_pesquisas search "Carvacrol antimicrobial"

# Top 5 only, skip scholarly
sr_pesquisas search "Thymol antifungal" --top 5 --no-scholarly

# Dry run (no DB write)
sr_pesquisas search "Eugenol" --dry-run

# List sessions
sr_pesquisas sessions

# View session #3
sr_pesquisas session 3

# Browse general DB
sr_pesquisas articles --limit 20
```

## Adding a new LLM / source

- **New search source**: implement a client in `search/` returning `list[ArticleData]`, add to `SearchOrchestrator.run()`
- **New LangGraph node**: add a function in `agents/nodes.py`, wire it in `agents/pipeline.py`
- **New Ollama model**: update `.env` (`OLLAMA_PRIMARY_MODEL`, etc.) — no code change needed
