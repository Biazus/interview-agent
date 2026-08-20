#!/bin/sh
set -e

export QDRANT_HOST="${QDRANT_HOST:-vector-db}"
export QDRANT_PORT="${QDRANT_PORT:-6333}"

echo "Waiting for Qdrant at ${QDRANT_HOST}:${QDRANT_PORT}..."
until uv run python -c "
from qdrant_client import QdrantClient
import os
host = os.environ['QDRANT_HOST']
port = int(os.environ['QDRANT_PORT'])
QdrantClient(host=host, port=port).get_collections()
" 2>/dev/null; do
  sleep 2
done

echo "Applying database migrations..."
alembic upgrade head

echo "Seeding Qdrant..."
uv run python -c "from app.domains.async_messaging.rag_ingestion import ingest_seed_documents; ingest_seed_documents()"

exec uv run uvicorn app.api.main:app --host 0.0.0.0 --port 8000
