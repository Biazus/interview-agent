#!/bin/sh
set -e

export QDRANT_HOST="${QDRANT_HOST:-vector-db}"
export QDRANT_PORT="${QDRANT_PORT:-6333}"

echo "Waiting for Qdrant at ${QDRANT_HOST}:${QDRANT_PORT}..."
uv run python -c "from app.core.rag.qdrant_wait import wait_for_qdrant; wait_for_qdrant()"

echo "Applying database migrations..."
uv run alembic upgrade head

exec uv run uvicorn app.api.main:app --host 0.0.0.0 --port 8000
