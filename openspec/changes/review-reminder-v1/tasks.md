## 1. Contract

- [x] 1.1 新增 `history-and-review-loop` delta spec，覆盖角标口径、过期强调、首页排序与会话内刷新语义
- [x] 1.2 同步 `.openspec.yaml`、`proposal.md`、`design.md` 的 capability 命名，移除孤立的 `review-loop`

## 2. Backend/Data

- [x] 2.1 复核本 change 无后端接口、数据模型和 migration 变更，继续复用 `GET /api/v1/reviews`

## 3. Frontend

- [x] 3.1 `App.tsx`（内含 `AppShell`）已渲染 Reviews tab 角标，并使用 `unfinishedReviews` state、颜色优先级和 `99+` 截断
- [x] 3.2 `HomePage.tsx` 已使用 `sortUnfinishedReviews(computeUnfinishedReviews(reviews))`，并为 expired 卡片显示红色逾期标签
- [x] 3.3 `ReviewsPage.tsx` 已为 `status === 'expired'` 卡片增加红色边框/背景和逾期天数
- [x] 3.4 `App.tsx` badge 刷新已收口为：主导航页 pathname 切换触发 + window focus 触发；拉取失败时清空旧角标；`ReviewsPage.tsx` 的未完成任务筛选已收敛到 `computeUnfinishedReviews`，消除口径分叉

## 4. QA/Release

- [x] 4.1 `npm test` 通过，`vitest` 46/46
- [x] 4.2 `npm run build` 通过；仍有现存 chunk size warning，非本 change 新引入
- [x] 4.3 `npm run lint` 已恢复通过；之前由 `src/utils/learningFeedback.test.ts` 中预存的 Storage mock / `beforeEach` 问题造成的阻塞已单独收口
- [ ] 4.4 手动 smoke：无待办、仅 pending、存在 expired、完成复盘后返回首页四条路径逐项确认
