import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  AlertTriangle,
  Bell,
  BellOff,
  Calendar,
  ChevronRight,
  Clock,
  RefreshCw,
  TrendingUp,
  CheckCircle2,
} from 'lucide-react';

import { getNotifications } from '../api';
import type { NotificationItem, NotificationListResponse, NotificationSummary } from '../types';
import { cn } from '../utils';


const NOTIFICATION_TYPE_LABELS: Record<string, string> = {
  review_reminder: '复盘提醒',
  watchlist_alert: '观察池异动',
  analysis_invalidation: '结论可能失效',
  portfolio_risk: '持仓风险',
};

const NOTIFICATION_TYPE_ICONS: Record<string, React.ElementType> = {
  review_reminder: Calendar,
  watchlist_alert: TrendingUp,
  analysis_invalidation: AlertTriangle,
  portfolio_risk: AlertCircle,
};

const NOTIFICATION_TYPE_COLORS: Record<string, string> = {
  review_reminder: 'bg-amber-50 border-amber-100',
  watchlist_alert: 'bg-blue-50 border-blue-100',
  analysis_invalidation: 'bg-red-50 border-red-100',
  portfolio_risk: 'bg-amber-50 border-amber-100',
};

const NOTIFICATION_TYPE_BADGE_COLORS: Record<string, string> = {
  review_reminder: 'bg-amber-100 text-amber-700',
  watchlist_alert: 'bg-blue-100 text-blue-700',
  analysis_invalidation: 'bg-red-100 text-red-700',
  portfolio_risk: 'bg-amber-100 text-amber-700',
};

function UrgencyDot({ urgency }: { urgency: string }) {
  if (urgency === 'overdue') {
    return <span className="w-2 h-2 rounded-full bg-red-500 shrink-0" />;
  }
  if (urgency === 'high') {
    return <span className="w-2 h-2 rounded-full bg-orange-500 shrink-0" />;
  }
  if (urgency === 'due_soon') {
    return <span className="w-2 h-2 rounded-full bg-amber-400 shrink-0" />;
  }
  return null;
}


