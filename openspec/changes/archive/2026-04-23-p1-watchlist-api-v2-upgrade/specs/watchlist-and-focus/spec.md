## ADDED Requirements

### Requirement: 观察列表专用 API 必须返回可展示的股票摘要
系统 SHALL 为观察列表提供稳定的专用 API 契约，使前端在不额外拼接本地缓存或二次查询的前提下即可展示观察项。`GET /api/v1/watchlist` 与创建、更新接口返回的观察项 MUST 包含 UUID 字符串 `id`、`stock_id`、`stock_name`、`market`、可选 `industry`、可选 `focus_reason` 以及统一时间字段；同一观察项在列表和写接口中的字段语义 MUST 一致。

#### Scenario: 列表接口返回完整展示字段
- **WHEN** 已登录用户调用 `GET /api/v1/watchlist`
- **THEN** 系统返回的每个观察项都包含 `id`、`stock_id`、`stock_name`、`market`、可选 `industry`、`focus_reason` 和统一时间字段，且 `id` 为 UUID 字符串

#### Scenario: 写接口返回值可直接回写前端状态
- **WHEN** 用户调用 `POST /api/v1/watchlist` 或 `PUT /api/v1/watchlist/{item_id}`
- **THEN** 系统返回与列表接口同语义的观察项结构，而不是 legacy `int` ID 或缺字段响应

## MODIFIED Requirements

### Requirement: 观察列表必须按用户持久化
系统 SHALL 将观察列表作为用户账号资产持久化保存，而不是只依赖单设备本地状态。用户在不同设备或会话中登录后 MUST 看到同一份观察列表，并且任何读写都必须受资源归属鉴权保护。

观察列表的服务端真源 MUST 为 `watchlists` 表（新版），不得再向 `watchlist_items_legacy` 表写入新数据。`/api/v1/watchlist` MUST 作为面向前端的专用观察列表 API，直接读写 `watchlists` 表并返回 v2 契约；`POST /api/v1/analysis/{id}/record-reason` 与该专用 API MUST 共享同一数据源，而不是形成双写分裂。

#### Scenario: 用户跨设备查看观察列表
- **WHEN** 同一用户在另一台设备登录并打开观察列表
- **THEN** 系统返回与原设备一致的服务端持久化列表

#### Scenario: 跨设备查看观察列表（服务端真源）
- **WHEN** 用户在设备 A 通过 `POST /api/v1/watchlist` 或 `POST /api/v1/analysis/{id}/record-reason` 添加股票到观察列表，设备 B 登录同一账号
- **THEN** 设备 B 通过 `GET /api/v1/watchlist` 查询时，应能查到同一条观察记录

#### Scenario: 专用 API 不再写入旧表
- **WHEN** 任意前端页面调用 `/api/v1/watchlist` 执行新增、更新或删除
- **THEN** 系统只对 `watchlists` 表执行读写，不得向 `watchlist_items_legacy` 写入新数据

### Requirement: 关注理由必须可结构化保存与更新
系统 SHALL 允许用户为观察标的记录结构化关注理由，并将该信息与观察记录一并持久化。关注理由 MUST 支持后续更新、清空与回显，且长度和敏感信息范围应受约束。

`POST /api/v1/analysis/{id}/record-reason` MUST 继续支持从分析结果页写入关注理由，但不再是唯一写路径；`POST /api/v1/watchlist` 与 `PUT /api/v1/watchlist/{item_id}` 也 MUST 能创建或更新同一条 `watchlists` 记录中的 `focus_reason`。无论通过哪条路径写入，后续通过 `GET /api/v1/watchlist` 查询时 MUST 返回最新理由。

#### Scenario: 用户更新关注理由
- **WHEN** 用户为已在观察列表中的股票调用 `PUT /api/v1/watchlist/{item_id}` 修改关注理由
- **THEN** 系统更新对应 `watchlists` 记录，并在后续读取时返回最新的关注理由

#### Scenario: 保存关注理由后可在服务端查回
- **WHEN** 用户在结果页为某股票提交“记录关注理由”，reason 为“准备年报后建仓”
- **THEN** 系统将理由写入 `watchlists` 表的 `focus_reason` 字段，后续通过 `GET /api/v1/watchlist` 查询时应能返回该理由

### Requirement: 观察列表操作必须具备一致性和幂等性
系统 MUST 对添加、移除和更新观察项提供一致的持久化语义。重复添加同一标的不得产生脏重复数据；移除后再次读取必须反映最新状态；状态同步失败时必须返回明确错误，而不是静默丢失更新。

`POST /api/v1/watchlist` 与 `POST /api/v1/analysis/{id}/record-reason` 在同一用户的 `user_id + stock_id` 组合已存在时 SHALL 执行 upsert，并返回同一条观察记录的 UUID 标识，而不是创建平行记录。`DELETE /api/v1/watchlist/{item_id}` MUST 基于 UUID 标识删除对应记录，并在后续读取中消失。

#### Scenario: 重复添加同一股票
- **WHEN** 用户连续两次通过 `POST /api/v1/watchlist` 将同一股票加入观察列表
- **THEN** 系统保持单条有效观察记录，并返回同一个观察项 UUID

#### Scenario: 重复提交相同股票的 record-reason
- **WHEN** 用户对同一股票第二次调用 `POST /api/v1/analysis/{id}/record-reason`
- **THEN** 系统更新现有 `watchlists` 记录的 `focus_reason` 字段，并返回该记录 ID（而非创建新记录），数据库只保留一条有效观察记录

#### Scenario: 专用 API 与 record-reason 不得分裂数据源
- **WHEN** 用户先通过 `POST /api/v1/watchlist` 添加观察项，再通过 `POST /api/v1/analysis/{id}/record-reason` 更新理由
- **THEN** 两次操作命中同一条 `watchlists` 记录，随后 `GET /api/v1/watchlist` 只能看到一条最新记录

#### Scenario: 删除后列表反映最新状态
- **WHEN** 用户调用 `DELETE /api/v1/watchlist/{item_id}` 删除某个观察项
- **THEN** 后续 `GET /api/v1/watchlist` 不再返回该观察项
