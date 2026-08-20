# Interview Agent - WIP

An AI-powered system that conducts technical interviews using agents. Instead of a static question list, the agent adapts to the domain, retrieves relevant reference material, and evaluates answers against a structured rubric.

## How it works

Each interview domain (e.g. **async messaging** with SQS, SNS, Lambda) bundles three capabilities:

- **Question bank** — curated questions by topic and difficulty
- **RAG retriever** — semantic search over domain knowledge (Qdrant + embeddings) to ground the agent's responses
- **Rubric provider** — criteria for scoring answers (weak / medium / strong examples)

A central **registry** wires domains at startup. The orchestrator picks a domain, asks questions, retrieves context, and uses an LLM to evaluate the candidate's answers.

## Stack

- **FastAPI** — HTTP API
- **Qdrant** — vector store for RAG
- **LLM providers** — Groq and OpenRouter, with fallback chain
- **Python 3.13+**, managed with [uv](https://docs.astral.sh/uv/)

## Getting started

```bash
# Install dependencies
uv sync

# Start containers (Postgres dev DB + Qdrant)
docker compose up -d postgres vector-db

# Apply database migrations (dev DB: interview_agent)
uv run alembic upgrade head

# Run tests (uses interview_agent_test — created by scripts/init-databases.sql)
# Ensure Postgres is up; schema is created automatically by pytest fixtures.
uv run pytest tests/unit tests/api          # Fase 0/1 (sem Qdrant)
uv run pytest tests/unit                    # rápido, sem Postgres para auth unitários
uv run pytest tests/integration             # RAG (requer docker compose up -d + seed)
uv run pytest                               # tudo
```

## Project layout

```
app/
├── api/              # FastAPI routes
├── core/
│   ├── domain/       # Registry, interfaces (Question, Rubric, Chunk)
│   ├── llm/          # LLM providers and fallback
│   └── rag/          # Embeddings, vector store, retriever
└── domains/
    └── async_messaging/   # First domain: questions, rubrics, RAG seed data
```

New domains (Kafka, RabbitMQ, etc.) can be added by implementing the three interfaces and registering a factory in the registry.
