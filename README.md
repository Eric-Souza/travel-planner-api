# Travel Planner API

Local-first AI travel planner backend. Owns all persistence, AI orchestration, file processing, business rules, and the public REST/SSE API consumed by [travel-planner-mobile](https://github.com/Eric-Souza/travel-planner-mobile).

## Tech stack

| Area | Choice |
|------|--------|
| Language | Python 3.12+ |
| Web framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Validation / DTOs | [Pydantic v2](https://docs.pydantic.dev/) |
| Settings | `pydantic-settings` |
| ORM | [SQLAlchemy 2.x](https://www.sqlalchemy.org/) (async) |
| Migrations | [Alembic](https://alembic.sqlalchemy.org/) (PostgreSQL path) |
| Database (dev default) | SQLite via `aiosqlite` |
| Database (production path) | PostgreSQL + [pgvector](https://github.com/pgvector/pgvector) |
| HTTP server | [Uvicorn](https://www.uvicorn.org/) |
| HTTP client | [httpx](https://www.python-httpx.org/) |
| PDF parsing | [PyMuPDF](https://pymupdf.readthedocs.io/) |
| EML parsing | Python `email` stdlib |
| Streaming | [sse-starlette](https://github.com/sysid/sse-starlette) |
| LLM (local) | [Ollama](https://ollama.com/) behind `LLMProvider` abstraction |
| LLM (dev fallback) | `MockLLMProvider` when Ollama is unavailable or `USE_MOCK_LLM=true` |
| File storage | Local disk (`data/uploads/`) |
| Live data tools | Open-Meteo, open.er-api.com, Nominatim, OSRM (backend adapters only) |
| Testing | [pytest](https://docs.pytest.org/) + pytest-asyncio |
| Linting | [Ruff](https://docs.astral.sh/ruff/) |
| Packaging | [Hatchling](https://hatch.pypa.io/) / `pyproject.toml` |
| Containers | Docker Compose (PostgreSQL + pgvector) |

**Intentionally not used:** LangChain, LlamaIndex, paid LLM APIs, multi-agent frameworks, cloud deployment in v1.

## Quick start

**Windows (PowerShell):**

```powershell
.\scripts\setup.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**macOS / Linux:**

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Manual setup:**

```bash
pip install -e ".[dev]"
cp .env.example .env    # edit CORS_ORIGINS with your LAN IP for mobile testing
python scripts/seed_demo.py
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API docs: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json
- Health: http://localhost:8000/health

## Environment

Copy `.env.example` to `.env` (or run `scripts/setup.ps1` / `scripts/setup.sh`).

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLite by default; switch to PostgreSQL for pgvector |
| `CORS_ORIGINS` | Expo dev URLs — include your LAN IP for physical devices |
| `UPLOADS_DIR` | Local path for uploaded PDFs/EML/TXT |
| `USE_MOCK_LLM` | `true` = no Ollama required; `false` when Ollama is running |
| `OLLAMA_*` | Model names when using real Ollama |

Defaults use SQLite (`./data/travel_planner.db`) and mock LLM (`USE_MOCK_LLM=true`) so you can run without Docker or Ollama.

For PostgreSQL + pgvector:

```bash
docker compose up -d postgres
# set DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/travel_planner
```

Set `CORS_ORIGINS` to include your Expo dev server (e.g. `http://localhost:8081` and your LAN IP).

## Tests

```bash
python -m pytest
python -m ruff check .
```

## Project structure

```
app/
  main.py                 FastAPI app, CORS, lifespan, error handlers
  api/v1/routes/          Thin HTTP routes (no business logic)
  core/                   Config, logging, errors, request IDs
  db/                     SQLAlchemy engine, sessions, init
  models/tables.py        ORM models
  schemas/                Pydantic request/response DTOs
  services/               Business logic (trips, documents, RAG, chat, planner, tools)
  evals/                  Evaluation fixtures
scripts/seed_demo.py      Synthetic Buenos Aires + Bariloche trip
tests/                    pytest suite
```

## Main endpoints

| Area | Endpoints |
|------|-----------|
| Trips | `POST/GET /v1/trips`, `GET/PATCH /v1/trips/{id}` |
| Preferences | `GET/PATCH /v1/trips/{id}/preferences` |
| Bookings | `POST/GET /v1/trips/{id}/bookings`, `POST /v1/bookings/{id}/confirm` |
| Documents | `POST /v1/trips/{id}/documents`, `POST /v1/documents/{id}/process` |
| RAG | `POST /v1/trips/{id}/search`, `POST /v1/trips/{id}/ask-document-question` |
| Chat | `POST /v1/trips/{id}/chat/stream` (SSE) |
| Itinerary | `POST /v1/trips/{id}/itinerary-proposals`, `POST .../apply` |
| Places | `GET/POST /v1/trips/{id}/places` |
| Eval (dev) | `POST /v1/eval/run` |

All `/v1` responses use `{ "data": ..., "request_id": "req_..." }`.

## Architecture rules

- **Routes** are thin; business logic lives in `app/services/`
- **LLMs propose**; Python validates; **users confirm** extracted bookings and itinerary applies
- **SQL** is authoritative for structured booking facts; **RAG** for document details; **tools** for live data
- **LLM** via `LLMProvider` (`OllamaProvider` + `MockLLMProvider`)
- Bookings from extraction stay `extracted` until `POST /bookings/{id}/confirm`
- Itinerary proposals never auto-apply

## Documentation

- [AI layer guide](docs/ai-layer.md) — LLMs, prompts, RAG, and chat streaming (with code map)

## Cursor / AI assistant setup

Copy the contents of [`CURSOR.md`](CURSOR.md) into a Cursor rule or project instruction, or rely on the auto-loaded rule at `.cursor/rules/project.md`.

## Related repo

Mobile client: **travel-planner-mobile** — presentation and typed API calls only; never calls Ollama or the database directly.
