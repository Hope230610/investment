## What Capabilities Change

### Modified Capabilities

- `post-trade-review`: 复盘提交后新增反馈卡交互，用户在收到分析结果后 800ms 自动弹出。流程从"提交 → 结果页"扩展为"提交 → 结果页 → 反馈卡（三按钮）→ 确认/稍后/忽略"。
- `user-profile`: 画像写入从一次性静态字段扩展为“行为标签确认写入 + learning history 查询”，供 `ResultPage` 与 `ProfilePage` 共用。

## Capabilities

### Learning Feedback Card

```
┌─────────────────────────────────────────────────────┐
│  LearningFeedbackCard · Bottom Sheet (轻阻塞)       │
│  trigger: post_trade_review result loaded + 800ms │
│  backdrop click → 触发「忽略」（永久跳过）           │
├─────────────────────────────────────────────────────┤
│                                                     │
│  📖 本次复盘 · 系统学到了这些 [第2次展示]        │
│                                                     │
│  🏷️ 行为标签更新                                   │
│  ┌───────────────────────────────────────────┐    │
│  │  + 新增「追涨倾向」                         │    │
│  │  来源：连续上涨触发 + 本次复盘确认           │    │
│  └───────────────────────────────────────────┘    │
│                                                     │
│  📊 判断质量                                       │
│  ┌───────────────────────────────────────────┐    │
│  │  68%（+5%）    ● 绿   [近7天持续提升 ↑]  │    │
│  │  ──────────────────────────────────────   │    │
│  │  判断基本可靠，存在一定情绪干扰              │    │
│  │                                             │    │
│  │  构成分析：                                  │    │
│  │  主要来自判断    45% ████████████          │    │
│  │  部分判断+运气   30% ██████████              │    │
│  │  主要来自运气    20% ██████                 │    │
│  │  难以区分         5% ██                     │    │
│  └───────────────────────────────────────────┘    │
│                                                     │
│  📈 情绪趋势（最近30天）                            │
│  ┌───────────────────────────────────────────┐    │
│  │  [SVG sparkline]                          │    │
│  │  均值 2.4  |  本次 3  |  ↑略高于均值      │    │
│  └───────────────────────────────────────────┘    │
│                                                     │
│  💡 建议：减少连续上涨场景下的追涨冲动               │
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │  [X忽略]  [⏱稍后 (2/3)]  [✓确认]         │  │
│  └─────────────────────────────────────────────┘  │
│  忽略=跳过不更新 | 稍后=下次复盘再提醒 | 确认=写入  │
└─────────────────────────────────────────────────────┘
```

### Trigger + State Logic

```
PostTradeInput.handleSubmit
  → navigate(..., { state: { reviewFormData } })
    → ResultPage (on mount)
      ├── 读 localStorage:
      │   feedback_dismissed_{id} = "true"?     → 不展示（永久跳过）
      │   feedback_dismissed_{id} = "confirmed"? → 不展示（已确认）
      │   feedback_showcount_{id} ≥ 3?          → 不展示（已达上限）
      │   → 通过全部检查 → computeLearningFeedback()
      │       → 800ms delay → LearningFeedbackCard.visible = true
      │
      └── 用户操作：
          ├── onConfirm  → 写入profile → localStorage[dismissed]="confirmed" → 关闭
          ├── onLater   → 不写入 → localStorage[count]++ → 关闭（下次复盘可再出现）
          └── onDismiss  → 不写入 → localStorage[dismissed]="true" → 关闭（永久跳过）
              backdrop点击 → 同 onDismiss（移动端标准交互）
```

### Judgment Quality Computation

```
输入: judgementQuality (表单选择)
  "主要来自判断"       → 100 分
  "部分判断+部分运气" → 50 分
  "主要来自运气"      → 0 分
  "难以区分"          → 排除（不计入）

聚合: 百分比 = Σ分数 / 计入次数 × 100%

下限兜底: 累计数据 < 3 次 → 显示"数据积累中"，不展示 delta / 趋势

"难以区分"处理:
  - 本次复盘不计入历史聚合（不污染百分比）
  - 反馈卡正常展示（行为标签、情绪趋势仍有效）
  - 判断质量区改为灰色中性样式，显示说明文字 + breakdown 100% "难以区分" 柱
  - `isHardToTell: true` 标记本次为"难以区分"
Delta: 与历史平均值差值
Level: ≥80% 绿 | 60-80% 黄 | <60% 红

构成分析（固定比例，用于UI展示）:
  主要来自判断 45% | 部分判断+运气 30% | 主要来自运气 20% | 难以区分 5%
```

### Behavior Tag Inference

