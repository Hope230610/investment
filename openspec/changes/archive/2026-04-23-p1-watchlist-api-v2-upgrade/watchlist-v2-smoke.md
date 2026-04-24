# Watchlist v2 Smoke Checklist

## Preconditions

- 后端已部署包含本 change 的代码
- 数据库已具备 `watchlists` 表与 `addedfromscenarioenum` 规范化迁移
- 使用一个已登录用户账号

## API Smoke

### 1. GET /api/v1/watchlist

- 预期返回 200
- 每个观察项包含：
  - `id`（UUID 字符串）
  - `stock_id`
  - `stock_name`
  - `market`
  - `industry`
  - `focus_reason`
  - `created_at`
  - `updated_at`

### 2. POST /api/v1/watchlist

请求示例：

```json
{
  "stock_id": "SH600519",
  "focus_reason": "等待估值回落后再跟踪"
}
```

- 预期返回 200
- 返回体字段与 GET 单项结构一致
- `id` 为 UUID 字符串
- 重复提交同一 `stock_id` 时不新增第二条记录

### 3. PUT /api/v1/watchlist/{item_id}

请求示例：

```json
{
  "focus_reason": "更新后的关注理由"
}
```

- 预期返回 200
- 再次 GET 时该观察项的 `focus_reason` 已更新

### 4. POST /api/v1/analysis/{uuid}/record-reason

请求示例：

```json
{
  "stock_id": "SH600519",
  "reason": "结果页记录理由"
}
```

- 预期返回 200
- 返回的 `id` 与观察列表中对应股票的 `id` 相同
- 再次 GET `/api/v1/watchlist` 时仅有一条记录，且理由为最新值

### 5. DELETE /api/v1/watchlist/{item_id}

- 预期返回 200
- 再次 GET 时该观察项已消失

## Legacy Guardrail

- 执行 POST / PUT / DELETE `/api/v1/watchlist` 后，确认新增或更新结果出现在 `watchlists`
- 确认 `watchlist_items_legacy` 未出现对应新写入

## Error Contract

- 非法 `item_id` 返回统一错误结构：
  - `error.code`
  - `error.message`
  - `error.request_id`
  - `error.retryable`
- 不再依赖旧的 `detail` 字段作为唯一解析入口
