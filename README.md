# Confluencr Webhook Processor

FastAPI service for receiving payment transaction webhooks, acknowledging immediately, and processing reliably in the background with idempotency.

## What This Project Does

- Accepts transaction webhook requests at `POST /v1/webhooks/transactions`
- Returns `202 Accepted` quickly
- Processes the transaction asynchronously with configured delay
- Stores transaction state in PostgreSQL
- Prevents duplicate processing by `transaction_id`
- Exposes status endpoint for verification/testing

## Request Flow (How We Handle It)

1. Webhook hits `POST /v1/webhooks/transactions`
2. Payload validated via Pydantic DTO
3. Service checks idempotency hash + transaction ID
4. Repository performs DB write/read
5. API returns `202 Accepted`
6. Background task simulates processing delay and updates status to:
   - `PROCESSED` on success
   - `FAILED` on error
7. `GET /v1/transactions/{transaction_id}` returns current state

## Endpoints

### `GET /`
Health check.

### `POST /v1/webhooks/transactions`
Accepts webhook payload:

```json
{
  "transaction_id": "txn_abc123def456",
  "source_account": "acc_user_789",
  "destination_account": "acc_merchant_456",
  "amount": 1500,
  "currency": "INR"
}
```

Response:

```json
{
  "acknowledged": true,
  "transaction_id": "txn_abc123def456"
}
```

### `GET /v1/transactions/{transaction_id}`
Returns persisted transaction status and timestamps.

## Project Modules and Use Cases

- `app/main.py`
  - FastAPI app bootstrap and startup/shutdown lifecycle.
  - Ensures DB tables exist on startup.

- `app/router/`
  - HTTP route layer only.
  - Delegates business logic to services.

- `app/services/`
  - Business logic orchestration.
  - `webhook_service.py`: idempotency and stale retry decision.
  - `processor.py`: async background processing and status transitions.
  - `transaction_service.py`: read/query use case.

- `app/repositories/`
  - DB operations (SQLAlchemy ORM queries/writes).
  - Isolates persistence logic from services/routes.

- `app/models/`
  - SQLAlchemy ORM entities.

- `app/dto/`
  - Pydantic input/output schemas for API contracts.

- `app/utils/`
  - Config, DB session/engine, enums, runtime signals, helper utilities.

- `alembic/`
  - Migration scripts for versioned schema changes.

- `tests/`
  - Integration-oriented tests for health, idempotency, delay, failures.

## Tech Stack

- FastAPI
- Pydantic v2
- SQLAlchemy 2.x ORM
- PostgreSQL
- Alembic
- Pytest
- Docker / Docker Compose

## Run Locally (Supabase Postgres + local API)

### 1. Create `.env`

```env
DATABASE_URL=postgresql+psycopg2://postgres.<project_ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
PROCESSING_DELAY_SECONDS=30
PROCESSING_STALE_TIMEOUT_SECONDS=120
LOG_LEVEL=INFO
```

Notes:
- Use Supabase connection string values from your project settings.
- This app auto-creates missing tables from ORM models at startup.

### 2. Install and run

```bash
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

### 3. Optional migration (recommended for team environments)

```bash
alembic upgrade head
```

## Quick Start with Docker (Fastest Local Setup)

### Start API + Postgres

```bash
docker compose up -d --build
```

### Check API

```bash
curl http://localhost:8000/
```

### Stop

```bash
docker compose down
```

### Reset DB (if needed)

```bash
docker compose down -v
```

## Testing

```bash
.\venv\Scripts\python.exe -m pytest -q
```

or

```bash
pytest -q
```

## Reliability Notes

- Duplicate webhook with same payload: accepted, no duplicate processing.
- Duplicate webhook with different payload: accepted, conflict tracked.
- On shutdown, app disposes DB connections only; tables are not deleted.
- If Alembic is not run, startup still creates missing tables from models.
