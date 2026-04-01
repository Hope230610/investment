import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, Calendar, ChevronRight, Search, Trash2 } from 'lucide-react';

import type { WatchlistItem } from '../types';
import { getWatchlist, removeFromWatchlist } from '../utils';


export default function WatchlistPage() {
  const navigate = useNavigate();
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);

  useEffect(() => {
    setWatchlist(getWatchlist());
  }, []);

  const handleRemove = (id: string) => {
    removeFromWatchlist(id);
    setWatchlist(getWatchlist());
  };

  const handleAnalysis = (stockId: string, stockName: string) => {
    navigate(`/analysis/single-stock?stock_id=${stockId}&stock_name=${encodeURIComponent(stockName)}`);
  };

  return (
    <div className="p-4 space-y-6 pb-32">
      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">观察列表</h2>
        <p className="text-sm text-stone-400">跟踪值得持续关注的股票。</p>
      </div>

      <Link
        to="/stock/search?callback=/watchlist"
        className="w-full py-4 bg-white border border-stone-200 rounded-2xl flex items-center justify-center gap-2 font-semibold text-stone-700 hover:bg-stone-50 active:scale-[0.98] transition-all"
      >
        <Search size={20} />
        添加股票到观察列表
      </Link>

      {watchlist.length > 0 ? (
        <div className="space-y-4">
          {watchlist.map((item) => (
            <div key={item.id} className="bg-white rounded-2xl p-4 border border-stone-100 flex items-center justify-between group">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center">
                    <Search size={20} className="text-blue-600" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-bold text-lg text-stone-900 truncate">{item.stock_name}</h3>
                    <p className="text-xs text-stone-400 font-mono truncate">{item.stock_id}</p>
                    {item.industry && <p className="text-[10px] text-stone-300 mt-1">{item.industry}</p>}
                    {item.focus_reason && (
                      <p className="text-xs text-stone-500 mt-1 line-clamp-1">关注理由：{item.focus_reason}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-4 mt-3 text-xs text-stone-400">
                  <span className="flex items-center gap-1">
                    <Calendar size={12} />
                    {new Date(item.added_at).toLocaleDateString()}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 ml-4">
                <button
                  onClick={() => handleAnalysis(item.stock_id, item.stock_name)}
                  className="p-2 text-stone-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  title="重新分析"
                >
                  <ChevronRight size={18} />
                </button>
                <button
                  onClick={() => handleRemove(item.id)}
                  className="p-2 text-stone-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  title="移除"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-8 flex flex-col items-center justify-center space-y-4 min-h-[60vh]">
          <div className="w-20 h-20 bg-stone-100 rounded-full flex items-center justify-center">
            <Search size={40} className="text-stone-300" />
          </div>
          <div className="text-center space-y-1">
            <p className="font-bold text-lg">观察列表为空</p>
            <p className="text-xs text-stone-400">把值得继续跟踪的股票放进来，后面会更方便复查和分析。</p>
          </div>
        </div>
      )}

      <div className="bg-amber-50 border border-amber-100 rounded-xl p-3 flex gap-3 items-start">
        <AlertCircle className="text-amber-500 shrink-0 mt-0.5" size={18} />
        <p className="text-xs text-amber-800 leading-relaxed">
          观察列表只是你的跟踪工具，不是仓位建议。请继续结合资金计划和风险承受能力使用。
        </p>
      </div>
    </div>
  );
}
