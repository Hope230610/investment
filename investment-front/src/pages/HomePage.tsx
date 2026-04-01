import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, History, Search, ShieldCheck, Star, UserCircle } from 'lucide-react';

import { apiGet } from '../api';
import type { AnalysisRecord, ReviewTask, UserProfile, WatchlistItem } from '../types';
import { getWatchlist, SCENARIOS } from '../utils';


export default function HomePage() {
  const [records, setRecords] = useState<AnalysisRecord[]>([]);
  const [reviews, setReviews] = useState<ReviewTask[]>([]);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);

  useEffect(() => {
    let cancelled = false;

    const loadHomeData = async () => {
      const [recordsResult, reviewsResult, profileResult] = await Promise.allSettled([
        apiGet<AnalysisRecord[]>('/api/v1/records'),
        apiGet<ReviewTask[]>('/api/v1/reviews'),
        apiGet<UserProfile>('/api/v1/user/profile'),
      ]);

      if (cancelled) {
        return;
      }

      if (recordsResult.status === 'fulfilled') {
        setRecords(recordsResult.value);
      }

      if (reviewsResult.status === 'fulfilled') {
        setReviews(reviewsResult.value);
      }

      if (profileResult.status === 'fulfilled') {
        setProfile(profileResult.value);
      }
    };

    loadHomeData().catch(() => {});
    setWatchlist(getWatchlist());

    return () => {
      cancelled = true;
    };
  }, []);

  const pendingReviews = reviews.filter((item) => item.status === 'pending');

  return (
    <div className="p-4 space-y-6">
      <div className="bg-amber-50 border border-amber-100 rounded-xl p-3 flex gap-3 items-start">
        <AlertCircle className="text-amber-500 shrink-0 mt-0.5" size={18} />
        <p className="text-xs text-amber-800 leading-relaxed">
          系统提供的是“结构化辅助判断”，不是直接买卖建议。所有结论都应和你自己的资金计划一起使用。
        </p>
      </div>

      {profile && (
        <Link to="/profile" className="block bg-white rounded-2xl p-4 border border-stone-100 card-shadow">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <UserCircle size={20} className="text-stone-400" />
              <span className="font-semibold">用户画像摘要</span>
            </div>
            <span className="text-xs text-stone-400">编辑画像</span>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className="px-2 py-1 bg-stone-100 rounded-md text-[10px] font-medium uppercase tracking-wider">
              风险：
              {profile.risk_tolerance === 'low'
                ? '低'
                : profile.risk_tolerance === 'medium'
                  ? '中'
                  : '高'}
            </span>
            <span className="px-2 py-1 bg-stone-100 rounded-md text-[10px] font-medium uppercase tracking-wider">
              周期：
              {profile.holding_horizon === 'short'
                ? '短期'
                : profile.holding_horizon === 'medium'
                  ? '中期'
                  : '长期'}
            </span>
            {profile.behavior_tags.map((tag) => (
              <span key={tag} className="px-2 py-1 bg-blue-50 text-blue-600 rounded-md text-[10px] font-medium uppercase tracking-wider">
                {tag === 'chasing_rise'
                  ? '追涨倾向'
                  : tag === 'panic_sell'
                    ? '恐慌卖出'
                    : tag === 'frequent_trading'
                      ? '频繁交易'
                      : '纪律稳定'}
              </span>
            ))}
          </div>
        </Link>
      )}

      <div className="grid grid-cols-1 gap-3">
        {Object.entries(SCENARIOS).map(([key, scenario]) => {
          const Icon = key === 'single_stock_check' ? Search : key === 'pre_trade_check' ? ShieldCheck : History;
          return (
            <Link
              key={key}
              to={scenario.path}
              className="bg-white rounded-2xl p-4 border border-stone-100 card-shadow flex items-center justify-between group active:scale-[0.98] transition-all"
            >
              <div className="flex items-center gap-4">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${scenario.color}`}>
                  <Icon size={24} />
                </div>
                <div>
                  <h3 className="font-bold text-base">{scenario.title}</h3>
                  <p className="text-xs text-stone-400">{scenario.description}</p>
                </div>
              </div>
            </Link>
          );
        })}
      </div>

      {watchlist.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h2 className="font-bold text-sm uppercase tracking-widest text-stone-400">观察列表</h2>
            <Link to="/watchlist" className="text-xs text-blue-600 font-medium">
              查看全部 ({watchlist.length})
            </Link>
          </div>
          <div className="space-y-2">
            {watchlist.slice(0, 3).map((item) => (
              <Link
                key={item.id}
                to={`/analysis/single-stock?stock_id=${item.stock_id}&stock_name=${encodeURIComponent(item.stock_name)}`}
                className="block bg-white rounded-xl p-3 border border-stone-100 hover:border-stone-200 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-sm">{item.stock_name}</div>
                    <div className="text-[10px] text-stone-400 mt-0.5 font-mono">{item.stock_id}</div>
                    {item.focus_reason && (
                      <div className="text-[10px] text-stone-300 mt-1 line-clamp-1">理由：{item.focus_reason}</div>
                    )}
                  </div>
                  <Star size={16} className="text-yellow-500 fill-yellow-500" />
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {pendingReviews.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h2 className="font-bold text-sm uppercase tracking-widest text-stone-400">待复盘提醒</h2>
            <Link to="/reviews" className="text-xs text-blue-600 font-medium">
              查看全部
            </Link>
          </div>
          <div className="space-y-2">
            {pendingReviews.slice(0, 2).map((review) => (
              <Link
                key={review.id}
                to={`/analysis/post-trade?stock_id=${review.stock_id || ''}&stock_name=${encodeURIComponent(review.stock_name)}`}
                className="block bg-white rounded-xl p-3 border border-stone-100"
              >
                <div className="font-semibold text-sm">{review.stock_name}</div>
                <div className="text-[10px] text-stone-400 mt-0.5">
                  {new Date(review.review_at).toLocaleDateString()} 到期
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <h2 className="font-bold text-sm uppercase tracking-widest text-stone-400">最近分析</h2>
          <Link to="/records" className="text-xs text-blue-600 font-medium">
            查看历史
          </Link>
        </div>
        <div className="space-y-2">
          {records.slice(0, 3).map((record) => (
            <Link
              key={record.id}
              to={`/analysis/${record.id}/result`}
              className="block bg-white rounded-xl p-3 border border-stone-100 hover:border-stone-200 transition-colors"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-sm">{record.stock_name || record.stock_id}</span>
                <span className="text-[10px] font-bold text-stone-300 uppercase tracking-tighter">
                  {SCENARIOS[record.scenario]?.title}
                </span>
              </div>
              <p className="text-xs text-stone-500 line-clamp-1">{record.headline}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
