## Purpose

定义行为干预的独立存储结构，支持冷静期追踪、用户确认反馈和动作归因，解决以内嵌 JSON 方式存储干预导致的查询困难和审计缺失问题。

## Requirements

### Requirement: 行为干预必须独立持久化
系统 SHALL 在识别到高风险行为偏差时将干预写入 `behavior_interventions` 表。干预 MUST 至少记录干预类型（`behavior_type`）、严重程度（`severity`）和触发时间，且系统 MUST 支持按用户 ID 查询历史干预记录。

#### Scenario: 识别追涨行为偏差并记录干预
- **WHEN** 分析判断用户当前操作属于追涨行为（`behavior_type = "chasing_rise"`）
- **THEN** 系统将干预写入 `behavior_interventions`，并设置 `severity` 为 `low/medium/high`

### Requirement: 行为干预必须设置冷静期
系统 SHALL 在输出高风险干预时设置 `cooldown_minutes`，并在该时间段内阻止或提示用户重复触发同类高风险操作。

#### Scenario: 高风险干预触发冷静期
- **WHEN** 干预 `severity` 为 `high`
- **THEN** 系统设置 `cooldown_minutes >= 10`，并在冷静期内对同类行为操作展示提示而非直接执行

### Requirement: 用户确认必须可追踪
系统 SHALL 记录用户对干预的确认行为（`user_acknowledged`）和补充备注（`user_notes`），并允许用户记录最终实际执行的动作（`action_taken`），用于后续归因分析。

#### Scenario: 用户确认并执行干预
- **WHEN** 用户看到干预提示后执行了操作
- **THEN** 系统记录 `user_acknowledged = true` 和 `action_taken`（`continued/delayed/cancelled/logged_only`）

### Requirement: 干预记录必须支持归因分析
系统 SHALL 支持按时间范围、行为类型和严重程度查询干预记录，并能统计用户的干预频率，为行为干预效果评估提供数据基础。

#### Scenario: 查询用户近30天干预记录
- **WHEN** 运营或系统查询用户近30天内的行为干预记录
- **THEN** 系统返回按 `behavior_type` 分组的干预统计和明细列表
