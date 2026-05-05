import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertTriangle, BarChart3, CheckCircle2, Edit3, FilePlus2, Plus, RefreshCw, ShieldAlert, Trash2 } from 'lucide-react';

import {
  deleteHolding,
  getPortfolioOverview,
  getTransactions,
  postHolding,
  postTransaction,
  putHolding,
} from '../api';
import type { HoldingItem, PortfolioOverview, TransactionItem, TransactionSide } from '../types';
import { cn } from '../utils';


const emptyHolding = {
  stock_id: '',
  stock_name: '',
  market: '',
  quantity: '',
  cost_price: '',
  current_price: '',
  note: '',
};

const emptyTransaction = {
  stock_id: '',
  stock_name: '',
  market: '',
  side: 'buy' as TransactionSide,
  price: '',
  quantity: '',
  reason: '',
};

function money(value: number) {
  return `¥${value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`;
}

function percent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export default function PortfolioPage() {
  const navigate = useNavigate();
  const [overview, setOverview] = useState<PortfolioOverview | null>(null);
  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [editing, setEditing] = useState<HoldingItem | null>(null);
  const [holdingForm, setHoldingForm] = useState(emptyHolding);
  const [txForm, setTxForm] = useState(emptyTransaction);

  const load = async () => {
    setLoading(true);
    try {
      setError(null);
      const [portfolioData, txData] = await Promise.all([
        getPortfolioOverview(),
        getTransactions(),
      ]);
      setOverview(portfolioData);
      setTransactions(txData);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : '组合数据加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const summary = overview?.summary;
  const holdings = overview?.holdings ?? [];
  const topHolding = useMemo(() => holdings[0], [holdings]);

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(null), 2000);
  };

  const startEdit = (item: HoldingItem) => {
    setEditing(item);
    setHoldingForm({
      stock_id: item.stock_id,
      stock_name: item.stock_name,
      market: item.market,
      quantity: String(item.quantity),
      cost_price: String(item.cost_price),
      current_price: String(item.current_price),
      note: item.note || '',
    });
  };

  const fillFromHolding = (item: HoldingItem, side: TransactionSide) => {
    setTxForm({
      stock_id: item.stock_id,
      stock_name: item.stock_name,
      market: item.market,
      side,
      price: String(item.current_price),
      quantity: '',
      reason: '',
    });
  };

  const saveHolding = async () => {
    const payload = {
      stock_id: holdingForm.stock_id.trim().toUpperCase(),
      stock_name: holdingForm.stock_name.trim() || holdingForm.stock_id.trim().toUpperCase(),
      market: holdingForm.market.trim().toUpperCase() || holdingForm.stock_id.slice(0, 2).toUpperCase(),
      quantity: Number(holdingForm.quantity),
      cost_price: Number(holdingForm.cost_price),
      current_price: Number(holdingForm.current_price),
      note: holdingForm.note.trim() || null,
    };
    if (!payload.stock_id || !payload.quantity || !payload.cost_price || !payload.current_price) {
      showToast('请补全持仓信息');
      return;
    }
    if (editing) {
      await putHolding(editing.id, payload);
      showToast('持仓已更新');
    } else {
      await postHolding(payload);
      showToast('持仓已保存');
    }
    setEditing(null);
    setHoldingForm(emptyHolding);
    await load();
  };

  const saveTransaction = async () => {
    const payload = {
      stock_id: txForm.stock_id.trim().toUpperCase(),
      stock_name: txForm.stock_name.trim() || txForm.stock_id.trim().toUpperCase(),
      market: txForm.market.trim().toUpperCase() || txForm.stock_id.slice(0, 2).toUpperCase(),
      side: txForm.side,
      price: Number(txForm.price),
      quantity: Number(txForm.quantity),
      reason: txForm.reason.trim() || null,
    };
    if (!payload.stock_id || !payload.price || !payload.quantity) {
      showToast('请补全交易记录');
      return;
    }
    await postTransaction(payload);
    setTxForm(emptyTransaction);
    showToast('交易记录已保存');
    await load();
  };

  const removeHolding = async (id: string) => {
    await deleteHolding(id);
    showToast('持仓已删除');
    await load();
  };

  if (loading && !overview) {
    return <div className="p-8 text-center text-stone-400">正在加载组合...</div>;
  }

  if (error && !overview) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 p-8 text-center">
        <AlertTriangle size={34} className="text-amber-500" />
        <div>
          <h2 className="text-lg font-bold">组合数据暂时不可用</h2>
          <p className="mt-2 text-sm leading-relaxed text-stone-500">{error}</p>
        </div>
        <button onClick={() => load()} className="rounded-xl bg-ink px-5 py-3 text-sm font-bold text-white">
          重新加载
        </button>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-6 pb-32">
      {toast && (
        <div className="fixed top-20 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-xl bg-ink px-4 py-2 text-sm font-medium text-white shadow-lg">
          <CheckCircle2 size={16} />
          <span>{toast}</span>
        </div>
      )}

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">持仓组合</h2>
            <p className="text-sm text-stone-400">手动维护真实投资状态，用于辅助分析和复盘。</p>
          </div>
          <button onClick={() => load()} className="rounded-xl border border-stone-200 bg-white p-3 text-stone-500">
            <RefreshCw size={18} />
          </button>
        </div>

        <div className="rounded-2xl border border-stone-100 bg-white p-4">
          <div className="grid grid-cols-2 gap-3">
            <Metric label="总市值估算" value={money(summary?.total_market_value ?? 0)} />
            <Metric
              label="浮动盈亏"
              value={money(summary?.total_unrealized_pnl ?? 0)}
              tone={(summary?.total_unrealized_pnl ?? 0) >= 0 ? 'up' : 'down'}
            />
            <Metric label="持仓数" value={String(summary?.holding_count ?? 0)} />
            <Metric label="最大单票占比" value={percent(summary?.max_position_weight ?? 0)} />
          </div>
          {summary?.concentration_alert && (
            <div className="mt-4 flex gap-2 rounded-xl border border-amber-100 bg-amber-50 p-3 text-xs leading-relaxed text-amber-800">
              <ShieldAlert size={16} className="mt-0.5 shrink-0" />
              <span>{summary.concentration_alert}</span>
            </div>
          )}
          <div className="mt-3 text-[10px] text-stone-400">
            更新时间：{summary?.data_updated_at ? new Date(summary.data_updated_at).toLocaleString() : '暂无数据'}；当前价依赖手动维护，可能不是实时价格。
          </div>
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-bold uppercase tracking-widest text-stone-400">
          {editing ? '编辑持仓' : '新增持仓'}
        </h3>
        <div className="rounded-2xl border border-stone-100 bg-white p-4 space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <Input label="股票代码" value={holdingForm.stock_id} onChange={(value) => setHoldingForm((p) => ({ ...p, stock_id: value }))} />
            <Input label="股票名称" value={holdingForm.stock_name} onChange={(value) => setHoldingForm((p) => ({ ...p, stock_name: value }))} />
            <Input label="市场" value={holdingForm.market} onChange={(value) => setHoldingForm((p) => ({ ...p, market: value }))} />
            <Input label="数量" type="number" value={holdingForm.quantity} onChange={(value) => setHoldingForm((p) => ({ ...p, quantity: value }))} />
            <Input label="成本价" type="number" value={holdingForm.cost_price} onChange={(value) => setHoldingForm((p) => ({ ...p, cost_price: value }))} />
            <Input label="当前价" type="number" value={holdingForm.current_price} onChange={(value) => setHoldingForm((p) => ({ ...p, current_price: value }))} />
          </div>
          <textarea
            value={holdingForm.note}
            onChange={(event) => setHoldingForm((p) => ({ ...p, note: event.target.value }))}
            placeholder="持仓理由或仓位边界"
            className="min-h-20 w-full rounded-xl border border-stone-200 bg-stone-50 px-3 py-2 text-sm outline-none focus:border-ink"
          />
          <div className="flex gap-2">
            {editing && (
              <button onClick={() => { setEditing(null); setHoldingForm(emptyHolding); }} className="flex-1 rounded-xl border border-stone-200 py-3 text-sm font-bold text-stone-500">
                取消
              </button>
            )}
            <button onClick={saveHolding} className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-ink py-3 text-sm font-bold text-white">
              <Plus size={16} />
              保存持仓
            </button>
          </div>
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <h3 className="text-sm font-bold uppercase tracking-widest text-stone-400">持仓明细</h3>
          {topHolding && <span className="text-[10px] text-stone-400">按更新时间排序</span>}
        </div>
        {holdings.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-3">
            {holdings.map((item) => (
              <React.Fragment key={item.id}>
                <HoldingCard
                  item={item}
                  onEdit={() => startEdit(item)}
                  onDelete={() => removeHolding(item.id)}
                  onAnalysis={() => navigate(`/analysis/single-stock?stock_id=${item.stock_id}&stock_name=${encodeURIComponent(item.stock_name)}`)}
                  onReview={() => navigate(`/analysis/post-trade?stock_id=${item.stock_id}&stock_name=${encodeURIComponent(item.stock_name)}`)}
                  onBuy={() => fillFromHolding(item, 'buy')}
                  onSell={() => fillFromHolding(item, 'sell')}
                />
              </React.Fragment>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-bold uppercase tracking-widest text-stone-400">新增交易流水</h3>
        <div className="rounded-2xl border border-stone-100 bg-white p-4 space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <Input label="股票代码" value={txForm.stock_id} onChange={(value) => setTxForm((p) => ({ ...p, stock_id: value }))} />
            <Input label="股票名称" value={txForm.stock_name} onChange={(value) => setTxForm((p) => ({ ...p, stock_name: value }))} />
            <Input label="市场" value={txForm.market} onChange={(value) => setTxForm((p) => ({ ...p, market: value }))} />
            <select
              value={txForm.side}
              onChange={(event) => setTxForm((p) => ({ ...p, side: event.target.value as TransactionSide }))}
              className="rounded-xl border border-stone-200 bg-stone-50 px-3 py-2 text-sm outline-none focus:border-ink"
            >
              <option value="buy">买入</option>
              <option value="sell">卖出</option>
            </select>
            <Input label="价格" type="number" value={txForm.price} onChange={(value) => setTxForm((p) => ({ ...p, price: value }))} />
            <Input label="数量" type="number" value={txForm.quantity} onChange={(value) => setTxForm((p) => ({ ...p, quantity: value }))} />
          </div>
          <textarea
            value={txForm.reason}
            onChange={(event) => setTxForm((p) => ({ ...p, reason: event.target.value }))}
            placeholder="交易理由，或当时的自检结论"
            className="min-h-20 w-full rounded-xl border border-stone-200 bg-stone-50 px-3 py-2 text-sm outline-none focus:border-ink"
          />
          <button onClick={saveTransaction} className="flex w-full items-center justify-center gap-2 rounded-xl bg-ink py-3 text-sm font-bold text-white">
            <FilePlus2 size={16} />
            保存交易记录
          </button>
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-bold uppercase tracking-widest text-stone-400">最近交易</h3>
        <div className="space-y-2">
          {transactions.slice(0, 8).map((item) => (
            <div key={item.id} className="rounded-xl border border-stone-100 bg-white p-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-bold text-sm">{item.stock_name}</div>
                  <div className="mt-0.5 font-mono text-[10px] text-stone-400">{item.stock_id}</div>
                </div>
                <div className="text-right">
                  <div className={cn('text-sm font-bold', item.side === 'buy' ? 'text-red-600' : 'text-emerald-600')}>
                    {item.side === 'buy' ? '买入' : '卖出'} {item.quantity}
                  </div>
                  <div className="text-[10px] text-stone-400">{money(item.amount)}</div>
                </div>
              </div>
              {item.reason && <p className="mt-2 line-clamp-2 text-xs text-stone-500">{item.reason}</p>}
            </div>
          ))}
          {transactions.length === 0 && <div className="rounded-xl bg-stone-50 p-4 text-center text-xs text-stone-400">暂无交易流水</div>}
        </div>
      </section>

      <div className="flex gap-3 rounded-xl border border-amber-100 bg-amber-50 p-3 text-xs leading-relaxed text-amber-800">
        <AlertTriangle size={16} className="mt-0.5 shrink-0" />
        <p>持仓和交易流水用于辅助判断，不代表系统给出买卖指令，也不会接入券商或自动交易。</p>
      </div>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: 'up' | 'down' }) {
  return (
    <div className="rounded-xl bg-stone-50 p-3">
      <div className="text-[10px] text-stone-400">{label}</div>
      <div className={cn('mt-1 text-lg font-bold', tone === 'up' && 'text-red-600', tone === 'down' && 'text-emerald-600')}>
        {value}
      </div>
    </div>
  );
}

function Input({ label, value, onChange, type = 'text' }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return (
    <input
      aria-label={label}
      type={type}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={label}
      className="min-w-0 rounded-xl border border-stone-200 bg-stone-50 px-3 py-2 text-sm outline-none focus:border-ink"
    />
  );
}

function HoldingCard({ item, onEdit, onDelete, onAnalysis, onReview, onBuy, onSell }: {
  item: HoldingItem;
  onEdit: () => void;
  onDelete: () => void;
  onAnalysis: () => void;
  onReview: () => void;
  onBuy: () => void;
  onSell: () => void;
}) {
  const pnlUp = item.unrealized_pnl >= 0;
  return (
    <div className="rounded-2xl border border-stone-100 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h4 className="truncate text-lg font-bold">{item.stock_name}</h4>
          <div className="mt-0.5 font-mono text-[10px] text-stone-400">{item.stock_id} · {item.market}</div>
        </div>
        <div className="text-right">
          <div className={cn('font-bold', pnlUp ? 'text-red-600' : 'text-emerald-600')}>{money(item.unrealized_pnl)}</div>
          <div className="text-[10px] text-stone-400">{percent(item.unrealized_pnl_rate)}</div>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-center">
        <MetricMini label="数量" value={String(item.quantity)} />
        <MetricMini label="现价/成本" value={`${item.current_price}/${item.cost_price}`} />
        <MetricMini label="占比" value={percent(item.weight)} />
      </div>
      {item.note && <p className="mt-3 line-clamp-2 text-xs text-stone-500">{item.note}</p>}
      <div className="mt-4 grid grid-cols-6 gap-2">
        <IconButton title="编辑" onClick={onEdit} icon={Edit3} />
        <IconButton title="删除" onClick={onDelete} icon={Trash2} danger />
        <IconButton title="分析" onClick={onAnalysis} icon={BarChart3} />
        <IconButton title="复盘" onClick={onReview} icon={ShieldAlert} />
        <button onClick={onBuy} className="rounded-xl bg-red-50 py-2 text-xs font-bold text-red-600">买</button>
        <button onClick={onSell} className="rounded-xl bg-emerald-50 py-2 text-xs font-bold text-emerald-600">卖</button>
      </div>
    </div>
  );
}

function MetricMini({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-stone-50 p-2">
      <div className="text-[10px] text-stone-400">{label}</div>
      <div className="mt-1 truncate text-xs font-bold">{value}</div>
    </div>
  );
}

function IconButton({ title, icon: Icon, onClick, danger }: { title: string; icon: React.ElementType; onClick: () => void; danger?: boolean }) {
  return (
    <button
      title={title}
      onClick={onClick}
      className={cn('flex items-center justify-center rounded-xl bg-stone-50 py-2 text-stone-500', danger && 'text-red-500')}
    >
      <Icon size={16} />
    </button>
  );
}

function EmptyState() {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center rounded-2xl border border-dashed border-stone-200 bg-white p-8 text-center">
      <BarChart3 size={36} className="text-stone-300" />
      <p className="mt-3 text-sm font-bold text-stone-600">还没有持仓记录</p>
      <p className="mt-1 text-xs text-stone-400">先录入一条持仓，分析和自检会开始理解你的真实仓位。</p>
      <Link to="/stock/search?callback=/portfolio" className="mt-4 rounded-xl bg-ink px-4 py-2 text-xs font-bold text-white">
        搜索标的
      </Link>
    </div>
  );
}
