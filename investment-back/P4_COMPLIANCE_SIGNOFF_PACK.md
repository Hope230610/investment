# P4 Compliance Sign-off Evidence Pack

Date: 2026-05-05

## Scope

Reviewed user-visible and AI-generated surfaces for the P4 readiness gate:

- Home / today focus
- Single-stock analysis result
- Pre-trade self-check
- Post-trade review
- Portfolio and holdings context
- Reminder center
- Learning feedback
- Public share card
- Failure / degraded analysis fallback
- AI eval and sanitizer / guard code paths

## Product Boundary

This product remains an investment decision coach / copilot. It must not become:

- stock picking
- call-order / signal pushing
- return promise
- auto trading
- copy trading

Allowed output style:

- observe
- review
- verify evidence
- control risk
- lower confidence when data is missing
- explain invalidation conditions

Disallowed user-visible output style:

- direct buy / sell instruction
- guaranteed return
- risk-free wording
- target-price promise
- full-position / follow-me wording

## Evidence Samples

Representative compliant output patterns observed in code and tests:

- Result cards include supporting evidence, counter evidence, risks, invalidation conditions, timestamp, and confidence level.
- Pre-trade flow asks users to pause and self-check emotion, position boundary, and evidence sufficiency before action.
- Post-trade flow focuses on review quality and repeatable process, not whether a trade should be copied.
- Failed / pending result cards explicitly say not to make investment judgments from placeholder content.
- Share service sanitizes title, summary, list fields, and sensitive holding fields.

## High-risk Phrase Review

Required high-risk Chinese phrase set:

`赶紧买`, `直接买`, `必须买`, `必须卖`, `立即卖`, `必涨`, `稳赚`, `保本`, `无风险`, `目标价`, `翻倍`, `满仓`, `梭哈`, `跟着买`, `强烈推荐`, `抄底`, `逃顶`, `闭眼买`, `稳赚不赔`, `买入信号`, `卖出信号`

Current evidence status:

- Existing audit grep found hits only in allowed contexts: tests, guard/sanitizer lists, behavior labels, transaction history labels, self-check prompts, and explicit non-advice copy.
- No newly introduced user-visible high-risk phrase was added in this round.
- Real model output coverage remains limited because the current provider path is deterministic rules-engine, not a live LLM provider.

Suggested verification command before sign-off:

```powershell
cd F:\investment
rg -n "赶紧买|直接买|必须买|必须卖|立即卖|必涨|稳赚|保本|无风险|目标价|翻倍|满仓|梭哈|跟着买|强烈推荐|抄底|逃顶|闭眼买|稳赚不赔|买入信号|卖出信号" investment-back/src investment-front/src investment-back/tests investment-front/tests
rg -n "buy now|sell now|strong buy|strong sell|guaranteed|risk-free|target return|follow me to buy|auto trade" investment-back/src investment-front/src investment-back/tests investment-front/tests
```

## Manual Review Checklist

| Area | Evidence needed | Status |
| --- | --- | --- |
| Share card title / summary / disclaimer | Product + compliance reviewer approval on actual rendered copy | Engineering evidence recorded; pending human review |
| Disclaimer wording | Confirm visible on result and share paths | Engineering evidence recorded; pending human review |
| Sanitizer rules | Confirm high-risk phrases are blocked or rewritten in real outputs | Engineering evidence recorded; pending human review |
| AI eval samples | Add real provider samples before live LLM launch | Engineering evidence recorded; pending human review |
| Degraded data wording | Confirm low confidence and no strong conclusion when data is missing | Pass |
| User privacy in share | Confirm no private holding amount / trade history leakage | Pass based on current service tests and audit |

## Sign-off Result

Current compliance gate: **Blocked**. Engineering evidence has been recorded, but controlled beta and public production remain blocked until named human compliance/legal sign-off is recorded.

Required human sign-off fields:

- Reviewer:
- Date:
- Scope reviewed:
- Result: Pass / Conditional Pass / Blocked
- Notes:

## P4 Final Blocker Closure Review - 2026-05-05

Reviewer: Codex engineering compliance review, not a licensed legal/compliance officer.

Date: 2026-05-05

Scope reviewed:

- Public share card service and public share serializer.
- Single-stock analysis result structure: supporting evidence, counter evidence, primary risks, invalidation conditions, timestamp, and confidence.
- Pre-trade self-check and post-trade review user-visible flows.
- Sanitizer / guard word lists and tests.
- AI eval deterministic sample coverage.
- Chinese and English high-risk phrase grep across `investment-back/src`, `investment-front/src`, `investment-back/tests`, and `investment-front/tests`.

