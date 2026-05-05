# P4 Online Readiness Audit

Date: 2026-05-05

## Final Gate Conclusion

Current state: **C. Blocked**.

Production launch allowed: **No**.

Controlled beta allowed: **No**.

The RealMarket and Redis/RQ blockers from the earlier P4 audit have been closed: RealMarket Full E2E passes, MockMarket Full E2E passes, and the real Redis + separate RQ worker topology acceptance passes with `RQ_ASYNC=false`. The only remaining online-readiness blocker is that formal named human compliance/legal sign-off is still pending.

Recommended next state: **do not public-launch production and do not start controlled beta**. The next gate is not additional business functionality; it is recording a real named human compliance/legal reviewer with role, scope, date, conclusion, notes, remaining risk, and explicit production/beta allowance.

## Phase 0 Worktree Protection

- `git status --short` at handoff showed existing modified files: `PROJECT_CONTEXT.md`, `investment-back/.env.example`, `investment-back/main.py`.
- Existing untracked P4 delivery files were present: `P4_ONLINE_READINESS_AUDIT.md`, `P4_ONLINE_READINESS_CHECKLIST.md`, `tests/test_health_readiness.py`.
- `need.md` had no diff at handoff and remains unmodified.
- This round stayed within P4 online-readiness hardening and did not expand product scope into stock-picking, call-order, return-promise, auto-trading, broker integration, copy trading, or commercial expansion.

## Current Capability Snapshot

P0/P1 baseline exists:

- watchlist server path
- structured result card evidence
- Learning Feedback tests
- analysis failure fallback
- compliance output guard
- reminders / today focus
- unified error protocol

P2 exists:

- holdings and transactions
- portfolio overview
- review growth loop
- share-card service
- AI eval baseline
- entitlement baseline

P3 release-candidate capability exists:

- GrowthService caution context
- AiEvalService deterministic checks
- public share page
- prompt/template metadata
- P3 acceptance pack

## RealMarket E2E Stabilization

Previous blocker:

- 11 passed
- 6 failed
- 5 not run
- 720s suite timeout
- frontend proxy `ECONNRESET`

Root cause found:

- `POST /api/v1/analysis` synchronously loaded full real market detail before creating the async task.
- Worker then loaded the same market detail again.
- Slow or failing external sources could block API requests and destabilize the frontend proxy.
- RealMarket E2E expected ready-only results in places where compliant degraded results should be acceptable.

Fixes completed:

- Analysis creation now validates / normalizes stock id, creates a minimal stock record, and enqueues quickly.
- Full market-data fetch is left to the async job path.
- Market data fetch now degrades by source segment: search, quote, history, profile, announcements.
- Default `STOCK_DATA_TIMEOUT` lowered from `8.0` to `3.0`.
- E2E polling accepts `partial_ready` as a valid terminal result when the requested target is `ready`, while preserving failed-state failure.
- E2E assertions were updated to accept compliant degraded terminal results where external data is incomplete.
- Frontend analysis forms pass `stock_name` in scenario payload so degraded result pages can still show user-recognizable identity.
- Added a regression test for external market outage degradation.

Result:

- RealMarket Full E2E: **22 passed**, about **6.4 minutes**.
- MockMarket Full E2E: **22 passed**, about **2.3 minutes**.
- No 720s timeout in the final RealMarket run.

## Redis/RQ Production Topology

Readiness layer:

- `/health` exposes worker mode and Redis requirement.
- `/ready` checks Redis when `RQ_ASYNC=false` and returns 503 degraded if Redis is unreachable.
- Readiness tests pass.

Topology acceptance status:

- `.venv` was missing `redis`/`rq` despite `requirements.txt`; installed the declared versions locally: `redis==5.0.8`, `rq==1.16.1`.
- No Redis server was available on `localhost:6379`.
- Docker is not installed on this machine.
- `redis-server` command was not available.
- Therefore real Redis + separate `python -m src.workers` + `RQ_ASYNC=false` full chain **was not completed**.

Result: **Must Fix remains open**.

## Compliance

Current state: **Blocked**.

Production launch allowed: **No**.

Controlled beta allowed: **No**.

Added:

- `P4_COMPLIANCE_SIGNOFF_PACK.md`

Grep results:

- Chinese high-risk hits are in allowed contexts: tests, guard/sanitizer word lists, and explicit "not direct trading advice" copy.
- English high-risk hits are in AI eval / sanitizer rules and tests.
- No newly introduced user-visible stock-picking / call-order / guaranteed-return copy was found.

Remaining:

- Formal named human compliance/legal sign-off remains pending.
- Human review of share-card title/summary/disclaimer wording remains required.
- Human review of sanitizer behavior on real model outputs remains required.
- Formal reviewer name, role, date, scope, conclusion, notes, remaining risk, and explicit production/beta allowance must be recorded in the sign-off pack.

