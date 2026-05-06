import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Calendar, CheckCircle2, Clock } from 'lucide-react';

import { apiGet } from '../api';
import type { ReviewTask } from '../types';
import { computeOverdueDays, computeUnfinishedReviews, sortUnfinishedReviews } from '../utils';


export default function ReviewsPage() {
  const [reviews, setReviews] = useState<ReviewTask[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const loadReviews = async () => {
      try {
        const data = await apiGet<ReviewTask[]>('/api/v1/reviews');
        if (!cancelled) {
          setReviews(data);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadReviews().catch(() => {
      if (!cancelled) {
        setLoading(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  // 已完成 = 有 review_result 的记录（无论是"稍后"还是"确认"触发的）
  const pending = sortUnfinishedReviews(computeUnfinishedReviews(reviews));
  const completed = reviews.filter((task) => task.review_result != null);

  if (loading) return <div className="p-8 text-center text-stone-400">加载中...</div>;

  return (
    <div className="p-4 space-y-8">
      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">复盘任务</h2>
        <p className="text-sm text-stone-400">管理到期的复盘事项，把分析真正闭环。</p>
      </div>

      <section className="space-y-4">
        <div className="flex items-center gap-2 px-1">
          <Clock size={16} className="text-amber-500" />
          <h3 className="text-xs font-bold text-stone-400 uppercase tracking-widest">待处理 ({pending.length})</h3>
        </div>
        <div className="space-y-3">
          {pending.length > 0 ? pending.map((task) => {
            const isExpired = task.status === 'expired';
            const overdueDays = isExpired ? computeOverdueDays(task.review_at) : 0;
            return (
              <div
                key={task.id}
                className={isExpired
                  ? 'bg-white rounded-2xl p-4 border border-red-300 bg-red-50/30 card-shadow space-y-4'
                  : 'bg-white rounded-2xl p-4 border border-stone-100 card-shadow space-y-4'
                }
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="font-bold text-lg">{task.stock_name}</h4>
                    <p className="text-[10px] text-stone-400 uppercase tracking-widest mt-0.5">
                      来源：{task.scenario === 'single_stock_check' ? '金融产品风险评估' : task.scenario === 'pre_trade_check' ? '消费决策自检' : '财务行为复盘'}
                    </p>
                  </div>
                  {isExpired ? (
                    <span className="px-2 py-1 bg-red-100 text-red-600 rounded text-[10px] font-bold">
                      已逾期 {overdueDays} 天
                    </span>
                  ) : (
                    <span className="px-2 py-1 bg-amber-50 text-amber-600 rounded text-[10px] font-bold">
                      待执行
                    </span>
                  )}
                </div>
              <div className="flex items-center justify-between pt-4 border-t border-stone-50">
                <div className="flex items-center gap-2 text-stone-400">
                  <Calendar size={14} />
                  <span className="text-xs">{new Date(task.review_at).toLocaleDateString()}</span>
                </div>
                <Link
                  to={`/analysis/post-trade?stock_id=${task.stock_id || ''}&stock_name=${encodeURIComponent(task.stock_name)}&pending_review_task_id=${task.analysis_task_id}`}
                  className="px-4 py-2 bg-ink text-white rounded-xl text-xs font-bold"
                >
                  去复盘
                </Link>
              </div>
              </div>
            );
          }) : (
            <div className="p-12 text-center bg-stone-50 rounded-2xl border border-dashed border-stone-200">
              <p className="text-sm text-stone-400">暂无待复盘任务</p>
            </div>
          )}
        </div>
      </section>

      {completed.length > 0 && (
        <section className="space-y-4 opacity-60">
          <div className="flex items-center gap-2 px-1">
            <CheckCircle2 size={16} className="text-emerald-500" />
            <h3 className="text-xs font-bold text-stone-400 uppercase tracking-widest">已完成</h3>
          </div>
          <div className="space-y-2">
            {completed.map((task) => (
              <div key={task.id} className="bg-white rounded-xl p-3 border border-stone-100 flex items-center justify-between">
                <span className="font-bold text-sm">{task.stock_name}</span>
                <span className="text-[10px] text-stone-400">
                  已于 {new Date(task.updated_at).toLocaleDateString()} 完成
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
