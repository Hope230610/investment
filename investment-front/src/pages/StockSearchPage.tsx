import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle2, ChevronRight, Search, Star, X } from 'lucide-react';

import { apiGet } from '../api';
import type { StockSearchItem } from '../types';
import { getWatchlistItems, postWatchlistItem } from '../api';


const hotSearches = ['5999元手机分期', '3000元替代手机', '校园贷风险', '月底超支复盘'];


export default function StockSearchPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const callback = searchParams.get('callback');

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<StockSearchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [watchlistStockIds, setWatchlistStockIds] = useState<Set<string>>(new Set());
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    getWatchlistItems()
      .then((list) => setWatchlistStockIds(new Set(list.map((item) => item.stock_id))))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (query.trim().length < 1) {
      setResults([]);
      setLoading(false);
      setError(null);
      return;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setError(null);

      try {
        const data = await apiGet<{ items: StockSearchItem[] }>(
          `/api/v1/stocks/search?q=${encodeURIComponent(query.trim())}&limit=12`,
          { signal: controller.signal },
        );
        setResults(data.items || []);
      } catch (searchError) {
        if (controller.signal.aborted) return;
        setResults([]);
        setError(searchError instanceof Error ? searchError.message : '搜索失败');
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }, 300);

    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [query]);

  const handleSelect = async (stock: StockSearchItem) => {
    if (callback === '/watchlist') {
      try {
        await postWatchlistItem({ stock_id: stock.stock_id });
        setWatchlistStockIds((prev) => new Set([...prev, stock.stock_id]));
      } catch {
        // 静默失败
      }
      navigate('/watchlist');
      return;
    }

    if (callback) {
      navigate(`${callback}?stock_id=${stock.stock_id}&stock_name=${encodeURIComponent(stock.stock_name)}`);
      return;
    }

    navigate(-1);
  };

  const handleAddToWatchlist = async (event: React.MouseEvent, stock: StockSearchItem) => {
    event.stopPropagation();
    try {
      await postWatchlistItem({ stock_id: stock.stock_id });
      setWatchlistStockIds((prev) => new Set([...prev, stock.stock_id]));
      setToast(`已将 ${stock.stock_name} 加入观察列表`);
      window.setTimeout(() => setToast(null), 2000);
    } catch {
      setToast('添加失败，请重试');
      window.setTimeout(() => setToast(null), 2000);
    }
  };

  const isInWatchlist = (stockId: string) => watchlistStockIds.has(stockId);

  return (
    <div className="flex flex-col h-full">
      {toast && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 bg-ink text-white px-4 py-2 rounded-xl text-sm font-medium shadow-lg flex items-center gap-2">
          <CheckCircle2 size={16} />
          <span>{toast}</span>
        </div>
      )}

      <div className="p-4 bg-white border-b border-stone-100 sticky top-14 z-20">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" size={18} />
          <input
            autoFocus
            type="text"
            placeholder="搜索演示对象、消费场景或风险主题"
            className="w-full bg-stone-100 border-none rounded-xl py-3 pl-10 pr-10 text-sm focus:ring-2 focus:ring-ink"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 p-1"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-8 text-center text-stone-400 text-sm">正在搜索演示数据...</div>
        ) : error ? (
          <div className="p-8 text-center text-red-600 text-sm">{error}</div>
        ) : results.length > 0 ? (
          <div className="divide-y divide-stone-50">
            {results.map((stock) => (
              <div
                key={stock.stock_id}
                className="p-4 flex items-center justify-between hover:bg-stone-50 transition-colors"
              >
                <button
                  onClick={() => handleSelect(stock)}
                  className="flex-1 text-left"
                >
                  <div className="font-bold text-base">{stock.stock_name}</div>
                  <div className="text-xs text-stone-400 font-mono">
                    {stock.stock_id} {stock.industry ? `| ${stock.industry}` : ''}
                  </div>
                  {stock.security_type && (
                    <div className="text-[10px] text-stone-300 mt-1">{stock.security_type}</div>
                  )}
                </button>
                {callback !== '/watchlist' && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(event) => handleAddToWatchlist(event, stock)}
                      disabled={isInWatchlist(stock.stock_id)}
                      className={[
                        'p-2 rounded-lg transition-all',
                        isInWatchlist(stock.stock_id)
                          ? 'bg-yellow-100 text-yellow-600'
                          : 'text-stone-400 hover:bg-stone-100',
                      ].join(' ')}
                      title={isInWatchlist(stock.stock_id) ? '已在观察列表' : '加入观察列表'}
                    >
                      <Star
                        size={18}
                        className={isInWatchlist(stock.stock_id) ? 'fill-yellow-500' : undefined}
                      />
                    </button>
                    <button
                      onClick={() => handleSelect(stock)}
                      className="p-2 text-stone-300 hover:text-stone-500"
                    >
                      <ChevronRight size={18} />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : query ? (
          <div className="p-12 text-center text-stone-400">
            <p className="text-sm">没有找到相关对象，请换个关键词试试</p>
          </div>
        ) : (
          <div className="p-8 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-widest text-stone-300">热门搜索</h3>
            <div className="flex flex-wrap gap-2">
              {hotSearches.map((stock) => (
                <button
                  key={stock}
                  onClick={() => setQuery(stock)}
                  className="px-3 py-1.5 bg-white border border-stone-200 rounded-lg text-xs font-medium text-stone-600 hover:bg-stone-50 transition-colors"
                >
                  {stock}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
