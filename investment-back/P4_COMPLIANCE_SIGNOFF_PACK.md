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
| Share card title / summary / disclaimer | Product + compliance reviewer approval on actual rendered copy | Conditional Pass |
| Disclaimer wording | Confirm visible on result and share paths | Conditional Pass |
| Sanitizer rules | Confirm high-risk phrases are blocked or rewritten in real outputs | Conditional Pass |
| AI eval samples | Add real provider samples before live LLM launch | Conditional Pass |
| Degraded data wording | Confirm low confidence and no strong conclusion when data is missing | Pass |
| User privacy in share | Confirm no private holding amount / trade history leakage | Pass based on current service tests and audit |

## Sign-off Result

Current compliance gate: **Conditional Pass for controlled staging / beta, Blocked for public production until human sign-off is recorded**.

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

- Engineering compliance review: **Conditional Pass for controlled staging / beta evidence**.
- Formal human compliance/legal sign-off: **Blocked / Pending**.
- Public production compliance gate: **Blocked** until a named human reviewer records a Pass or Conditional Pass below.

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
