import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Filter, ChevronRight, Calendar } from 'lucide-react';

import { apiGet } from '../api';
import { AnalysisRecord } from '../types';
import { SCENARIOS, cn } from '../utils';

export default function RecordsPage() {
  const [records, setRecords] = useState<AnalysisRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    let cancelled = false;

    const loadRecords = async () => {
      try {
        const data = await apiGet<AnalysisRecord[]>('/api/v1/records');
        if (!cancelled) {
          setRecords(data);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadRecords().catch(() => {
      if (!cancelled) {
        setLoading(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const filteredRecords = filter === 'all' 
    ? records 
    : records.filter(r => r.scenario === filter);

  if (loading) return <div className="p-8 text-center text-stone-400">加载中...</div>;

  return (
    <div className="p-4 space-y-6">
      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">历史记录</h2>
        <p className="text-sm text-stone-400">查看过去的分析、干预与复盘行为</p>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 overflow-x-auto pb-2 no-scrollbar">
        <button
          onClick={() => setFilter('all')}
          className={cn(
            "px-4 py-2 rounded-full text-xs font-bold whitespace-nowrap transition-all",
            filter === 'all' ? "bg-ink text-white" : "bg-white border border-stone-200 text-stone-500"
          )}
        >
          全部
        </button>
        {Object.entries(SCENARIOS).map(([key, s]) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={cn(
              "px-4 py-2 rounded-full text-xs font-bold whitespace-nowrap transition-all",
              filter === key ? "bg-ink text-white" : "bg-white border border-stone-200 text-stone-500"
            )}
          >
            {s.title}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {filteredRecords.length > 0 ? filteredRecords.map(record => (
          <Link
            key={record.id}
            to={`/analysis/${record.id}/result`}
            className="block bg-white rounded-2xl p-4 border border-stone-100 card-shadow hover:border-stone-200 transition-all active:scale-[0.99]"
          >
            <div className="flex justify-between items-start mb-2">
              <div>
                <h4 className="font-bold text-base">{record.stock_name}</h4>
                <div className="flex items-center gap-2 mt-1">
                  <span className={cn(
                    "text-[10px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded",
                    record.scenario === 'single_stock_check' ? "bg-blue-50 text-blue-600" :
                    record.scenario === 'pre_trade_check' ? "bg-emerald-50 text-emerald-600" : "bg-purple-50 text-purple-600"
                  )}>
                    {SCENARIOS[record.scenario]?.title}
                  </span>
                  <span className="text-[10px] text-stone-300 font-mono">{record.stock_id}</span>
                </div>
              </div>
              <div className="text-[10px] text-stone-400 flex items-center gap-1">
                <Calendar size={10} />
                {new Date(record.created_at).toLocaleDateString()}
              </div>
            </div>
            <p className="text-sm text-stone-600 line-clamp-2 leading-relaxed">
              {record.headline}
            </p>
            <div className="mt-4 pt-4 border-t border-stone-50 flex justify-between items-center">
              <span className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest">结论有效</span>
              <ChevronRight size={14} className="text-stone-300" />
            </div>
          </Link>
        )) : (
          <div className="p-12 text-center">
            <p className="text-sm text-stone-400">暂无相关记录</p>
          </div>
        )}
      </div>
    </div>
  );
}
