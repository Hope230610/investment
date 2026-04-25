## Why

当前的复盘流程（`post-trade-review`）在用户提交后基本停留在“生成结果”这一步，无法把复盘结论沉淀回用户画像。缺少这条闭环会带来三个直接问题：

1. 行为标签只能靠系统单次推断，缺少用户确认，画像可信度不高。
2. 判断质量与情绪状态没有形成历史记录，结果页和画像页都无法展示趋势。
3. 用户感知不到系统“学到了什么”，复盘难以转化为长期可复用的方法论。

## What Changes

- 在 `post_trade_review` 结果页新增轻阻塞 `LearningFeedbackCard`，展示行为标签更新、判断质量、情绪趋势和建议文案。
- 新增 `emotion_history` / `judgment_history` 数据模型、`ProfileService` 写入逻辑，以及 `GET /api/v1/user/profile/learning-history` 和 `POST /api/v1/user/profile/learning-feedback`。
- `ResultPage` 优先读取真实 learning history，失败时降级到 synthetic emotion history；`ProfilePage` 新增 `LearningHistorySection`，复用同一套趋势展示。
- `inferTagUpdates` 支持 `action_taken` 字段作为 `intent` 的回退，解决 `post_trade_review` 场景标签推断失效问题。

## Capabilities

### Modified Capabilities

- `post-trade-review`: 复盘提交后不再只停留在结果页，而是进入”结果 → 反馈卡 → 确认/稍后/忽略”的闭环，并沉淀可聚合的判断质量记录。行为标签推断同时支持 `intent` 和 `action_taken` 字段回退。
- `user-profile`: 用户画像支持基于复盘确认写入行为标签，并提供 learning history 查询给结果页与画像页使用。

## Impact

- 关联 `structure` 基线文档：`investment_v1_prd.md`、`investment_json_schema_contract.md`、`database_design.md`、`investment_current_implementation_gap_audit.md`
- 后端影响范围：`investment-back/src/api/v1/user.py`、`investment-back/src/services/profile_service.py`、`investment-back/src/models/emotion_history.py`、`investment-back/src/models/judgment_history.py`、`investment-back/src/schemas/learning_feedback.py`、`investment-back/alembic/versions/008_add_learning_feedback_tables.py`
- 前端影响范围：`investment-front/src/components/LearningFeedbackCard.tsx`、`investment-front/src/utils/learningFeedback.ts`、`investment-front/src/utils/learningFeedback.test.ts`、`investment-front/src/pages/PostTradeInput.tsx`、`investment-front/src/pages/ResultPage.tsx`、`investment-front/src/pages/ProfilePage.tsx`、`investment-front/src/api.ts`
- 发布影响：仍需执行 `alembic upgrade head`，并手动验证 `post_trade_review → feedback card → ProfilePage` 的完整闭环；前端 `lint` / `test` / `build` 已通过，单元测试已全部完成（46 个用例）。
