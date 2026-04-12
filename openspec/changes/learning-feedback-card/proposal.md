## Why

当前的复盘流程（post-trade-review）提交后即结束，系统不会将复盘结论反馈到用户画像中，导致：
1. 用户的行为标签（追涨倾向、恐慌卖出等）仅由系统单次推断，没有用户确认机制
2. 判断质量数据（"主要来自判断" vs "主要来自运气"）仅做单次记录，没有历史聚合
3. 情绪记录（emotion_level）没有积累趋势，sparkline 无数据可画
4. 用户看不到自己的"学习曲线"，画像系统对用户不可感知

结果：画像系统是"看不见的"，用户感知不到系统在学习自己，失去了通过反馈建立自我认知的核心价值。

## What Changes

**前端（本次已实现）：**
- 新增 `LearningFeedbackCard` 组件：底部弹出式确认卡，展示行为标签更新、判断质量%、情绪 sparkline、建议文案
- 新增 `computeLearningFeedback` 计算引擎：将复盘表单数据映射为画像反馈数据
- `PostTradeInput` 提交后通过 `location.state` 传递 `reviewFormData` 到 `ResultPage`
- `ResultPage` 在 `post_trade_review` 场景下，分析结果加载 800ms 后弹出反馈卡
- 用户点击"确认"触发画像写入（后端 TODO）；点击"忽略"静默关闭

**后端（待接入）：**
- 新增 `/api/v1/profile/learning-feedback` POST 接口：接收标签更新 + 判断质量写回 UserProfile
- 新增 `/api/v1/profile/emotion-history` GET 接口：返回用户 30 天情绪记录用于 sparkline

## Goals / Non-Goals

**Goals:**
- 画像学习闭环的前端展示层：用户在复盘后看到系统的"学习结果"
- 主动确认机制：行为标签更新需要用户显式确认才写入 profile
- 判断质量可见化：百分比主指标 + 趋势 + 四分类构成
- 情绪历史积累与趋势展示

**Non-Goals:**
- 不在后端尚未实现的情况下强行伪造真实数据（synthetic demo 数据有明确 TODO 注释）
- 不改变后端数据库表结构（emotion_history 和 judgement_history 表暂不新建）
- 不改变现有 API 的外部接口语义
- 不在本次实现用户画像展示页（ProfilePage）

## Decisions

### 决策 1：反馈卡采用"轻阻塞"而非"全阻塞"形态

选择方案：bottom sheet 弹出，用户可点击"忽略"继续用 app，确认按钮异步完成写入。

理由：复盘结果本身对用户有价值（看到当初的预判），不应被标签确认流程打断。反馈卡是"奖励/认知"性质的，不是"警告/禁止操作"性质的，轻阻塞体验更流畅。

放弃的替代方案：全阻塞模态弹窗（必须点确认才能进入结果页）体验过重，会让用户感觉"被打断"，降低复盘意愿。

### 决策 2：行为标签推断规则在客户端计算

选择方案：标签推断逻辑（intent + trigger → 行为标签）在 `computeLearningFeedback.ts` 前端工具函数中实现。

理由：当前 `scenario_payload` 中的 `intent` 和 `trigger_reason` 字段已经可用，前端可以在后端接口接入前先跑通完整交互链路。后续后端接入时只需替换 API 端点，标签推断规则保持不变。

放弃的替代方案：后端计算推断标签，前端只展示。这样做的缺点是需要等后端改完才能验证前端交互，当前阶段前后端强耦合。

### 决策 3：情绪历史先用 synthetic data，保留明确 TODO

选择方案：`buildEmotionHistory()` 生成 30 天合成数据用于 UI 开发，后端接入后替换。

理由：情绪历史需要新增数据库表和 API 接口，改动范围大，不应阻塞 UI 开发。用合成数据可以在后端实现前完成全部前端开发和测试，后端接入时 UI 逻辑无需改变。

### 决策 4：判断质量展示为主指标百分比 + 辅助文字评价 + 构成柱状图

选择方案：
- 主指标：68% 数字（一眼看懂）
- 辅助评价：80%+/60-80%/<60% 三档文字（帮用户理解并知道下一步）
- 构成柱：四分类横向柱，从大到小排序（"运气占比"会自然显得短，心理冲击更强）

理由：用户更关心"我有没有变强"，单点数字不如趋势和构成有洞察力。四分类构成是差异化设计，让用户意识到"赚钱≠判断对，亏钱≠判断错"。

## Risks / Trade-offs

- **[后端断链]** 若后端接口迟迟不接入，反馈卡始终在 synthetic data 模式下运行 → 缓解：UI 逻辑完整，只换数据源
- **[行为标签推断误判]** 客户端推断规则可能不完整，部分场景无法正确推断标签 → 缓解：兜底为"本次复盘确认"来源，即使推断失败也有默认标签
- **[确认 vs 忽略语义不清]** 用户点"忽略"是否意味着拒绝更新标签？还是只是关闭弹窗？ → 待产品确认：目前设计"忽略"仅关闭弹窗，不写入 profile；确认才写入
- **[合成数据欺骗用户]** 用户可能误以为情绪 sparkline 是真实历史数据 → 缓解：synthetic data 有固定随机种子（Math.random），同一用户在同一天刷新结果一致；TODO 注释明确标注

