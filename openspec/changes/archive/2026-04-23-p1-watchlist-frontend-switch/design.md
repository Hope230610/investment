## What Capabilities Change

### Modified Capabilities

- `watchlist-and-focus`：前端观察列表全链路（列表/添加/删除）切换到 B1a 冻结的 v2 API，`WatchlistPage`、`HomePage`、`ResultPage`、`StockSearchPage` 不再读写 localStorage。

## Capabilities

### Frozen API Contract（from B1a handoff）

```
GET  /api/v1/watchlist           → List<WatchlistApiItem>
POST /api/v1/watchlist           → WatchlistApiItem
PUT  /api/v1/watchlist/{itemId} → WatchlistApiItem  (itemId: UUID string)
DELETE /api/v1/watchlist/{itemId} → { message: string }  (itemId: UUID string)
```

`WatchlistApiItem` 字段（B1a 冻结）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `string` (UUID) | 路由参数使用此值 |
| `stock_id` | `string` | — |
| `stock_name` | `string` | B1a 新增 |
| `market` | `string` | B1a 新增 |
| `industry` | `string?` | B1a 新增 |
| `focus_reason` | `string?` | — |
| `created_at` | `string` | 前端映射为 `added_at` |
| `updated_at` | `string` | — |

## Technical Design

### File Changes

```
investment-front/src/
├── api.ts                      # B1a 已添加：getWatchlistItems / postWatchlistItem / putWatchlistItem / deleteWatchlistItem
├── types.ts                   # WatchlistApiItem（B1a）+ WatchlistItem 注释更新
├── utils.ts                   # 移除 getWatchlist / addToWatchlist / removeFromWatchlist
└── pages/
    ├── WatchlistPage.tsx       # list + delete → API
    ├── HomePage.tsx            # list → API
    ├── ResultPage.tsx           # add/delete → API，"已添加"判断 → API
    └── StockSearchPage.tsx     # add → API，"已添加"判断 → API
```

### WatchlistPage.tsx Changes

```tsx
// Before
import { getWatchlist, removeFromWatchlist } from '../utils';
const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
useEffect(() => { setWatchlist(getWatchlist()); }, []);
const handleRemove = (id: string) => {
  removeFromWatchlist(id);
  setWatchlist(getWatchlist());
};
// item.added_at

// After
import { getWatchlistItems, deleteWatchlistItem } from '../api';
import type { WatchlistApiItem } from '../types';
const [watchlist, setWatchlist] = useState<WatchlistApiItem[]>([]);
useEffect(() => {
  getWatchlistItems().then(setWatchlist).catch(() => setWatchlist([]));
}, []);
const handleRemove = async (id: string) => {
  await deleteWatchlistItem(id);
  setWatchlist((prev) => prev.filter((item) => item.id !== id));
};
// item.created_at（显示为 added_at）
```

### HomePage.tsx Changes

```tsx
// Before
import { getWatchlist } from '../utils';
const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
useEffect(() => { setWatchlist(getWatchlist()); }, []);

// After
import { getWatchlistItems } from '../api';
import type { WatchlistApiItem } from '../types';
const [watchlist, setWatchlist] = useState<WatchlistApiItem[]>([]);
useEffect(() => {
  getWatchlistItems().then(setWatchlist).catch(() => setWatchlist([]));
}, []);
```

### ResultPage.tsx Changes

```tsx
// Before
import { addToWatchlist, getWatchlist } from '../utils';
// 检查是否已在列表
const watchlist = getWatchlist();
const isInWatchlist = watchlist.some(w => w.stock_id === stockId);
// 添加
addToWatchlist({ stock_id, stock_name, market, industry, focus_reason });

// After
import { getWatchlistItems, postWatchlistItem, deleteWatchlistItem } from '../api';
// 检查是否已在列表：GET 一次，在 then 里判断
// 添加
await postWatchlistItem({ stock_id, focus_reason });
// 删除
await deleteWatchlistItem(itemId);
```

注意：`postWatchlistItem` 只需 `stock_id` + `focus_reason`，不需要 `stock_name`/`market`（API JOIN stocks 表获取）。

### StockSearchPage.tsx Changes

```tsx
// Before
import { addToWatchlist, getWatchlist } from '../utils';
const storedWatchlist = getWatchlist();
const isAdded = storedWatchlist.some(...);
addToWatchlist(stock);

// After
import { getWatchlistItems, postWatchlistItem } from '../api';
// 初始加载时 GET list，缓存到本地 state
// "已添加"判断基于 state 数组
await postWatchlistItem({ stock_id: stock.stock_id, focus_reason: stock.focus_reason });
```

### utils.ts Cleanup

移除以下导出（不再有 localStorage watchlist 写入路径）：

```typescript
// 删除
export const getWatchlist = ...
export const addToWatchlist = ...
export const removeFromWatchlist = ...
```

保留 `STORAGE_KEYS.WATCHLIST`（其他模块可能引用）和 `getFocusReasons` / `addFocusReason`（独立功能）。

### types.ts Alignment

`WatchlistItem`（页面层使用）保持字段不变，`added_at` 字段加注释说明来源：

```typescript
export interface WatchlistItem {
  // ...
  /** 来源：服务端 API 的 created_at，前端映射后展示为此字段 */
  added_at: string;
}
```

`WatchlistApiItem`（B1a 已定义）字段不变。

### Error Handling

- API 读取失败：显示空状态，不阻断页面渲染（`catch(() => setWatchlist([]))`）
- 添加失败：Toast 提示错误，不静默失败
- 删除失败：Toast 提示错误，保留列表项

### Animation

- 列表加载：skeleton 占位（复用现有 loading 态）
- 添加/删除：乐观更新（先更新 UI，再调 API，失败回滚）

## Verified Implementation

✅ TypeScript 编译零错误（app 文件）；Vite build 零警告（仅 chunk size 提示，非本次引入）；vitest 46/46 通过

✅ 实现清单：
- `WatchlistPage.tsx`：→ `getWatchlistItems()` / `deleteWatchlistItem()`；`added_at` → `created_at`；loading 态；乐观删除
- `HomePage.tsx`：→ `getWatchlistItems()` from `api.ts`；静默降级
- `ResultPage.tsx`：→ `getWatchlistItems()` / `postWatchlistItem()`；移除 localStorage 引用
- `StockSearchPage.tsx`：→ `getWatchlistItems()` / `postWatchlistItem()`；`Set<string>` 判断已添加；乐观更新
- `utils.ts`：移除 `getWatchlist` / `addToWatchlist` / `removeFromWatchlist`；保留 `getFocusReasons` / `addFocusReason`
- `types.ts`：`WatchlistItem` + `WatchlistApiItem` 注释更新为 B1b 完成状态
