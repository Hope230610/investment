## Purpose

定义观察列表与关注理由的持久化、一致性和用户归属边界，确保该能力能够跨设备复用并服务后续复盘闭环。本 spec 聚焦"用户关注过什么、为什么关注、在不同设备上是否还是同一份事实"，不规定具体存储方案、接口对象名或前端状态实现。

## Requirements

### Requirement: 观察列表必须按用户持久化
系统 SHALL 将观察列表作为用户账号资产持久化保存，而不是只依赖单设备本地状态。用户在不同设备或会话中登录后 MUST 看到同一份观察列表，并且任何读写都必须受资源归属鉴权保护。

观察列表的服务端真源为 `watchlists` 表（新版），不再是 `watchlist_items_legacy` 表（旧版）。`/api/v1/watchlist` 路由对应的 WatchlistService 路径为废弃路径，不再向前端新增调用。后续所有观察列表操作走 `POST /api/v1/analysis/{id}/record-reason` 写入（通过分析记录附带写入），读路径走 `GET /api/v1/analysis` 的 filtered 查询或后续新增的专用 API。

#### Scenario: 用户跨设备查看观察列表
- **WHEN** 同一用户在另一台设备登录并打开观察列表
- **THEN** 系统返回与原设备一致的服务端持久化列表

#### Scenario: 跨设备查看观察列表（服务端真源）
- **WHEN** 用户在设备 A 添加股票到观察列表，设备 B 登录同一账号
- **THEN** 设备 B 通过服务端的读路径查询，应能查到该股票

#### Scenario: 废弃路径不再产生新数据
- **WHEN** 任何前端页面调用 `/api/v1/watchlist`
- **THEN** 返回 404 或空列表，不得向 watchlist_items_legacy 表写入新数据

### Requirement: 关注理由必须可结构化保存与更新
系统 SHALL 允许用户为观察标的记录结构化关注理由，并将该信息与观察记录一并持久化。关注理由 MUST 支持后续更新、清空与回显，且长度和敏感信息范围应受约束。

`POST /api/v1/analysis/{id}/record-reason` 为当前唯一的理由写入路径，写入后 `watchlists` 表的 `focus_reason` 字段必须可被查询。

#### Scenario: 用户更新关注理由
- **WHEN** 用户为已在观察列表中的股票修改关注理由
- **THEN** 系统更新对应观察记录，并在后续读取时返回最新的关注理由

#### Scenario: 保存关注理由后可在服务端查回
- **WHEN** 用户在结果页为某股票提交"记录关注理由"，reason 为"准备年报后建仓"
- **THEN** 系统将理由写入 `watchlists` 表的 `focus_reason` 字段。后续通过服务端的读路径查询时，应能返回该理由（非 localStorage）。

### Requirement: 观察列表操作必须具备一致性和幂等性
系统 MUST 对添加、移除和更新观察项提供一致的持久化语义。重复添加同一标的不得产生脏重复数据；移除后再次读取必须反映最新状态；状态同步失败时必须返回明确错误，而不是静默丢失更新。

当 `record-reason` 写入的 `user_id + stock_id` 组合已存在时，系统 SHALL 执行 upsert（更新 focus_reason），而不是创建新记录或报错。

#### Scenario: 重复添加同一股票
- **WHEN** 用户连续两次将同一股票加入观察列表
- **THEN** 系统保持单条有效观察记录，并返回一致的当前状态

#### Scenario: 重复提交相同股票的 record-reason
- **WHEN** 用户对同一股票第二次调用 `POST /api/v1/analysis/{id}/record-reason`
- **THEN** 系统更新现有 `watchlists` 记录的 `focus_reason` 字段，并返回该记录 ID（而非创建新记录）。数据库只保留一条有效的观察记录。
