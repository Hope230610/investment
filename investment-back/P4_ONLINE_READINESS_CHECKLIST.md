# P4 Online Readiness Checklist

Date: 2026-05-05

Run data-modifying and E2E commands only against dedicated test/staging databases.

| Area | Command | Purpose | Current Result | Blocks Production |
| --- | --- | --- | --- | --- |
| Git | `git status --short` | Confirm worktree scope | Modified P4 hardening files plus pre-existing handoff files; untracked P4 docs/scripts/tests | No, review before merge |
| Git | `git diff --name-status` | Confirm diff scope | Docs, readiness, market-data degradation, analysis create fast-path, E2E helper, P4 docs | No |
| Git | `git diff -- need.md` | Protect product baseline | No diff | Yes if modified |
| Backend compile | `cd F:\investment\investment-back; python -m compileall src tests scripts` | Syntax/import sanity | Passed | Yes if failing |
| Backend tests | `cd F:\investment\investment-back; pytest -q` | Backend regression baseline | 117 passed, 131 warnings | Yes if failing |
| Readiness / market degradation | `cd F:\investment\investment-back; pytest tests/test_mock_market_data_service.py tests/test_health_readiness.py -q` | Verify mock market, real-source degradation, DB/Redis readiness behavior | 7 passed | Yes if failing |
| Migration current | `cd F:\investment\investment-back; alembic current` | Verify migration head | `013 (head)` | Yes if not head |
| Migration upgrade | `cd F:\investment\investment-back; alembic upgrade head` | Verify migration can reach head | Passed/no-op | Yes if failing |
| Frontend typecheck | `cd F:\investment\investment-front; npm run lint` | TypeScript no-emit check | Passed | Yes if failing |
| Frontend unit | `cd F:\investment\investment-front; npm run test -- --run` | Frontend regression baseline | 52 passed | Yes if failing |
| Frontend build | `cd F:\investment\investment-front; npm run build` | Production bundle sanity | Passed; existing 543.83 kB chunk warning | Warning only |
| E2E list | `cd F:\investment\investment-front; npm run test:e2e -- --list` | Confirm Playwright suite discoverability | 22 tests listed | Yes if failing |
| Mock full E2E | `cd F:\investment\investment-front; powershell -ExecutionPolicy Bypass -File .\scripts\run-e2e-acceptance.ps1 -PrepareDb -MockMarket -Full` | Deterministic release baseline | 22 passed in about 2.3 minutes | Yes if failing |
| Real full E2E | `cd F:\investment\investment-front; powershell -ExecutionPolicy Bypass -File .\scripts\run-e2e-acceptance.ps1 -PrepareDb -Full` | Validate real market-data dependency and full user loop | 22 passed in about 6.4 minutes | Yes if failing |
| RQ package preflight | `cd F:\investment\investment-back; .\.venv\Scripts\pip.exe install redis==5.0.8 rq==1.16.1` | Match declared worker dependencies | Installed declared versions locally | Yes if missing in deploy env |
| Redis ping | `cd F:\investment\investment-back; .\.venv\Scripts\python.exe -c "from redis import Redis; r=Redis.from_url('redis://localhost:6379/0'); print(r.ping())"` | Verify Redis availability | Failed: connection refused on localhost:6379 | Yes |
| RQ topology | `cd F:\investment\investment-back; powershell -ExecutionPolicy Bypass -File .\scripts\run_rq_topology_acceptance.ps1` plus separate `python -m src.workers` | Validate production async topology | Not completed because Redis server unavailable and Docker unavailable | Yes |
| Quality grep CN | `rg -n "赶紧买|直接买|必须买|必须卖|立即卖|必涨|稳赚|保本|无风险|目标价|翻倍|满仓|梭哈|跟着买|强烈推荐|抄底|逃顶|闭眼买|稳赚不赔|买入信号|卖出信号" investment-back/src investment-front/src investment-back/tests investment-front/tests` | Check high-risk visible phrasing | Hits in tests, guard/sanitizer lists, and explicit non-advice copy | Yes if unsafe user-visible advice appears |
| Quality grep EN | `rg -n "buy now|sell now|strong buy|strong sell|guaranteed|risk-free|target return|follow me to buy|auto trade" investment-back/src investment-front/src investment-back/tests investment-front/tests` | Check English unsafe phrase coverage | Hits limited to guard/sanitizer/tests | Yes if unsafe user-visible advice appears |
| Whitespace | `git diff --check` | Check whitespace errors | No whitespace errors; LF/CRLF warnings only | Yes if errors |

## Current Gate Result

**Production Online Ready: No. Current status: Blocked.**

Closed this round:

1. RealMarket Full E2E is now passing.
2. MockMarket Full E2E remains passing.
3. Market-data failure now degrades instead of breaking analysis creation.
4. P4 compliance pack, deployment runbook, beta plan, and RQ topology preflight script were added.

Must Fix before production:

1. Run and pass real Redis/RQ worker topology with `RQ_ASYNC=false`, real Redis, separate worker, API, frontend, and task completion.
2. Record formal human compliance sign-off in `P4_COMPLIANCE_SIGNOFF_PACK.md`.

Permitted next step: staging hardening and Redis-backed topology validation, not public production launch.

## P4 Final Blocker Closure Rerun - 2026-05-05

