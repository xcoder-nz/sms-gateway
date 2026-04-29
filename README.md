# SMS Wallet Demo (DEMO / SIMULATED)

Local-first, provider-agnostic SMS wallet demo using FastAPI + SQLite.

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .[test]
cp .env.example .env
python -c "from app.main import app"  # initialize db
python app/seed/demo_seed.py
uvicorn app.main:app --reload
```

Open:
- Mobile demo: http://127.0.0.1:8000/
- Admin dashboard: http://127.0.0.1:8000/admin

## Demo SMS

```bash
curl -X POST http://127.0.0.1:8000/api/sms/inbound -H 'content-type: application/json' -d '{"from_number":"0700123456","body":"BAL"}'
curl -X POST http://127.0.0.1:8000/api/sms/inbound -H 'content-type: application/json' -d '{"from_number":"0700123456","body":"PAY 0799001100 120 PIN 1234"}'
```
