# Smoke Checklist — reviews-page-reminder-resolve

验证 ReviewsPage 入口修复后，未完成 reminder 数量能净减少。

## 前置条件

- 后端服务运行中（`uvicorn main:app`）
- 前端服务运行中（`npm run dev`）
- 数据库已迁移到 HEAD（`alembic upgrade head`）
- 测试用户：user_id=1（username=testuser, password=smoke123）
- 基线未完成数：29（`SELECT COUNT(*) FROM review_tasks WHERE user_id=1 AND status != 'COMPLETED'`）

---

## 1. ReviewsPage 入口链路（核心验证）

### 1.1 基线确认

```bash
# DB 查询当前未完成数，期望 29
python -c "
import os; os.environ['DATABASE_URL']='postgresql://postgres:123456@localhost:5432/investment_db'
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    r = conn.execute(text(\"SELECT COUNT(*) FROM review_tasks WHERE user_id=1 AND status!='COMPLETED'\"))
    for row in r: print('uncompleted:', row[0])
"
```

### 1.2 选一条 post_trade_review PENDING reminder 作为入口

```bash
# 找一条 scenario='post_trade_review'、analysis_task_id 非空、status=PENDING 的 reminder
# 记录其 id 和 analysis_task_id（UUID）
```

### 1.3 创建 analysis（带 pending_review_task_id）

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"smoke123"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -X POST http://localhost:8000/api/v1/analysis \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": "post_trade_review",
    "stock_id": "<从步骤1.2取到的stock_id>",
    "scenario_payload": {
      "action_taken": "smoke test",
      "outcome_summary": "smoke test outcome",
      "plan_deviation": false,
      "judgement_quality": "主要来自判断",
      "behavior_patterns": ["纪律稳定"],
      "emotion_level": 3,
      "pending_review_task_id": "<从步骤1.2取到的analysis_task_id（UUID）>"
    }
  }'
# 期望：返回 {"id": "<新UUID>", "status": "processing"}
```

### 1.4 轮询等待 analysis 完成

```bash
NEW_ID="<上一步返回的id>"
for i in $(seq 1 30); do
  sleep 5
  STATUS=$(curl -s "http://localhost:8000/api/v1/analysis/$NEW_ID" \
    -H "Authorization: Bearer $TOKEN" | python -c "import sys,json; print(json.load(sys.stdin).get('status','?'))")
  echo "[$i] status=$STATUS"
  if [ "$STATUS" = "ready" ]; then echo "DONE"; break; fi
done
```

### 1.5 验证新 ReviewTask 未创建

```bash
# 新 analysis 的 UUID 在 review_tasks 表中不存在（修复生效）
python -c "
import os; os.environ['DATABASE_URL']='postgresql://postgres:123456@localhost:5432/investment_db'
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    r = conn.execute(text(\"SELECT COUNT(*) FROM review_tasks WHERE analysis_task_id='<NEW_ID>'\"))
    for row in r: print('new review task count (expected 0):', row[0])
"
```

### 1.6 标记原始 reminder 完成

```bash
ORIGINAL_UUID="<步骤1.2取到的analysis_task_id（UUID）>"
curl -X PATCH "http://localhost:8000/api/v1/reviews/by-analysis/$ORIGINAL_UUID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mark_completed": true}'
# 期望：返回 200，status="completed"
```

### 1.7 验证未完成数 = 28

```bash
python -c "
import os; os.environ['DATABASE_URL']='postgresql://postgres:123456@localhost:5432/investment_db'
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    r = conn.execute(text(\"SELECT COUNT(*) FROM review_tasks WHERE user_id=1 AND status!='COMPLETED'\"))
    for row in r: print('uncompleted (expected 28):', row[0])
"
```

---

## 2. 直接入口回归验证

### 2.1 创建 analysis（不带 pending_review_task_id）

```bash
curl -X POST http://localhost:8000/api/v1/analysis \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": "post_trade_review",
    "stock_id": "SZ000001",
    "scenario_payload": {
      "action_taken": "regression test",
      "outcome_summary": "regression test outcome",
      "plan_deviation": false,
      "judgement_quality": "主要来自判断",
      "behavior_patterns": [],
      "emotion_level": 3
    }
  }'
# 期望：返回新 id，ReviewTask 正常创建
```

### 2.2 验证 ReviewTask 正常创建

```bash
# 等待上一步的 analysis 完成（步骤同 1.4）
# 然后查询新 analysis UUID 对应的 review_tasks 有 1 条记录
```

---

## 3. 清理

```bash
# 删除测试数据，恢复基线
python -c "
import os; os.environ['DATABASE_URL']='postgresql://postgres:123456@localhost:5432/investment_db'
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    # 恢复原始 reminder
    conn.execute(text(\"UPDATE review_tasks SET status='PENDING', review_result=NULL WHERE id=<步骤1.2的id>\"))
    # 删除测试 analysis 和 review_tasks
    conn.execute(text(\"DELETE FROM review_tasks WHERE analysis_task_id IN ('<test1_id>', '<test2_id>')\"))
    conn.execute(text(\"DELETE FROM analysis_tasks WHERE id IN ('<test1_id>', '<test2_id>')\"))
    conn.commit()
"
# 确认恢复：未完成数回到 29
```

---

## 失败处理策略

| 症状 | 可能原因 | 修复 |
|---|---|---|
| 新 analysis 创建后 ReviewTask 仍被创建 | analysis_service.py 的跳过逻辑未生效 | 检查 `scenario_payload.get("pending_review_task_id")` 是否取到了值 |
| patch 原始 reminder 返回 404 | pending_review_task_id 指向的 UUID 在 review_tasks 中不存在 | 选一条有 analysis_task_id 的 PENDING reminder |
| 未完成数仍是 29 | patch 步骤未执行或失败 | 检查 ResultPage 是否正确调用了 patchReviewResult |
