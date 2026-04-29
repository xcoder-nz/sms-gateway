# SMS Wallet Demo (DEMO / SIMULATED)

Local-first, provider-agnostic SMS wallet demo using FastAPI + SQLite.

> All balances and money movement are simulated in-app (demo ledger only).

## 1) Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .[test]
cp .env.example .env
python -c "from app.main import app"  # initialize db tables
python app/seed/demo_seed.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open:
- Mobile demo: http://127.0.0.1:8000/
- Admin dashboard: http://127.0.0.1:8000/admin

## 2) Run in a shared cloud environment

The app can run on any VM/container service (Railway/Render/Fly.io/ECS/Kubernetes/etc.) as long as you can expose HTTP endpoints.

### Minimal cloud checklist
1. Build/deploy this repo as a Python web service.
2. Set environment variables from `.env.example`.
3. Start command:
   - `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`
4. Run seed once after first boot:
   - `python app/seed/demo_seed.py`
5. Persist your SQLite file or switch to Postgres for multi-instance/shared deployments.

### Important cloud note
- SQLite is okay for single-instance demos.
- For shared team environments or autoscaling, move to Postgres and set `DATABASE_URL` accordingly.

## 3) Demo SMS commands

### Simulated inbound (works everywhere)
```bash
curl -X POST http://127.0.0.1:8000/api/sms/inbound \
  -H 'content-type: application/json' \
  -d '{"from_number":"0700123456","body":"BAL"}'

curl -X POST http://127.0.0.1:8000/api/sms/inbound \
  -H 'content-type: application/json' \
  -d '{"from_number":"0700123456","body":"PAY 0799001100 120 PIN 1234"}'
```

## 4) Can this interact with real phones/SMS?

### Current state in this repo
- **Inbound from real SMS networks is not turnkey yet.**
- The current backend endpoint `/api/sms/inbound` works and processes canonical payloads.
- `AndroidGatewayAdapter` exists for outbound + payload normalization, but there is no fully wired adapter factory/router yet to switch transports dynamically at runtime.

### iPhone question (direct answer)
- **You cannot use an iPhone as the SMS gateway host for this code path today.**
- Typical “Android SMS gateway” apps run on Android devices and expose an HTTP webhook/API that this app can call.
- You *can* send an SMS from your iPhone **to the Android phone number** (running gateway app), and if that gateway forwards inbound SMS to `/api/sms/inbound`, then this backend can process it.

### Practical demo setup with real phones
1. Run this backend on a public HTTPS URL.
2. Run an Android SMS gateway app on an Android phone with a SIM.
3. Configure the gateway inbound webhook to `POST https://<your-domain>/api/sms/inbound`.
4. Configure outbound API credentials in `.env` (`ANDROID_GATEWAY_URL`, `ANDROID_GATEWAY_TOKEN`).
5. Send SMS from any phone (including iPhone) to the Android gateway SIM number.
6. Watch `/admin` and `/` pages update with SMS logs/transactions.

## 5) Testing

```bash
pytest -q
```
