# P4 Deployment Runbook

Date: 2026-05-05

## Release State

This runbook supports staging and controlled beta readiness. It does not by itself approve public production launch.

## Required Services

- PostgreSQL
- Redis
- FastAPI backend
- Separate RQ worker
- Frontend static build / frontend server

## Required Production-like Environment

Set explicit non-placeholder values:

```powershell
ENVIRONMENT=staging
DEBUG=false
DATABASE_URL=postgresql://...
SECRET_KEY=<strong secret>
AI_API_KEY=<provider key or explicit disabled provider config>
REDIS_URL=redis://...
RQ_ASYNC=false
STOCK_DATA_TIMEOUT=3.0
STOCK_DATA_CACHE_SECONDS=180
```

Production / staging must use `RQ_ASYNC=false`. `RQ_ASYNC=true` is development-only because jobs run through FastAPI background tasks.

## Database

Before deploy:

```powershell
cd F:\investment\investment-back
alembic current
alembic upgrade head
```

Expected current head from the P3/P4 gate: `013 (head)` unless a newer migration is intentionally added.

Backup requirement:

- Take a PostgreSQL backup before migration.
- Record backup location and restore command in the deployment ticket.
- If migration fails, stop traffic, restore backup, and redeploy the previous backend build.

## Backend

Start API:

```powershell
cd F:\investment\investment-back
$env:RQ_ASYNC="false"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Health checks:

```powershell
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

Expected with Redis reachable and `RQ_ASYNC=false`:

- `/health` returns healthy plus worker mode metadata.
- `/ready` returns 200 ready and Redis healthy.

Expected with Redis unreachable:

- `/ready` returns 503 degraded.
- Traffic should not be sent to this instance.

## Worker

Start a separate worker process:

```powershell
cd F:\investment\investment-back
$env:RQ_ASYNC="false"
python -m src.workers
```

Worker must not be co-located inside FastAPI background tasks for staging / production acceptance.

## Frontend

Build:

```powershell
cd F:\investment\investment-front
npm run build
```

Known current warning:

- Main JS chunk is above 500 kB. This is a beta warning, not currently a P4 blocker unless production policy requires warning-free builds.

## Smoke Acceptance

Run before opening staging:

```powershell
cd F:\investment\investment-back
python -m compileall src tests scripts
pytest -q
alembic current
alembic upgrade head

cd F:\investment\investment-front
npm run lint
npm run test -- --run
npm run build
```

Run E2E against a dedicated test/staging database:

```powershell
cd F:\investment\investment-front
powershell -ExecutionPolicy Bypass -File .\scripts\run-e2e-acceptance.ps1 -PrepareDb -MockMarket -Full
powershell -ExecutionPolicy Bypass -File .\scripts\run-e2e-acceptance.ps1 -PrepareDb -Full
```

## Redis-backed Staging Acceptance Steps

Use these steps to close the current P4 Redis/RQ blocker. Passing local BackgroundTasks mode is not sufficient.

1. Start Redis or provide a staging Redis URL.

```powershell
$env:REDIS_URL="redis://host:6379/0"
python -c "from redis import Redis; import os; r=Redis.from_url(os.environ['REDIS_URL']); assert r.ping() is True; print('redis=healthy')"
```

2. Set the staging environment.

```powershell
$env:ENVIRONMENT="staging"
$env:RQ_ASYNC="false"
$env:REDIS_URL="redis://host:6379/0"
```

Also set the remaining required values from `.env.example`, including `DATABASE_URL`, `SECRET_KEY`, market-data settings, and explicit AI provider configuration.

3. Start FastAPI backend.

```powershell
cd F:\investment\investment-back
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

4. Start the independent worker in a separate process with the same environment.

```powershell
cd F:\investment\investment-back
python -m src.workers
```

5. Start the frontend or deploy the frontend build.

```powershell
cd F:\investment\investment-front
npm run dev
```

6. Run the topology acceptance script.

```powershell
cd F:\investment
powershell -ExecutionPolicy Bypass -File .\investment-back\scripts\run_rq_topology_acceptance.ps1
```

The script must verify Redis ping, `/health`, `/ready`, auth, quick `POST /analysis` enqueue, RQ job presence, independent worker completion, and frontend reachability. Redis unreachable, missing RQ job, or worker non-completion remains a hard failure.

7. Rerun the full P4 checklist in the Redis-backed staging topology.

```powershell
cd F:\investment\investment-back
pytest -q
alembic current
alembic upgrade head

cd F:\investment\investment-front
npm run lint
npm run test -- --run
npm run build
powershell -ExecutionPolicy Bypass -File .\scripts\run-e2e-acceptance.ps1 -PrepareDb -MockMarket -Full
powershell -ExecutionPolicy Bypass -File .\scripts\run-e2e-acceptance.ps1 -PrepareDb -Full
```

8. Update the readiness evidence only with observed results:

- `P4_ONLINE_READINESS_AUDIT.md`
- `P4_ONLINE_READINESS_CHECKLIST.md`
- `P4_COMPLIANCE_SIGNOFF_PACK.md`

Do not promote the gate while Redis/RQ topology, named human compliance/legal sign-off, or the Redis-backed checklist remains incomplete.

## Rollback

Frontend rollback:

- Redeploy previous static build.
- Confirm share and result pages still render.

Backend rollback:

- Stop new traffic.
- Stop worker.
- Redeploy previous backend build.
- Restart worker matching the previous backend.
- Re-check `/health` and `/ready`.

Database rollback:

- Prefer restore from pre-migration backup.
- Only use Alembic downgrade if the migration has been explicitly reviewed as reversible for production data.

Redis / worker rollback:

- Stop current worker.
- Clear or quarantine failed jobs only after saving failure evidence.
- Restart previous worker version.
- Do not mark queued jobs as completed manually.

## Monitoring Checklist

Minimum launch-day observations:

- `/ready` status
- Redis connectivity
- RQ failed job count
- analysis pending / running / completed / failed counts
- market data timeout / degraded counts
- sanitizer / AI guard hit counts
- share page errors
- auth errors
