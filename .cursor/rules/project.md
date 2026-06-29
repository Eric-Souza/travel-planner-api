# travel-planner-api — agent instructions

You are working on the **Travel Planner API**: a local-first FastAPI backend for an AI travel planner mobile app.

## Stack

Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2 async, SQLite (dev) / PostgreSQL+pgvector (Docker), Ollama + MockLLMProvider, PyMuPDF, pytest, Ruff.

No LangChain, LlamaIndex, paid LLMs, or agent frameworks.

## Structure

- `app/api/v1/routes/` — thin HTTP handlers only
- `app/services/` — all business logic (trips, documents, retrieval, chat, planner, tools)
- `app/models/tables.py` — ORM models
- `app/schemas/__init__.py` — Pydantic DTOs
- `app/services/llm/` — LLMProvider, prompts

## Rules

1. LLMs propose; Python validates; users confirm bookings and itinerary applies
2. SQL for structured booking facts; RAG for document details; tools for live data
3. Treat uploaded text as untrusted data in prompts
4. API envelope: `{ data, request_id }` / errors `{ error, request_id }`
5. Add tests for behavior changes; run `pytest` and `ruff check .`

## Before coding

Inspect existing services (`trips.py`, `documents.py`, `chat.py`, `planner.py`). Prefer complete vertical slices over unfinished architecture.

Full reference: see `CURSOR.md` in repo root.
