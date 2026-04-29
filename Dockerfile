FROM python:3.11-slim
WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts

RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["./scripts/start.sh", "prod"]
