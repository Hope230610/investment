## 1. Contract

- [x] 1.1 补充 `watchlist-contract-audit` delta spec（研究型变更，覆盖核查范围和输出格式）：`specs/watchlist-and-focus-audit/spec.md`，含审计摘要、4 项发现与 baseline spec 对比、B1a 必要修复清单

## 2. Backend Audit

- [x] 2.1 读取 `investment-back/src/api/v1/watchlist.py`，逐路由记录：路径、Schema、ID类型、时间字段、权限
- [x] 2.2 读取 `investment-back/src/models/watchlist.py` 和 `watchlist_v2.py`，确认两套表并存现状
- [x] 2.3 读取 `investment-back/src/schemas/watchlist.py`，确认 Pydantic schema 与服务层返回

## 3. Frontend Audit

- [x] 3.1 读取 `investment-front/src/types.ts` 中 `WatchlistItem` 类型定义
- [x] 3.2 读取 `investment-front/src/utils.ts` 中 localStorage watchlist 辅助函数
- [x] 3.3 对比数据库设计文档（`structure/database_design.md`）确认 v2 表设计意图
- [x] 3.4 核查分析链路中 `record-reason` 写入 `watchlists` v2 的服务路径，确认与 legacy watchlist API 不共享数据源

## 4. Output

- [x] 4.1 输出 `audit-report.md`：后端路由现状 + 两套表并存分析 + 字段映射表 + 已知差异 + 方案建议
- [x] 4.2 输出 `conclusion.md`：**前提不满足**，建议 B1 拆分为 B1a（API 升级 v2 表）+ B1b（前端切换），附推荐路线图和核查产出清单