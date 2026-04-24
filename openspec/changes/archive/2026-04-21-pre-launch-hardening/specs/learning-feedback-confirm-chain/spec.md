## MODIFIED Requirements

### Requirement: 复盘任务必须有完整生命周期

系统 SHALL 对复盘任务使用统一生命周期管理，至少覆盖待处理、已完成和已过期三类业务状态，并提供读取和完成能力。任何复盘任务状态变更 MUST 与对应的分析记录和用户归属建立可追溯关联。

复盘任务的完成操作 SHALL 通过两步原子性行为完成：
- **Step1**：写入 emotion_history 和 judgment_history（画像学习）
- **Step2**：更新对应 review_task 的 status 为 completed

两步均需成功才算完成。任何一步失败（包括 404 Not Found），系统 SHALL 记录结构化日志但不向用户展示错误。失败不得导致前端静默标记为"已处理"。

#### Scenario: 用户完成复盘任务（两步均成功）
- **WHEN** 用户在结果页点击 feedback card 的"确认"按钮，且 Step1（画像写入）和 Step2（review_task 更新）均返回 2xx
- **THEN** 系统关闭卡片，且 emotion_history 有新记录、review_tasks.status 为 completed

#### Scenario: Step2 失败（ReviewTask 不存在）
- **WHEN** 用户点击"确认"，Step1 返回 2xx，但 Step2 返回 404（ReviewTask 未找到）
- **THEN** 系统关闭卡片、记录结构化日志（含 analysis_task_id 和错误码），但 review_tasks.status 保持不变。不得向用户展示错误。

#### Scenario: Step1 失败
- **WHEN** 用户点击"确认"，Step1 返回 500 或其他错误
- **THEN** 系统关闭卡片并记录错误，不标记为已处理。下次打开结果页时卡片仍可弹出。

---

### Requirement: 结果回看必须处理过期与再评估

系统 MUST 在分析结果超过有效期后，将其标记为已过期或明确提示需要重新评估。用户回看过期结果时，系统 SHALL 提示该结论不可继续作为当前操作依据，并提供重新分析或重新复盘的入口语义。

当用户对过期结果提交复盘反馈时，系统 SHALL 接受反馈并写入 emotion_history 和 judgment_history，即使 review_task.status 为已过期状态也不例外（用户可对历史结果做新的学习记录）。

#### Scenario: 用户对过期结果提交 learning feedback
- **WHEN** 用户打开已过期分析结果，并在反馈卡中点击"确认"
- **THEN** 系统将 emotion_level 和 judgment_score 写入 emotion_history/judgment_history，即使对应的 review_task.status 已为过期状态。review_task.status 保持不变（不再更新为已完成）。