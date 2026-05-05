# P4 Controlled Beta Plan

Date: 2026-05-05

## Goal

Validate the product in a real user environment without presenting it as production-grade investment advice.

## Scope

Recommended beta scope:

- 10 to 30 invited users
- 2 to 4 weeks
- Staging or controlled beta environment only
- No brokerage integration
- No auto trading
- No copy trading
- No direct buy / sell signal notifications
- Users must acknowledge that outputs are decision support, not investment advice

## Entry Criteria

Controlled beta may start only after:

- MockMarket full E2E passes.
- RealMarket Full E2E passes.
- Redis/RQ worker topology passes with real Redis and separate worker.
- A named human compliance/legal reviewer records sign-off in the compliance pack.
- The Redis-backed staging P4 checklist is rerun and recorded.
- Backend and frontend core tests pass.
- Deployment runbook and rollback path are reviewed.

Current status on 2026-05-05: RealMarket and MockMarket Full E2E are passing, but controlled beta remains blocked until Redis/RQ topology, named human compliance/legal sign-off, and the Redis-backed staging checklist are complete.

## User-facing Risk Controls

Beta users must see clear boundaries:

- The system does not provide investment advice.
- The system does not provide buy / sell instructions.
- Market data may be delayed, missing, or degraded.
- AI output is an aid to evidence review and risk control.
- Final decisions remain the user's responsibility.

## Metrics

Product loop metrics:

- daily open rate
- today focus click-through
- analysis task creation rate
- analysis completion rate
- pre-trade self-check completion rate
- post-trade review completion rate
- reminder click-through
- Learning Feedback generation rate

Safety / compliance metrics:

- user confusion rate: "I thought this was a stock recommendation"
- sanitizer / guard hit count
- low-confidence output count
- degraded data count
- failed analysis count
- share page visits and share creation count

Quality metrics:

- user-rated usefulness of evidence
- user-rated clarity of risk boundary
- cases where data timestamp was misunderstood
- pages where users got stuck
- recurring external data source failures

## Feedback Prompts

Ask users:

- Which evidence felt useful?
- Which risk warning changed your decision process?
- Which output sounded too much like a recommendation?
- Which page lacked context?
- Which reminder created a real daily-use reason?
- Did you understand the data timestamp and non-real-time boundary?

## Exit Criteria

Move from controlled beta toward production review only if:

- No user-visible stock-picking / call-order / return-promise language is found.
- RealMarket stability is acceptable or degraded states are clear and non-misleading.
- Redis/RQ topology remains stable under beta traffic.
- User isolation and share privacy remain clean.
- Users can explain the product boundary in their own words.

## Current Recommendation

Do not open public production. Prepare controlled beta only after remaining P4 blockers are closed.