## Security, Privacy, And User Isolation

Reviewed and preserved:

- Server-side holding context injection still removes client-supplied `holding_context`.
- Existing portfolio isolation tests pass.
- Analysis ownership lookup filters by `AnalysisTask.user_id`.
- Review task lookup filters by `user_id`.
- Share service tests cover public serializer not exposing user/source ids.
- Frontend passes `stock_name` only as display context; server still rebuilds holding context from persisted holdings.

Current risk:

- No obvious blocker found in this round.
- More systematic cross-user API integration tests remain a Should Fix before public scale.

## Product Loop

Current product loop remains:

analysis -> decision support -> feedback -> review -> growth

Established:

- Home / today focus and reminders provide daily entry points.
- Single-stock analysis renders evidence, counter evidence, risks, invalidation conditions, timestamp, and confidence.
- Pre-trade self-check focuses on emotion, evidence, and position boundary.
- Post-trade review feeds Learning Feedback.
- Portfolio context is injected server-side and affects analysis output.

Needs beta validation:

- Whether reminders create a true daily-use habit.
- Whether users understand degraded data and non-advice boundaries.
- Whether share pages are misunderstood as recommendations.

## Deployment, Monitoring, And Beta Planning

Added:

- `P4_DEPLOYMENT_RUNBOOK.md`
- `P4_CONTROLLED_BETA_PLAN.md`
- `scripts/run_rq_topology_acceptance.ps1`

Runbook covers:

- env requirements
- backend startup
- worker startup
- `/health` and `/ready`
- migration checks
- backup and rollback
- launch-day monitoring indicators

## Final Test Evidence

Passed:

- `python -m compileall src tests scripts`
- `pytest -q`: 117 passed, 131 warnings
- `pytest tests/test_mock_market_data_service.py tests/test_health_readiness.py -q`: 7 passed
- `npm run lint`
- `npm run test -- --run`: 52 passed
- `npm run build`: passed, Vite chunk warning remains
- `alembic current`: `013 (head)`
- `alembic upgrade head`: passed/no-op
- `git diff --check`: no whitespace errors, LF/CRLF warnings only
- MockMarket Full E2E: 22 passed, about 2.3 minutes
- RealMarket Full E2E: 22 passed, about 6.4 minutes

Blocked / not completed:

- Redis/RQ real topology acceptance: Redis server unavailable locally, Docker unavailable.
- Compliance human sign-off: pending.

## Launch Blockers

| Level | Item | Current Evidence | Recommendation |
| --- | --- | --- | --- |
| Closed | Redis/RQ topology accepted | Redis reachable; `/health` healthy; `/ready` ready with Redis healthy and `worker_mode=rq`; quick `POST /analysis`; RQ job found; independent worker moved task to `ready` | Keep as required release evidence |
| Must Fix | Compliance human sign-off pending | Evidence pack created, grep clean for disallowed user-visible copy, but no named human compliance/legal reviewer signature | Complete manual sign-off before public production or controlled beta |
| Should Fix | Vite chunk warning | main JS about 543.83 kB | Accept for beta or split chunks before production |
| Should Fix | Deprecation warnings | FastAPI `on_event`, Pydantic class config, `datetime.utcnow` | Track as hardening |
| Should Fix | More cross-user API isolation tests | Existing focused tests pass | Broaden before public scale |

## Online Recommendation

Do not proceed to public production launch.

The project is materially stronger than the initial P4 Blocked state because RealMarket Full E2E passes, Redis/RQ topology passes, and data-source failures degrade safely. But the conservative final state remains **Blocked** until named human compliance/legal sign-off is complete.

## P4 Final Blocker Closure Attempt - 2026-05-05

Final state after this attempt: **Blocked**.

What changed in this pass:

- `scripts/run_rq_topology_acceptance.ps1` was hardened from a Redis/readiness preflight into a real topology acceptance script.
- The script now requires `RQ_ASYNC=false`, Redis ping, `/health`, `/ready` with `worker_mode=rq` and Redis healthy, frontend reachability, authenticated `POST /analysis`, quick enqueue timing, RQ job presence for the created task, and worker-driven terminal result.
- The script intentionally hard-fails when Redis is unavailable and does not claim readiness from `/ready` alone.
- `P4_COMPLIANCE_SIGNOFF_PACK.md` now records an engineering compliance review and keeps formal human compliance/legal sign-off explicitly pending.

Rerun evidence:

