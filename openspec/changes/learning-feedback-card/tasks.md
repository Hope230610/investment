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
| **7** | **三按钮交互（确认/稍后/忽略）+ localStorage 追踪** | ✅ done | commit `0b379f9` |
| **7b** | **判断质量分母确认（方案B: 含50分 + 3次下限兜底）** | ✅ done | 决策已记录，代码已实现 |
| **7c** | **"难以区分"处理：不 return null，展示中性卡面 + breakdown 100%** | ✅ done | 反馈卡正常展示行为标签和情绪数据 |

### Phase 2: 后端接入（已完成 ✅）

| # | Task | Status | Notes |
|---|------|--------|-------|
| 8 | 新建 `emotion_history` 表 | ✅ done | migration `008` |
| 9 | 实现 `/api/v1/user/profile/learning-history` GET | ✅ done | 返回 emotion_history + judgment_history |
| 10 | 实现 `/api/v1/user/profile/learning-feedback` POST | ✅ done | 写入行为标签 + 判断质量历史 |
| 11 | `buildEmotionHistory()` 替换为真实 API 调用 | ✅ done | 优先用 API，fallback 合成数据 |
| 12 | `handleFeedbackConfirm` 接入真实 POST | ✅ done | 替换 simulate delay |

### Phase 3: 用户可见化（已完成 ✅）

| # | Task | Status | Notes |
|---|------|--------|-------|
| 13 | `ProfilePage` 新增学习记录区块 | ✅ done | LearningHistorySection 组件 |
| 14 | 画像页展示当前 behavior_tags 及来源 | ⚠️ partial | 标签可编辑，来源由 POST 写入历史 |
| 15 | 全链路 E2E 测试 | pending | 见下方验证清单 |

## Verification

### 已验证清单

#### Phase 1 ✅
- [x] TypeScript: `tsc --noEmit` 零错误
- [x] Build: `vite build` 零错误，bundle ~495KB gzip 153KB
- [x] 三按钮渲染：确认（主）/ 稍后（次）/ 忽略（次）
- [x] 展示次数 badge 显示 (n/3)
- [x] backdrop 点击 = 触发「忽略」
- [x] localStorage mount 检查正确（dismissed / confirmed / count ≥ 3 均不展示）
- [x] onConfirm → 写入 localStorage + 关闭
- [x] onLater → 计数+1 + 关闭（下次可再出现，最多3次）
- [x] onDismiss → 永久跳过 + 关闭
- [x] "难以区分"不 return null，灰色中性卡面 + breakdown 100%
- [x] 数据 < 3 次时显示"数据积累中"，隐藏 delta / trend

#### Phase 2 ✅
- [x] `008_add_learning_feedback_tables.py` migration 语法正确
- [x] `EmotionHistory` + `JudgmentHistory` models 新建
- [x] `learning_feedback.py` schemas 新建
- [x] `ProfileService` upsert + behavior_tags 合并逻辑正确
- [x] `user.py` 两个新 endpoint：`GET /profile/learning-history` + `POST /profile/learning-feedback`
- [x] 前端 `getLearningHistory()` + `postLearningFeedback()` API 函数
- [x] `ResultPage` 接入真实 POST，历史数据传入 `computeLearningFeedback`
- [x] `buildEmotionHistory()` 优先用真实数据，API 失败 fallback 合成数据

#### Phase 3 ✅
- [x] `ProfilePage` 新增 `LearningHistorySection` 组件
- [x] `EmotionSparkline` 导出并被 ProfilePage 复用
- [x] ProfilePage 显示情绪 sparkline + 判断质量趋势条 + 逐条记录列表

### 待手动 E2E 验证（上线前）

- [ ] `alembic upgrade head` 执行成功，新表创建
- [ ] 登录 → post-trade-review → 提交复盘 → 反馈卡弹出 → 点击"确认"
- [ ] 再次进入 post-trade-review → 情绪 sparkline 显示真实历史数据
- [ ] ProfilePage → 学习记录区块显示判断质量趋势条 + 情绪 sparkline
- [ ] ProfilePage → behavior_tags 已更新（反映确认后的标签）
