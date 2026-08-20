FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

COPY . .

RUN chmod +x scripts/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["scripts/docker-entrypoint.sh"]