- Backend compile: passed.
- Backend pytest: 117 passed, 131 warnings.
- Targeted readiness / market degradation tests: 7 passed, 21 warnings.
- Frontend lint: passed.
- Frontend unit: 52 passed.
- Frontend build: passed with existing 543.83 kB chunk warning.
- Alembic current: `013 (head)`.
- Alembic upgrade head: passed/no-op.
- MockMarket Full E2E: 22 passed in about 2.4 minutes.
- RealMarket Full E2E: 22 passed in about 7.5 minutes.
- `git diff --check`: no whitespace errors; LF/CRLF warnings only.
- `git diff -- need.md`: no diff.

Redis/RQ topology result:

- Failed / not accepted.
- Local `localhost:6379` refused connections.
- `Test-NetConnection localhost 6379` returned `TcpTestSucceeded=False`.
- Docker is not available in PATH.
- WSL Ubuntu exists, but Redis was not present and the attempted apt-based install did not complete into a usable Redis service.
- `run_rq_topology_acceptance.ps1` failed at Redis ping with `Error 10061 connecting to localhost:6379`.
- No independent `python -m src.workers` production topology acceptance was completed.

Compliance sign-off result:

- Engineering review evidence is recorded only and is not formal named human compliance/legal sign-off.
- Formal named human compliance/legal sign-off: Blocked / Pending.
- Public production compliance gate remains Blocked.
- Controlled beta gate remains Blocked.

Staging checklist result:

- Local production-like checks and both full E2E suites were rerun and passed.
- The checklist was not completed in a true Redis-backed staging topology.
- Because Redis/RQ topology was not accepted, staging readiness cannot be promoted to Controlled Beta Ready.

Current launch decision:

- **Production Online Ready: No.**
- **Staging Ready / Controlled Beta Ready: No.**
- **Blocked: Yes.**

Must Fix:

1. Provide a reachable Redis service or staging Redis URL.
2. Start FastAPI with `RQ_ASYNC=false` and the same `REDIS_URL`.
3. Start a separate worker with `python -m src.workers`.
4. Run and pass `scripts/run_rq_topology_acceptance.ps1` without `-SkipFrontendCheck` against the real frontend/backend topology.
5. Record a named human compliance/legal reviewer, date, scope, result, and notes in `P4_COMPLIANCE_SIGNOFF_PACK.md`.
6. Rerun the P4 checklist in that Redis-backed staging environment.

Should Fix:

- Address the Vite 543.83 kB chunk warning before broad production traffic.
- Track FastAPI/Pydantic/`datetime.utcnow` deprecation warnings.
- Add broader cross-user integration coverage before public scale.

Later:

- Add live provider AI eval samples before enabling any live LLM provider for public production.
- Add launch-day dashboards for Redis/RQ queue depth, failed jobs, degraded market data, and sanitizer hits.

## P4 Redis-backed Staging Acceptance Attempt - 2026-05-05

Final state after this attempt: **Blocked**.

Scope of this pass:

- Re-read the P4 readiness audit, checklist, deployment runbook, compliance sign-off pack, and RQ topology acceptance script.
- Reconfirmed worktree protection before staging acceptance: `git status --short` clean, `git diff -- need.md` clean, and `git diff --check` clean.
- Checked local Redis reachability, process topology, and staging environment variables before running acceptance.
- Executed `investment-back/scripts/run_rq_topology_acceptance.ps1` against the default local topology.

Environment findings:

- `Test-NetConnection -ComputerName localhost -Port 6379` returned `TcpTestSucceeded=False`.
- No `REDIS_URL`, `RQ_ASYNC`, `ENVIRONMENT`, or `DATABASE_URL` variables were set in the current shell before the script.
- Running processes showed PostgreSQL, but no Redis server, FastAPI backend, separate `python -m src.workers` worker, or frontend dev server.
- PostgreSQL processes were present locally, but this was not a complete Redis-backed staging topology.

RQ topology acceptance result:

- **Failed / not accepted**.
- Script environment guard set `RQ_ASYNC=false` and `REDIS_URL=redis://localhost:6379/0`.
- The script failed at Redis ping with `redis.exceptions.ConnectionError: Error 10061 connecting to localhost:6379`.
- Because Redis was unreachable, the acceptance did not proceed to `/health`, `/ready`, frontend reachability, auth/login, quick `POST /analysis`, RQ job presence, worker consumption, or terminal task status.
- No BackgroundTasks fallback was used and the Redis/RQ blocker remains open.

P4 checklist status:

- The full P4 checklist was not rerun in Redis-backed staging topology because phase-one Redis topology preflight failed.
- Previous local non-Redis evidence remains useful history, but cannot promote staging readiness.
- `need.md` remained unmodified during this attempt.

Compliance sign-off status:

- No named human legal/compliance reviewer was provided in this environment.
- Engineering conditional review remains the only recorded review.
- Formal compliance/legal sign-off remains **Blocked / Pending**.

Launch decision:

