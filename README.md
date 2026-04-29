# SMS Wallet Demo (DEMO / SIMULATED)

Local-first, provider-agnostic SMS wallet demo using FastAPI with Alembic-managed schema migrations.

## Quick start (local dev)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .[test]
cp .env.example .env
alembic upgrade head
python app/seed/demo_seed.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open:
- Mobile demo: http://127.0.0.1:8000/
- Admin dashboard: http://127.0.0.1:8000/admin
- Health check: http://127.0.0.1:8000/health

## Schema evolution (Alembic)

Use migrations instead of implicit table creation:

```bash
alembic upgrade head      # apply latest schema
alembic downgrade -1      # roll back one migration
alembic downgrade base    # clear schema
```

## Environment profiles + startup behavior

Profiles are stored in `.env.dev`, `.env.demo`, `.env.prod`:

- `dev`: sqlite + reload/debug + mock adapters
- `demo`: postgres + no reload + mock SMS
- `prod`: postgres + no reload + android SMS adapter

Run with profile:

```bash
./scripts/start.sh dev
./scripts/start.sh demo
./scripts/start.sh prod
```

The start script validates the profile, loads the matching env file when present, runs `alembic upgrade head`, then starts Uvicorn. For hosted `prod` deployments (e.g., Render), it can run without `.env.prod` as long as required environment variables are set in the platform config.

## Docker / Compose (prod-like local)

Build app image:

```bash
docker build -t sms-gateway .
```

Run app + Postgres locally:

```bash
docker compose up --build
```

This uses `.env.demo` for the app container and a Postgres 16 service.

## Shared cloud deployment runbook

### 1) Provision
- Deploy app container/image using `Dockerfile`.
- Provision managed Postgres.
- Set env vars (from `.env.prod` baseline) with secure credentials.

### 2) Bootstrap
```bash
alembic upgrade head
python app/seed/demo_seed.py
```

### 3) Runtime command
```bash
./scripts/start.sh prod
```

### 4) Health checks
- Liveness/readiness endpoint: `GET /health`
- Expected payload includes `ok`, active profile (`mode`), and selected adapter.

### 5) Ops commands
Seed data:
```bash
./scripts/seed.sh
```

Reset schema + reseed:
```bash
./scripts/reset_db.sh
```

### 6) Notes for shared environments
- Prefer Postgres for multi-user/shared deployments.
- Run migrations on deploy before switching traffic.
- Keep seed/reset scripts restricted to non-production or controlled maintenance windows.

## Demo SMS commands

```bash
curl -X POST http://127.0.0.1:8000/api/sms/inbound \
  -H 'content-type: application/json' \
  -d '{"from_number":"0700123456","body":"BAL"}'

curl -X POST http://127.0.0.1:8000/api/sms/inbound \
  -H 'content-type: application/json' \
  -d '{"from_number":"0700123456","body":"PAY 0799001100 120 PIN 1234"}'
```

## Testing

```bash
pytest -q
```