```
规则引擎（前端计算）:

  intent 字段（优先）:
    intent = 'buy'/'add_position' AND trigger = '连续上涨'/'看到大涨'
      → 新增「追涨倾向」

    intent = 'sell'/'reduce_position' AND trigger = '快速下跌'/'恐慌性抛盘'
      → 新增「恐慌卖出」

  action_taken 字段（回退，intent 为空时使用）:
    action_taken = 'buy'/'add' AND trigger = '连续上涨'/'看到大涨'
      → 新增「追涨倾向」

    action_taken = 'sell'/'reduce' AND trigger = '快速下跌'/'恐慌性抛盘'
      → 新增「恐慌卖出」

  兜底: 用户勾选的行为模式 → 来源标记为「本次复盘确认」
```

已在 `design.md` v2 更新，`learningFeedback.test.ts` 38 个用例全部通过（含 6 个 `action_taken` 回退场景）。


### Emotion Sparkline

```
- 纯 SVG path，无第三方依赖
- X轴: 最近30天日期
- Y轴: emotion_level 1-5
- 均值参考线（虚线）
- 本次值: 带标注的蓝色圆点
- 预警: 本次 > 均值 → ⚠️ 略高于均值
- 空状态: "数据不足，无法绘制趋势"
```

## Technical Design

### File Structure

```
investment-front/src/
├── components/
│   └── LearningFeedbackCard.tsx    # 组件（EmotionSparkline, JudgmentBar, TagUpdateRow, TrendBadge）
├── utils/
│   ├── learningFeedback.ts          # computeLearningFeedback + types
│   └── learningFeedback.test.ts     # 38 个用例（含 action_taken 回退场景）
└── pages/
    ├── PostTradeInput.tsx          # 传递 reviewFormData via location.state
    └── ResultPage.tsx              # 集成触发逻辑
```

### Key Types

```typescript
// LearningFeedbackData
interface LearningFeedbackData {
  tagUpdates: TagUpdate[];              // 标签更新列表
  judgmentQualityPercent: number;         // 0-100
  judgmentQualityDelta: number;         // vs 历史均值
  judgmentLevel: 'high' | 'medium' | 'low';
  judgmentBreakdown: JudgmentBreakdown;
  judgmentTrend: { direction: 'up' | 'down' | 'stable'; description: string };
  suggestion: string;
  emotionHistory: EmotionDataPoint[];   // 30天数据
  currentEmotionLevel: number;           // 1-5
}

interface TagUpdate {
  tag: string;
  type: 'add' | 'remove' | 'upgrade';
  source: string;
}
```

### Animation

- Backdrop: fade 200ms ease-out
- Sheet: spring `{ damping: 30, stiffness: 300 }` 从底部滑入
- Exit: 同动画逆向（退出比进入更快约 60-70%）

## Verified Implementation

已在 `6ee2677` + `0b379f9` + `e6b1db7` + 本次提交完成门禁收口；当前前端验证状态为：`npm run lint` 通过、`npm run build` 通过（仍有现存 chunk size warning）、`vitest` 46 个用例全部通过。

```
investment-front/src/components/LearningFeedbackCard.tsx   +468 (+新三按钮 + isHardToTell中性样式)
investment-front/src/pages/PostTradeInput.tsx              +21
investment-front/src/pages/ResultPage.tsx                   +119 (+localStorage追踪)
investment-front/src/utils/learningFeedback.ts             +206 (+含50分 + 下限兜底 + 难以区分处理)
investment-front/src/utils/learningFeedback.test.ts        +120 (+46个单元测试，含 localStorage 语义与 null safety)
```

关键验证点：
- [x] 三按钮（确认/稍后/忽略）渲染正确
- [x] 稍后按钮显示当前展示次数 (n/3)
- [x] 第 n 次展示时 header 显示 badge
- [x] backdrop 点击触发永久跳过
- [x] localStorage 在页面挂载时读取，防止重复展示
- [x] 展示次数 ≥ 3 时自动停止自动弹出
- [x] hint 文案解释三个按钮语义
- [x] "难以区分"不 return null，反馈卡正常展示
- [x] "难以区分"判断质量区显示灰色中性样式 + 说明文字 + breakdown 100% 柱
- [x] "难以区分"不计入历史聚合，不污染百分比计算
- [x] 数据 < 3 次时显示"数据积累中"，隐藏 delta / trend
- [x] `action_taken` 字段作为 `intent` 的回退，追涨/恐慌标签推断在两种场景均生效
- [x] `intent` 字段优先于 `action_taken`，两者同时存在时以 `intent` 为准
- [x] `learningFeedback.test.ts` 中 `beforeEach` 与 `localStorage` stub 已通过 TypeScript 类型检查，不再阻塞前端 `lint`
