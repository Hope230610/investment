## Tasks

### Phase 1: 前端实现（已完成 ✅）

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | 设计反馈卡 UI 规范（判断质量% + 趋势 + 构成 + 情绪 sparkline） | ✅ done | 参与决策 |
| 2 | 实现 `LearningFeedbackCard.tsx` 组件 | ✅ done | commit `6ee2677` |
| 3 | 实现 `computeLearningFeedback.ts` 计算引擎 | ✅ done | commit `6ee2677` |
| 4 | `PostTradeInput` 传递 `reviewFormData` 到 `ResultPage` | ✅ done | commit `6ee2677` |
| 5 | `ResultPage` 集成反馈卡触发逻辑 | ✅ done | commit `6ee2677` |
| 6 | TypeScript lint + Vite build 验证 | ✅ done | 零错误零警告 |

### Phase 2: 后端接入

| # | Task | Status | Notes |
|---|------|--------|-------|
| 7 | 新建 `emotion_history` 表 | pending | user_id, date, emotion_level, intent, trigger |
| 8 | 实现 `/api/v1/profile/emotion-history` GET | pending | 返回 EmotionDataPoint[] |
| 9 | 实现 `/api/v1/profile/learning-feedback` POST | pending | 写入行为标签 + 判断质量历史 |
| 10 | `buildEmotionHistory()` 替换为真实 API 调用 | pending | 移除 synthetic data |
| 11 | `handleFeedbackConfirm` 接入真实 POST | pending | 替换 simulate delay |

### Phase 3: 用户可见化

| # | Task | Status | Notes |
|---|------|--------|-------|
| 12 | `ProfilePage` 新增学习记录区块 | pending | 行为标签历史 + 判断质量趋势 |
| 13 | 画像页展示当前 behavior_tags 及来源 | pending | 说明每个标签的推断来源 |
| 14 | 全链路 E2E 测试 | pending | post-trade-review → 反馈卡 → 确认 → profile |

## Verification

### 已验证清单

- [x] TypeScript: `tsc --noEmit` 零错误
- [x] Build: `vite build` 零错误，bundle 491KB gzip 152KB
- [x] 提交范围：仅 4 个文件，793 行，无污染其他改动
- [x] Commit: `6ee2677 feat(front): add learning feedback card for post-trade review`
- [x] 触发条件正确：仅 `post_trade_review` + 有 `reviewFormData`
- [x] Bottom sheet 动画与现有 `showExplain` 模式一致
- [x] SVG sparkline 无第三方依赖
- [x] 判断质量三档阈值（80/60）正确
- [x] "忽略"按钮存在且可关闭弹窗
