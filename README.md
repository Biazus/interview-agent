# Interview Agent

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

# Start Qdrant (and optionally the API)
docker compose up -d vector-db

# Run tests
uv run pytest
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