Evidence checked:

- Share cards use `SHARE_DISCLAIMER`: "本卡片仅用于展示风险教育和决策过程，不构成投资建议、收益承诺或买卖指令。"
- Share service sanitizes title, summary, support, counter, risks, and invalidation fields and strips sensitive holding fields such as quantity, cost price, average cost, profit/loss, and PnL.
- Public share serializer does not expose user id or source id based on existing tests.
- Result page displays non-advice boundary copy: "以下内容用于辅助判断，不构成直接投资建议".
- Single-stock result E2E verifies evidence, counter evidence, invalidation conditions, and confidence.
- Pre-trade and post-trade flows are framed as self-check/review, not direct trade instruction.
- Sanitizer / guard tests cover Chinese and English direct-recommendation and guaranteed-return examples.

High-risk phrase grep result:

- Chinese high-risk hits are limited to test fixtures, sanitizer / guard lists, and explicit non-advice boundary copy.
- English high-risk hits are limited to test fixtures, sanitizer / guard lists, and sanitizer replacement maps.
- No user-visible path was found that presents stock-picking, call-order language, guaranteed return, risk-free return, full-position pressure, copy trading, or auto-trading.

Formal sign-off result:

- Engineering compliance review: evidence recorded only; not formal legal/compliance sign-off.
- Formal human compliance/legal sign-off: **Blocked / Pending**.
- Public production compliance gate: **Blocked** until a named human reviewer records explicit production allowance.

Human reviewer fields still required:

- Reviewer:
- Date:
- Scope reviewed:
- Result: Pass / Conditional Pass / Blocked
- Notes:

Residual risks:

- Current AI provider path is deterministic rules-engine. A live LLM/provider launch still needs real provider output sampling before public production.
- Share-page wording should be manually reviewed in the deployed UI, not only in code.
- Users may still misinterpret decision-support language as recommendations; controlled beta should explicitly measure this.

## Human Compliance / Legal Sign-off Record - Pending

Reviewer name: Pending; no named human compliance/legal reviewer was provided in this environment.

Role: Pending.

Date: Pending.

Scope required:

- Public share card title, summary, disclaimer, and rendered UI.
- Result-page disclaimer and degraded-data wording.
- Sanitizer and guard behavior for high-risk Chinese and English phrases.
- AI eval sample coverage, including real provider samples before any live LLM launch.
- User-visible flows for home/today focus, single-stock analysis, pre-trade self-check, post-trade review, portfolio context, reminders, learning feedback, and public share pages.

Reviewed materials: Pending human review. Engineering evidence currently includes this sign-off pack, `P4_ONLINE_READINESS_AUDIT.md`, `P4_ONLINE_READINESS_CHECKLIST.md`, sanitizer / guard tests, AI eval tests, share service tests, and high-risk phrase grep evidence.

Conclusion: **Blocked / Pending**.

Notes:

- This record intentionally does not convert the engineering conditional review into a formal legal/compliance Pass.
- No human reviewer signature or approval was available during the Redis-backed staging acceptance attempt.
- Public production remains blocked until this section is completed by a named human reviewer.

Remaining risk:

- Users may interpret share-card or result language as investment recommendations without human wording review.
- Current deterministic AI eval evidence does not substitute for live provider output review.
- Sanitizer rules should be confirmed against deployed UI behavior and representative generated samples.

## AI-assisted engineering compliance review record - 2026-05-05

Reviewer name: Codex AI-assisted review, not a named human legal/compliance reviewer.

Reviewer role: AI-assisted engineering compliance reviewer; not licensed legal/compliance sign-off.

Review date: 2026-05-05.

Review scope:

- P4 compliance pack.
- Online readiness audit/checklist.
- Controlled beta plan.
- Share card/result/pre-trade/post-trade/reminder/user-visible boundary copy.
- Sanitizer/guard/AI eval samples.
- High-risk phrase grep evidence.

Reviewed materials:

- `P4_COMPLIANCE_SIGNOFF_PACK.md`.
- `P4_ONLINE_READINESS_AUDIT.md`.
- `P4_ONLINE_READINESS_CHECKLIST.md`.
- `P4_CONTROLLED_BETA_PLAN.md`.
- `share_service`, `ai_eval_service`, `output_quality_service`.
- Frontend Home/Me/Portfolio visible disclaimer copy.
- Related sanitizer/share/AI eval/output quality tests.

Conclusion: **Blocked**.

Production launch allowed: **No**.

Controlled beta allowed: **No**.

Notes:

