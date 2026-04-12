import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ChevronRight, Info, Search } from 'lucide-react';

import { apiPost } from '../api';


export default function SingleStockInput() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const stockId = searchParams.get('stock_id') || '';
  const stockName = searchParams.get('stock_name') || '';

  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!stockId || submitting) return;

    setSubmitting(true);
    setError(null);

    try {
      const data = await apiPost<{ id: string }>('/api/v1/analysis', {
        scenario: 'single_stock_check',
        stock_id: stockId,
        scenario_payload: { focus_reason: reason.trim() || undefined },
      });
      navigate(`/analysis/${data.id}/result`);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : '创建分析失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-4 space-y-8">
      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">单股咨询</h2>
        <p className="text-sm text-stone-400">快速评估这只股票现在是否值得继续跟踪</p>
      </div>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">选择股票</label>
        <button
          onClick={() => navigate('/stock/search?callback=/analysis/single-stock')}
          className="w-full p-4 bg-white border border-stone-200 rounded-2xl flex items-center justify-between group"
        >
          {stockId ? (
            <div className="text-left">
              <div className="font-bold text-lg">{stockName}</div>
              <div className="text-xs text-stone-400 font-mono">{stockId}</div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-stone-400">
              <Search size={18} />
              <span className="text-sm">点击搜索 A 股标的</span>
            </div>
          )}
          <ChevronRight size={18} className="text-stone-300" />
        </button>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-bold uppercase tracking-widest text-stone-400">关注原因</label>
          <span className="text-[10px] text-stone-300">{reason.length}/100</span>
        </div>
        <textarea
          placeholder="例如：近期跌幅较大、行业有利好消息、准备加入观察列表等"
          className="w-full bg-white border border-stone-200 rounded-2xl p-4 text-sm h-32 focus:ring-2 focus:ring-ink resize-none"
          maxLength={100}
          value={reason}
          onChange={(event) => setReason(event.target.value)}
        />
      </section>

      <div className="bg-stone-100 p-4 rounded-2xl flex gap-3 items-start">
        <Info size={18} className="text-stone-400 shrink-0 mt-0.5" />
        <p className="text-xs text-stone-500 leading-relaxed">
          系统会基于实时股价、最近公告和你的用户画像生成一张可以直接用于跟踪管理的分析卡片。
        </p>
      </div>

      {error && (
        <div className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="pt-4">
        <button
          disabled={!stockId || submitting}
          onClick={handleSubmit}
          className="w-full py-4 bg-ink text-white rounded-2xl font-bold text-lg active:scale-[0.98] transition-all disabled:opacity-30 disabled:scale-100"
        >
          {submitting ? '分析中...' : '开始结构化分析'}
        </button>
        <p className="text-center text-[10px] text-stone-400 mt-4 uppercase tracking-widest">
          系统不会直接给出买卖指令
        </p>
      </div>
    </div>
  );
}