## Open Questions

~~1. 行为标签更新是否需要用户确认？~~ → **已确认：强确认（Path A）**，反馈卡带确认按钮，确认后才写入 profile

~~2. 判断质量展示方式？~~ → **已确认：百分比主指标 + 文字评价 + 四分类构成柱**，趋势（近7天 vs 近30天）作为辅助

~~3. 反馈卡形态？~~ → **已确认：轻阻塞 bottom sheet**，不打断用户浏览结果页

~~4. "忽略"语义~~ → **已确认：路径 C — 三按钮方案**

用户有三种选择，语义明确：

| 按钮 | 行为 | localStorage 状态 |
|------|------|-----------------|
| 确认 | 写入 profile，关闭 | `feedback_dismissed_{id}` = `"confirmed"` |
| 稍后 | 不写入，关闭，下次复盘再出现（≤3次） | `feedback_showcount_{id}` += 1 |
| 忽略 | 不写入，关闭，永久跳过 | `feedback_dismissed_{id}` = `"true"` |

设计理由：覆盖用户真实心理（懒得点 / 不同意 / 好奇），不强迫决策。"稍后"给了动机 A 用户缓冲；"忽略"给了动机 B 用户明确的拒绝渠道；两者都不写入 profile，保证数据质量。

**注意**：点击 backdrop（sheet 外区域）= 触发"忽略"（永久跳过），因为这是移动端标准交互模式。

~~5. **判断质量百分比的分母**：只计入"主要来自判断"和"主要来自运气"两种选项，还是包含"部分判断+运气"折算？
   → 当前实现：100分/50分/0分（含50），待产品确认最终分母方案~~

**→ 已确认（方案 B：含50分 + 下限兜底）**

| 选项 | 分值 | 是否计入 |
|------|------|---------|
| 主要来自判断 | 100 | ✅ 计入 |
| 部分判断+运气 | 50 | ✅ 计入（折算为半次有效判断） |
| 主要来自运气 | 0 | ✅ 计入 |
| 难以区分 | -1 | ❌ 排除（不计入分母） |

**下限兜底**：累计数据 < 3 次时，判断质量百分比旁显示"数据积累中"，不展示 delta 和趋势，避免早期数据波动误导用户。

**理由**：排除"部分判断+运气"会使分母过小、百分比波动过大；含50分诚实反映"半判断、半运气"的现实认知，同时3次下限兜底防止早期数字不稳定。

6. **情绪 sparkline 的真实数据来源**：emotion_history 表是否需要在本次同步新建？还是作为独立后续 change？
   → 建议作为独立后续 change，不阻塞本次 UI

## Migration Plan

### 本次（已实现）

- [x] `LearningFeedbackCard.tsx`：组件实现，包含全部 UI 模块
- [x] `learningFeedback.ts`：`computeLearningFeedback` 工具函数 + synthetic emotion history
- [x] `PostTradeInput.tsx`：传递 `reviewFormData` 到 `ResultPage`
- [x] `ResultPage.tsx`：集成反馈卡触发逻辑
- [x] **三按钮交互**：`确认`（写入 profile）/ `稍后`（下次复盘再出现，最多3次）/ `忽略`（永久跳过）
- [x] **localStorage 追踪**：`feedback_dismissed_{id}` + `feedback_showcount_{id}`，页面挂载时读取，阻止已跳过/已确认的卡重复出现
- [x] **判断质量分母**：含50分 + 3次下限兜底（OQ2 已确认）
- [x] **"难以区分"处理**：不 return null，灰色中性卡面 + breakdown 100%，不计入历史聚合
- [x] **Phase 2 后端接入**：`emotion_history` + `judgment_history` 表、`ProfileService`、两个 API endpoint
- [x] **Phase 3 用户可见化**：`ProfilePage` 新增 `LearningHistorySection`（情绪 sparkline + 判断质量趋势）
- [ ] 单元测试：覆盖 `computeLearningFeedback` 所有分支

### Phase 2（后端接入）

- [ ] 新建 `emotion_history` 表（user_id, date, emotion_level, intent, trigger）
- [ ] 新增 `/api/v1/profile/emotion-history` GET 接口
- [ ] 新增 `/api/v1/profile/learning-feedback` POST 接口
- [ ] `ResultPage.handleFeedbackConfirm` 接入真实 API
- [ ] `buildEmotionHistory()` 替换为真实 API 调用

### Phase 3（用户可见化）

- [ ] `ProfilePage` 新增"学习记录"区块：展示行为标签历史、判断质量趋势图
- [ ] 画像页展示当前 behavior_tags 及来源说明