function NotificationCard({ item, onNavigate }: { item: NotificationItem; onNavigate: () => void }) {
  const Icon = NOTIFICATION_TYPE_ICONS[item.type] || Bell;
  const typeLabel = NOTIFICATION_TYPE_LABELS[item.type] || item.type;
  const typeColor = NOTIFICATION_TYPE_COLORS[item.type] || 'bg-stone-50 border-stone-100';
  const badgeColor = NOTIFICATION_TYPE_BADGE_COLORS[item.type] || 'bg-stone-100 text-stone-600';
  const isUrgent = item.urgency === 'overdue' || item.urgency === 'high';

  const handleClick = () => {
    onNavigate();
  };

  return (
    <button
      onClick={handleClick}
      className={cn(
        'w-full text-left rounded-2xl p-4 border transition-all hover:scale-[0.99] active:scale-[0.98]',
        typeColor,
        isUrgent && 'ring-1 ring-red-200',
      )}
    >
      <div className="flex items-start gap-3">
        <div className={cn(
          'w-10 h-10 rounded-xl flex items-center justify-center shrink-0',
          isUrgent ? 'bg-white' : 'bg-white/60',
        )}>
          <Icon
            size={18}
            className={
              isUrgent
                ? item.type === 'analysis_invalidation'
                  ? 'text-red-500'
                  : 'text-amber-500'
                : 'text-stone-400'
            }
          />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className={cn('px-1.5 py-0.5 rounded text-[10px] font-bold', badgeColor)}>
              {typeLabel}
            </span>
            {isUrgent && (
              <span className="px-1.5 py-0.5 bg-red-100 text-red-600 rounded text-[10px] font-bold">
                {item.urgency === 'overdue' ? '已逾期' : '请关注'}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5 mb-1">
            <UrgencyDot urgency={item.urgency} />
            <span className="text-sm font-bold text-stone-800 truncate">{item.title}</span>
          </div>
          <p className="text-xs text-stone-500 leading-relaxed line-clamp-2">{item.description}</p>
          {item.stock_name && (
            <div className="mt-2 text-[10px] text-stone-400 font-mono">
              {item.stock_id} · {item.stock_name}
            </div>
          )}
        </div>
        <ChevronRight size={16} className="text-stone-300 shrink-0 mt-1" />
      </div>
    </button>
  );
}


function SummaryBar({ summary }: { summary: NotificationSummary }) {
  const items = [
    { label: '已逾期', count: summary.overdue_count, color: 'text-red-600', bg: 'bg-red-50' },
    { label: '即将到期', count: summary.due_soon_count, color: 'text-amber-600', bg: 'bg-amber-50' },
    { label: '观察异动', count: summary.watchlist_alert_count, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: '结论预警', count: summary.invalidation_count, color: 'text-orange-600', bg: 'bg-orange-50' },
  ];

  return (
    <div className="bg-white rounded-2xl border border-stone-100 p-4">
      <div className="grid grid-cols-4 gap-2">
        {items.map((item) => (
          <div key={item.label} className={cn('rounded-xl p-3 text-center', item.bg)}>
            <div className={cn('text-xl font-bold', item.color)}>{item.count}</div>
            <div className="text-[10px] text-stone-400 mt-0.5 leading-tight">{item.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}


export default function NotificationsPage() {
  const [data, setData] = useState<NotificationListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const result = await getNotifications();
        if (!cancelled) {
          setData(result);
          setError(null);
        }
      } catch {
        if (!cancelled) {
          setError('加载提醒失败，请稍后重试');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();
    return () => { cancelled = true; };
  }, []);

  const handleNavigate = (item: NotificationItem) => {
    if (item.action_url) {
      navigate(item.action_url);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex flex-col items-center justify-center space-y-4 min-h-[60vh]">
        <div className="w-10 h-10 border-4 border-stone-200 border-t-ink rounded-full animate-spin" />
        <p className="text-sm text-stone-400">正在加载提醒...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 min-h-[60vh] flex flex-col items-center justify-center space-y-4">
        <AlertCircle className="text-red-400" size={40} />
        <p className="text-sm text-stone-500">{error || '加载提醒失败'}</p>
        <button
          onClick={() => window.location.reload()}
          className="flex items-center gap-2 px-4 py-2 bg-ink text-white rounded-xl text-sm font-medium"
        >
          <RefreshCw size={14} />
          重试
        </button>
      </div>
    );
  }

  const { notifications, summary } = data;

  return (
    <div className="p-4 space-y-6 pb-24">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">提醒中心</h1>
          <p className="text-xs text-stone-400 mt-0.5">
            {summary.total === 0
              ? '暂无待处理提醒'
              : `${summary.total} 条提醒，${summary.overdue_count} 条已逾期`}
          </p>
        </div>
        {summary.overdue_count > 0 && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-red-50 border border-red-100 rounded-full">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-xs font-bold text-red-600">{summary.overdue_count} 已逾期</span>
          </div>
        )}
      </div>

      {/* 摘要 */}
      {summary.total > 0 && <SummaryBar summary={summary} />}

      {/* 风险提示 */}
      <div className="bg-stone-50 border border-stone-100 rounded-xl p-3 flex gap-3 items-start">
        <AlertCircle className="text-stone-400 shrink-0 mt-0.5" size={14} />
        <p className="text-[11px] text-stone-500 leading-relaxed">
          提醒仅供辅助参考，不构成投资建议。所有决策请结合自身资金计划和风险承受能力判断。
        </p>
      </div>

      {/* 提醒列表 */}
      {notifications.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 space-y-4">
          <div className="w-16 h-16 bg-stone-100 rounded-full flex items-center justify-center">
            <BellOff size={28} className="text-stone-300" />
          </div>
          <div className="text-center space-y-1">
            <p className="text-sm font-medium text-stone-500">暂无待处理提醒</p>
            <p className="text-xs text-stone-400">保持分析习惯，复盘和观察都会在这里提醒你</p>
          </div>
          <Link
            to="/"
            className="mt-2 px-4 py-2 bg-ink text-white rounded-xl text-sm font-medium"
          >
            回到首页
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {/* 按类型分组 */}
          {(['review_reminder', 'watchlist_alert', 'analysis_invalidation', 'portfolio_risk'] as const).map((type) => {
            const items = notifications.filter((n) => n.type === type);
            if (items.length === 0) return null;

            const Icon = NOTIFICATION_TYPE_ICONS[type];
            const label = NOTIFICATION_TYPE_LABELS[type];
            const badgeColor = NOTIFICATION_TYPE_BADGE_COLORS[type];

            return (
              <div key={type} className="space-y-2">
                <div className="flex items-center gap-2 px-1">
                  <Icon size={14} className="text-stone-400" />
                  <span className="text-[10px] font-bold text-stone-400 uppercase tracking-widest">
                    {label}
                  </span>
                  <span className={cn('px-1.5 py-0.5 rounded text-[10px] font-bold', badgeColor)}>
                    {items.length}
                  </span>
                </div>
                <div className="space-y-2">
                  {items.map((item) => (
                    <React.Fragment key={item.id}>
                      <NotificationCard
                        item={item}
                        onNavigate={() => handleNavigate(item)}
                      />
                    </React.Fragment>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
