MAX_ANSWER_LENGTH = 4096

RAG_SEED_DOCKER_CMD = "docker compose --profile seed run --rm seed"
RAG_SEED_UV_CMD = "uv run python scripts/run_seed.py"
RAG_SEED_RUNBOOK_HINT = f"Execute: {RAG_SEED_DOCKER_CMD} — ou: {RAG_SEED_UV_CMD}"