- **Production Online Ready: No.**
- **Staging Ready / Controlled Beta Ready: No.**
- **Blocked: Yes.**

Remaining Must Fix:

1. Provide a reachable staging Redis URL or start a real Redis service.
2. Start FastAPI with `ENVIRONMENT=staging`, `RQ_ASYNC=false`, and the same `REDIS_URL`.
3. Start a separate worker with `python -m src.workers`.
4. Start the frontend and run `scripts/run_rq_topology_acceptance.ps1` without skipping frontend checks.
5. Rerun the full P4 checklist in that Redis-backed staging topology.
6. Record a named human compliance/legal reviewer with role, date, reviewed scope, conclusion, notes, and remaining risk.

## P4 Redis-backed Staging Acceptance Rerun - 2026-05-05

Final state after this rerun: **Blocked**.

What changed in this pass:

- Redis became reachable at `redis://localhost:6379/0`; Python Redis ping returned `True` and `Test-NetConnection localhost:6379` returned `TcpTestSucceeded=True`.
- Fixed `scripts/run_rq_topology_acceptance.ps1` scope/quoting issues so the script carries the auth token and analysis id across steps and preserves embedded Python strings.
- Fixed Redis/RQ dispatch startup path:
  - `src/workers/dispatcher.py` now imports `rq.Queue` in the queue creation path without a local-scope cache bug.
  - `src/workers/worker_main.py` uses RQ `SimpleWorker` plus `TimerDeathPenalty` on Windows, avoiding unsupported `os.fork()` and `SIGALRM`.
- Re-ran RQ topology acceptance with Redis, FastAPI, independent worker, and frontend.

Redis/RQ topology result:

- **Passed**.
- Verified by `powershell -NoProfile -ExecutionPolicy Bypass -File .\investment-back\scripts\run_rq_topology_acceptance.ps1 -User p4redis_<timestamp> -Password testpassword123`.
- Evidence:
  - Redis ping: healthy.
  - `/health`: healthy; Redis required; worker mode `rq`.
  - `/ready`: ready; database healthy; Redis healthy; worker mode `rq`.
  - Frontend: reachable with HTTP 200.
  - Auth/register: succeeded for a fresh acceptance user.
  - `POST /analysis`: quick enqueue in about 0.46s.
  - RQ job: present in Redis with status `started`.
  - Worker terminal result: task moved from `processing` to `ready`.
  - Script final line: `RQ topology acceptance passed.`

Full checklist rerun:

- Backend `pytest -q`: **117 passed, 131 warnings**.
- Targeted readiness / market degradation tests: **7 passed, 21 warnings**.
- `alembic current`: **013 (head)**.
- `alembic upgrade head`: **passed/no-op**.
- Frontend `npm run lint`: **passed**.
- Frontend `npm run test -- --run`: **52 passed**.
- Frontend `npm run build`: **passed**, Vite chunk warning remains at about **543.83 kB**.
- MockMarket Full E2E with Redis/RQ worker and E2E DB: **22 passed**, about **2.6 minutes**.
- RealMarket Full E2E with Redis/RQ worker and E2E DB: **22 passed**, about **7.2 minutes**.
- `git diff --check`: no whitespace errors; LF/CRLF warnings only.
- `git diff -- need.md`: no diff.
- Compliance grep: hits remain in tests, sanitizer/guard lists, behavior labels, transaction/self-check contexts, and explicit non-advice copy.

Important E2E note:

- The E2E script's Playwright backend command uses `python`; to keep `RQ_ASYNC=false` with declared `rq`/`redis` dependencies, the run prepended `F:\investment\investment-back\.venv\Scripts` to `PATH`.
- Independent workers were started separately for MockMarket and RealMarket with the E2E database and matching market-data environment.
- No BackgroundTasks fallback was used for the accepted RQ topology.

Compliance sign-off result:

- Engineering compliance review evidence is recorded only and is not formal named human compliance/legal sign-off.
- Formal named human compliance/legal sign-off remains **Blocked / Pending**.
- No human reviewer name, role, date, conclusion, notes, or remaining-risk acceptance was provided in this environment.

Current launch decision:

- **Production Online Ready: No.**
- **Staging Ready / Controlled Beta Ready: No under the requested final gate, because formal human compliance/legal sign-off remains incomplete.**
- **Blocked: Yes.**

Remaining Must Fix:

1. Record formal named human compliance/legal sign-off covering share cards, disclaimers, sanitizer, AI eval samples, and user-visible flows.

Remaining Should Fix:

- Address the Vite chunk warning before broader production traffic.
- Track FastAPI/Pydantic/`datetime.utcnow` deprecation warnings.
- Consider making the E2E backend command explicitly use the backend virtualenv so Redis/RQ dependencies are never missed when `RQ_ASYNC=false`.
