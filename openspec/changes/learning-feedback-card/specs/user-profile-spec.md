## ADDED Requirements

### Requirement: 画像学习闭环必须基于复盘确认写入行为标签
系统 SHALL 在用户完成复盘后，以主动反馈形式展示行为标签更新，并且行为标签 MUST 仅在用户显式确认后写入 `UserProfile.behavior_tags`。系统推断标签与用户自报标签 MUST 记录来源说明，以便后续追溯。

#### Scenario: 用户确认行为标签更新
- **WHEN** 反馈卡展示新增或确认的行为标签
- **AND** 用户点击“确认”
- **THEN** 系统将对应标签写入 `UserProfile.behavior_tags`
- **AND** 系统记录标签来源为“本次复盘确认”或具体触发条件

#### Scenario: 用户忽略反馈卡
- **WHEN** 反馈卡展示行为标签更新
- **AND** 用户点击“忽略”
- **THEN** 系统关闭反馈卡且不写入行为标签
- **AND** 已经写入的判断质量历史不受影响

### Requirement: 画像系统必须提供学习历史查询
系统 SHALL 提供 learning history 查询接口，返回情绪历史与判断质量历史，供结果页与画像页展示趋势。查询结果 MUST 支持最近 N 天范围，并保留“难以区分”标记，供前端决定是否纳入聚合。

#### Scenario: 用户查看学习记录
- **WHEN** 已登录用户在结果页或画像页请求 learning history
- **THEN** 系统返回 `emotion_history` 与 `judgment_history`
- **AND** `judgment_history` 包含 `score`、`label` 和 `is_hard_to_tell`
- **AND** 前端可据此展示 sparkline、趋势条和最近记录列表
