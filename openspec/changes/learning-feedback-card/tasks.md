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
| **7** | **三按钮交互（确认/稍后/忽略）+ localStorage 追踪** | ✅ done | **本次 commit** |

### Phase 2: 后端接入

| # | Task | Status | Notes |
|---|------|--------|-------|
| 8 | 新建 `emotion_history` 表 | pending | user_id, date, emotion_level, intent, trigger |
| 9 | 实现 `/api/v1/profile/emotion-history` GET | pending | 返回 EmotionDataPoint[] |
| 10 | 实现 `/api/v1/profile/learning-feedback` POST | pending | 写入行为标签 + 判断质量历史 |
| 11 | `buildEmotionHistory()` 替换为真实 API 调用 | pending | 移除 synthetic data |
| 12 | `handleFeedbackConfirm` 接入真实 POST | pending | 替换 simulate delay |

### Phase 3: 用户可见化

| # | Task | Status | Notes |
|---|------|--------|-------|
| 13 | `ProfilePage` 新增学习记录区块 | pending | 行为标签历史 + 判断质量趋势 |
| 14 | 画像页展示当前 behavior_tags 及来源 | pending | 说明每个标签的推断来源 |
| 15 | 全链路 E2E 测试 | pending | post-trade-review → 反馈卡 → 确认 → profile |

## Verification

### 已验证清单

- [x] TypeScript: `tsc --noEmit` 零错误
- [x] Build: `vite build` 零错误，bundle 493KB gzip 152KB
- [x] 提交范围：仅 4 个文件，793 行，无污染其他改动
- [x] Commit: `6ee2677 feat(front): add learning feedback card for post-trade review`
- [x] 触发条件正确：仅 `post_trade_review` + 有 `reviewFormData`
- [x] Bottom sheet 动画与现有 `showExplain` 模式一致
- [x] SVG sparkline 无第三方依赖
- [x] 判断质量三档阈值（80/60）正确
- [x] 三按钮渲染：确认（主）/ 稍后（次）/ 忽略（次）
- [x] 展示次数 badge 显示 (n/3)
- [x] hint 文案说明三按钮语义
- [x] backdrop 点击 = 触发「忽略」
- [x] localStorage mount 检查正确（dismissed / confirmed / count ≥ 3 均不展示）
- [x] onConfirm → 写入 localStorage + 关闭
- [x] onLater → 计数+1 + 关闭（下次可再出现，最多3次）
- [x] onDismiss → 永久跳过 + 关闭