- Current materials show strong engineering compliance evidence: user-visible high-risk phrases appear limited to explicit non-advice copy, tests, sanitizer/guard lists, and replacement maps.
- Share card disclaimer states it is not investment advice, return promise, or buy/sell instruction.
- Result structure requires evidence, counter-evidence, risks, invalidation conditions, timestamp, and confidence.
- Degraded/low-confidence paths avoid strong conclusions.
- This AI-assisted review does not constitute named human legal/compliance sign-off.
- Treating this response as formal human sign-off would violate the project audit rule.
- Therefore P4 must remain **Blocked** until a real named human reviewer records role, date, scope, conclusion, notes, remaining risk, and explicit production/beta allowance.

Remaining risks:

- Share cards may still be interpreted by users as recommendation propagation without real human wording review.
- Live LLM/provider outputs have not been reviewed with real provider samples.
- Sanitizer behavior should be verified against deployed UI and representative generated outputs.
- Some visible copy should be checked in the actual rendered app, not only source/test evidence.

Must fix before launch:

- Obtain named human compliance/legal sign-off.
- Record reviewer name, role, review date, reviewed scope/materials, conclusion, notes, and remaining risks.
- Explicitly state whether controlled beta is allowed.
- Explicitly state whether public production launch is allowed.
- Keep all non-advice, no-return-promise, and no-buy/sell-instruction disclaimers in user-visible flows.

Formal human sign-off status: **Pending / Blocked**.

## Redis-backed Staging Rerun Compliance Status - 2026-05-05

Reviewer name: Pending; no named human compliance/legal reviewer was provided.

Role: Pending.

Date: Pending.

Scope required for formal review:

- Public share card title, summary, disclaimer, and rendered UI.
- Result-page disclaimer, degraded-data wording, confidence, evidence, counter-evidence, and invalidation conditions.
- Sanitizer and guard behavior for high-risk Chinese and English phrases.
- AI eval deterministic samples and real provider samples before any live LLM launch.
- Home/today focus, single-stock analysis, pre-trade self-check, post-trade review, portfolio context, reminders, learning feedback, and public share pages.

Reviewed materials available:

- `P4_ONLINE_READINESS_AUDIT.md`.
- `P4_ONLINE_READINESS_CHECKLIST.md`.
- Share service tests, AI eval tests, output quality tests, and high-risk phrase grep evidence.
- Redis/RQ topology acceptance evidence and MockMarket/RealMarket Full E2E evidence from the Redis-backed rerun.

Conclusion: **Blocked / Pending** for public production.

Notes:

- Redis/RQ topology and the full technical checklist now have passing evidence.
- This does not complete legal/compliance sign-off.
- Engineering evidence remains engineering review material only and does not allow controlled beta or public production.

Remaining risk:

- Formal human reviewer has not accepted the exact public share-card and disclaimer wording.
- Users may still interpret decision-support language as recommendations without human review.
- Real provider output review remains required before public live LLM use.

## P4 Compliance Sign-off Closure Decision - 2026-05-05

Reviewer name: Pending; no named human compliance/legal reviewer was provided.

Reviewer role: Pending.

Review date: Pending.

Review scope required:

- Share card rendered title, summary, disclaimer, privacy behavior, and absence of buy/sell signal wording.
- Single-stock result evidence, counter-evidence, risks, invalidation conditions, timestamp, confidence, and non-advice boundary.
- Pre-trade self-check and post-trade review wording.
- Portfolio, holdings, reminder, learning feedback, home/today focus, failure fallback, and public share flows.
- Sanitizer / guard behavior for high-risk Chinese and English phrases.
- AI eval samples, including real provider samples before any live LLM production use.

Reviewed materials available for the human reviewer:

- `P4_COMPLIANCE_SIGNOFF_PACK.md`.
- `P4_ONLINE_READINESS_AUDIT.md`.
- `P4_ONLINE_READINESS_CHECKLIST.md`.
- Share service, sanitizer / guard, output quality, and AI eval tests.
- High-risk phrase grep evidence across backend/frontend source and tests.
- Redis/RQ, MockMarket, RealMarket, backend, frontend, and Alembic technical acceptance evidence.

Conclusion: **Blocked / Pending**.

Formal compliance/legal sign-off conclusion: **Not completed**.

Public production launch allowed: **No**.

Controlled beta allowed: **No**, unless a named human compliance/legal reviewer explicitly records Pass or Conditional Pass with beta allowance.

Notes:

- Engineering evidence remains engineering evidence only.
- This section intentionally does not create, infer, or substitute a legal/compliance approval.
- The P4 final gate must remain Blocked while reviewer name, role, date, scope, conclusion, and notes are missing.
