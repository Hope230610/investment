# P4 Online Readiness Audit

Date: 2026-05-05

## Final Gate Conclusion

Current state: **Blocked for Production Online Ready**.

The main RealMarket blocker from the previous P4 audit was fixed in this round: RealMarket Full E2E now passes from a prepared E2E database. However, production launch remains blocked because the real Redis + separate RQ worker topology could not be accepted on this machine and formal human compliance sign-off is still pending.

Recommended next state: **continue P4 hardening; do not public-launch production**. Once Redis/RQ topology and compliance sign-off are complete, the project may be reconsidered for **Staging Ready / Controlled Beta Ready**.

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

Current state: **Conditional Pass for controlled staging/beta evidence; Blocked for production without human sign-off**.

Added:

- `P4_COMPLIANCE_SIGNOFF_PACK.md`

Grep results:

- Chinese high-risk hits are in allowed contexts: tests, guard/sanitizer word lists, and explicit "not direct trading advice" copy.
- English high-risk hits are in AI eval / sanitizer rules and tests.
- No newly introduced user-visible stock-picking / call-order / guaranteed-return copy was found.

Remaining:

- Human review of share-card title/summary/disclaimer wording.
- Human review of sanitizer behavior on real model outputs.
- Formal reviewer/date/result recorded in the sign-off pack.

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
| Must Fix | Redis/RQ topology not accepted | Redis package installed, but no Redis server / Docker available; full worker chain not run | Run real Redis + API + separate worker + frontend with `RQ_ASYNC=false` |
| Must Fix | Compliance human sign-off pending | Evidence pack created, grep clean for disallowed user-visible copy, but no reviewer signature | Complete manual sign-off before public production |
| Should Fix | Vite chunk warning | main JS about 543.83 kB | Accept for beta or split chunks before production |
| Should Fix | Deprecation warnings | FastAPI `on_event`, Pydantic class config, `datetime.utcnow` | Track as hardening |
| Should Fix | More cross-user API isolation tests | Existing focused tests pass | Broaden before public scale |

## Online Recommendation

Do not proceed to public production launch.

The project is materially stronger than the initial P4 Blocked state because RealMarket Full E2E now passes and data-source failures degrade safely. But the conservative final state remains **Blocked** until Redis/RQ topology and human compliance sign-off are complete.

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

- Engineering review: Conditional Pass for controlled staging / beta evidence.
- Formal named human compliance/legal sign-off: Blocked / Pending.
- Public production compliance gate remains Blocked.

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