Run environment:

- OS: Microsoft Windows NT 10.0.26200.0.
- Local PostgreSQL: `postgresql://postgres:123456@localhost:5432/investment_db`; E2E scripts prepared `investment_e2e`.
- Redis: no reachable Redis on `localhost:6379`; `Test-NetConnection localhost:6379` returned `TcpTestSucceeded=False`.
- Docker: not available in PATH.
- WSL: Ubuntu exists, but Redis was not available; attempted WSL apt Redis install did not complete and no Redis service became available.
- RQ topology env attempted by script: `RQ_ASYNC=false`, `REDIS_URL=redis://localhost:6379/0`.
- Worker command required for acceptance: `cd F:\investment\investment-back; $env:RQ_ASYNC='false'; $env:REDIS_URL='redis://localhost:6379/0'; python -m src.workers`.
- Frontend/backend E2E startup: existing Playwright webServer flow through `investment-front/scripts/run-e2e-acceptance.ps1`.

| Area | Command | 2026-05-05 Rerun Result | Blocks Production |
| --- | --- | --- | --- |
| Git | `git status --short` | Existing modified RealMarket/P4 hardening files plus untracked P4 docs/scripts/tests; no commit made | No, review before merge |
| Git | `git diff --name-status` | Existing P4 hardening scope; no `need.md` changes | No |
| Git | `git diff -- need.md` | No diff | Yes if modified |
| Backend compile | `cd F:\investment\investment-back; python -m compileall src tests scripts` | Passed | Yes if failing |
| Backend tests | `cd F:\investment\investment-back; pytest -q` | 117 passed, 131 warnings | Yes if failing |
| Readiness / market degradation | `cd F:\investment\investment-back; pytest tests/test_mock_market_data_service.py tests/test_health_readiness.py -q` | 7 passed, 21 warnings | Yes if failing |
| Migration current | `cd F:\investment\investment-back; alembic current` | `013 (head)` | Yes if not head |
| Migration upgrade | `cd F:\investment\investment-back; alembic upgrade head` | Passed/no-op | Yes if failing |
| Frontend lint | `cd F:\investment\investment-front; npm run lint` | Passed | Yes if failing |
| Frontend unit | `cd F:\investment\investment-front; npm run test -- --run` | 52 passed | Yes if failing |
| Frontend build | `cd F:\investment\investment-front; npm run build` | Passed; main chunk warning remains 543.83 kB | Warning only |
| Mock full E2E | `cd F:\investment\investment-front; powershell -ExecutionPolicy Bypass -File .\scripts\run-e2e-acceptance.ps1 -PrepareDb -MockMarket -Full` | 22 passed in about 2.4 minutes | Yes if failing |
| Real full E2E | `cd F:\investment\investment-front; powershell -ExecutionPolicy Bypass -File .\scripts\run-e2e-acceptance.ps1 -PrepareDb -Full` | 22 passed in about 7.5 minutes | Yes if failing |
| RQ topology acceptance | `cd F:\investment; powershell -NoProfile -ExecutionPolicy Bypass -File .\investment-back\scripts\run_rq_topology_acceptance.ps1 -SkipFrontendCheck` | Failed at Redis ping: `Error 10061 connecting to localhost:6379`; script now uses backend `.venv` and hard-fails before any false pass | Yes |
| Redis reachability | `Test-NetConnection -ComputerName localhost -Port 6379` | `TcpTestSucceeded=False` | Yes |
| Quality grep CN | `rg -n "赶紧买|直接买|必须买|必须卖|立即卖|必涨|稳赚|保本|无风险|目标价|翻倍|满仓|梭哈|跟着买|强烈推荐|抄底|逃顶|闭眼买|稳赚不赔|买入信号|卖出信号" investment-back/src investment-front/src investment-back/tests investment-front/tests` | Hits limited to tests, sanitizer/guard lists, replacement maps, and explicit non-advice copy | Yes if unsafe user-visible advice appears |
| Quality grep EN | `rg -n "buy now|sell now|strong buy|strong sell|guaranteed|risk-free|target return|follow me to buy|auto trade" investment-back/src investment-front/src investment-back/tests investment-front/tests` | Hits limited to tests and sanitizer/guard lists/replacement maps | Yes if unsafe user-visible advice appears |
| Whitespace | `git diff --check` | No whitespace errors; LF/CRLF warnings only | Yes if errors |

Script hardening completed:

- `scripts/run_rq_topology_acceptance.ps1` no longer stops at Redis ping and `/ready`.
- It now validates Redis, `/health`, `/ready` rq+redis mode, frontend reachability, auth, quick `POST /analysis`, RQ job presence for the analysis task, and worker-driven terminal status.
- It fails if Redis is unreachable, if task creation blocks too long, if no RQ job is found, if the worker leaves the task non-terminal, or if a failed terminal state is returned.

Updated gate result:

**Production Online Ready: No. Current status: Blocked.**

Remaining production blockers:

1. Real Redis + independent `python -m src.workers` + FastAPI + frontend + `RQ_ASYNC=false` topology has not passed because Redis is unavailable locally.
2. Formal human compliance/legal sign-off remains pending.
3. Staging checklist is partially rerun locally, but not in a real Redis-backed staging topology.
