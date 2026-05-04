## 1. Contract

- [x] 1.1 为 `post-trade-review` 与 `user-profile` 补充画像学习闭环相关 delta spec，覆盖反馈卡展示、行为标签确认写入和 learning history 查询
- [x] 1.2 同步 proposal / design 到当前实现状态，移除“后端待接入”与已完成 Phase 2/3 之间的矛盾描述

## 2. Backend/Data

- [x] 2.1 新建 `emotion_history` 与 `judgment_history` 表，并提交 `008_add_learning_feedback_tables.py`
- [x] 2.2 在 `ProfileService` 中实现情绪历史、判断质量历史与行为标签写入逻辑
- [x] 2.3 新增 `GET /api/v1/user/profile/learning-history` 与 `POST /api/v1/user/profile/learning-feedback`

## 3. Frontend

- [x] 3.1 实现 `LearningFeedbackCard.tsx` 与 `computeLearningFeedback`
- [x] 3.2 打通 `PostTradeInput -> ResultPage` 的反馈卡触发、三按钮交互和 localStorage gating
- [x] 3.3 在 `ResultPage` 中优先使用真实 learning history，失败时降级到 synthetic emotion history
- [x] 3.4 在 `ProfilePage` 中新增 `LearningHistorySection` 并复用 `EmotionSparkline`
- [x] 3.5 为 `computeLearningFeedback` 的关键分支补充单元测试（含 `action_taken` 回退场景）

## 4. QA/Release

- [x] 4.1 完成 TypeScript 编译与前端构建验证，确认反馈卡主链路无类型错误
- [x] 4.2 完成 migration `008`、模型、schema 与 profile API 的实现级校对
- [x] 4.3 在目标环境执行 `alembic upgrade head`，确认学习历史表创建成功
- [x] 4.4 完成手动 E2E：登录 → post-trade-review → 确认反馈 → ProfilePage 查看 learning history
