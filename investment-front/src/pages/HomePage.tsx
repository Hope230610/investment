import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  ArrowRight,
  Bell,
  CalendarCheck,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  Clock3,
  History,
  PieChart,
  Search,
  ShieldCheck,
  Star,
  UserCircle,
} from 'lucide-react';

import { apiGet, getNotificationSummary, getPortfolioOverview, getWatchlistItems } from '../api';
import type {
  AnalysisRecord,
  NotificationItem,
  NotificationSummary,
  PortfolioOverview,
  ReviewTask,
  UserProfile,
  WatchlistApiItem,
} from '../types';
import { SCENARIOS, cn, computeUnfinishedReviews, sortUnfinishedReviews } from '../utils';

type IconType = React.ComponentType<{ size?: number; className?: string }>;

function SectionHeader({
  title,
  action,
  to,
  icon: Icon,
}: {
  title: string;
  action?: string;
  to?: string;
  icon?: IconType;
}) {
  return (
    <div className="flex items-center justify-between gap-3 px-1">
      <div className="flex min-w-0 items-center gap-2">
        {Icon && <Icon size={15} className="shrink-0 text-teal-700" />}
        <h2 className="section-kicker truncate text-stone-400">{title}</h2>
      </div>
      {to && action && (
        <Link to={to} className="shrink-0 text-xs font-semibold text-teal-700">
          {action}
        </Link>
      )}
    </div>
  );
}

function EmptyState({
  title,
  description,
  to,
  action,
}: {
  title: string;
  description: string;
  to?: string;
  action?: string;
}) {
  const content = (
    <div className="rounded-3xl border border-dashed border-stone-200 bg-white/55 p-5 text-center">
      <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-2xl bg-stone-100 text-stone-400">
        <CheckCircle2 size={18} />
      </div>
      <p className="mt-3 text-sm font-semibold text-stone-800">{title}</p>
      <p className="mt-1 text-xs leading-relaxed text-stone-500">{description}</p>
      {action && <div className="mt-3 text-xs font-semibold text-teal-700">{action}</div>}
    </div>
  );

  return to ? <Link to={to}>{content}</Link> : content;
}

export default function HomePage() {
  const [records, setRecords] = useState<AnalysisRecord[]>([]);
  const [reviews, setReviews] = useState<ReviewTask[]>([]);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistApiItem[]>([]);
  const [notificationSummary, setNotificationSummary] = useState<NotificationSummary | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioOverview | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadHomeData = async () => {
      const [recordsResult, reviewsResult, profileResult, notifResult, portfolioResult] = await Promise.allSettled([
        apiGet<AnalysisRecord[]>('/api/v1/analysis'),
        apiGet<ReviewTask[]>('/api/v1/reviews'),
        apiGet<UserProfile>('/api/v1/user/profile'),
        getNotificationSummary(),
        getPortfolioOverview(),
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

      if (notifResult.status === 'fulfilled') {
        setNotificationSummary(notifResult.value);
      }

      if (portfolioResult.status === 'fulfilled') {
        setPortfolio(portfolioResult.value);
      }
    };

    loadHomeData().catch(() => {});
    getWatchlistItems()
      .then(setWatchlist)
      .catch(() => setWatchlist([]));

    return () => {
      cancelled = true;
    };
  }, []);

  const pendingReviews = sortUnfinishedReviews(computeUnfinishedReviews(reviews));
  const notifications = notificationSummary
    ? { summary: notificationSummary, notifications: [] as NotificationItem[] }
    : null;
  const reminderTotal = notificationSummary
    ? notificationSummary.overdue_count + notificationSummary.due_soon_count
    : 0;
  const recentRecord = records[0];
  const nextReview = pendingReviews[0];

  return (
    <div className="space-y-5 px-4 py-5">
      <section
        className="relative overflow-hidden rounded-[30px] border border-white/80 bg-white/85 p-5 shadow-[0_18px_50px_rgba(23,33,31,0.08)]"
      >
        <div className="absolute -right-12 -top-14 h-40 w-40 rounded-full bg-teal-100/70" />
        <div className="absolute right-8 top-12 h-16 w-16 rounded-full border border-amber-200/80" />
        <div className="relative space-y-5">
          <div className="space-y-2">
            <div className="section-kicker text-teal-700">PCG 校园 AI 产品创意大赛 Demo</div>
            <h1 className="text-3xl font-bold leading-tight tracking-tight text-stone-950">
              AI 金融素养教练
            </h1>
            <p className="max-w-sm text-sm leading-relaxed text-stone-600">
              面向大学生的学习与决策工作台，在大额消费和金融产品选择前先做一次冷静自检。
            </p>
          </div>

          <div className="rounded-3xl border border-stone-100 bg-mist/80 p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-teal-700 text-white">
                <ShieldCheck size={19} />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-bold text-stone-900">下一步：先完成 3 分钟消费自检</p>
                <p className="mt-0.5 text-xs leading-relaxed text-stone-500">
                  生成决策卡、风险提示和复盘任务，不替你做购买、借贷或资金安排。
                </p>
              </div>
            </div>
            <div className="mt-4 flex flex-col gap-2 sm:flex-row">
              <Link to="/analysis/pre-trade" className="primary-action flex-1">
                开始消费自检 Demo
                <ArrowRight size={16} />
              </Link>
              <Link
                to="/records"
                className="inline-flex flex-1 items-center justify-center gap-2 rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm font-bold text-stone-700 transition-all hover:bg-stone-50 active:scale-[0.98]"
              >
                看最近决策卡
              </Link>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2">
            {[
              { label: '对象', value: '大学生' },
              { label: '边界', value: '不荐股' },
              { label: '闭环', value: '复盘成长' },
            ].map((item) => (
              <div key={item.label} className="rounded-2xl bg-stone-50/90 px-3 py-2">
                <div className="text-[10px] font-bold text-stone-400">{item.label}</div>
                <div className="mt-0.5 text-sm font-bold text-stone-900">{item.value}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Link to="/reviews" className="rounded-3xl border border-stone-100 bg-white/75 p-4 transition-all hover:bg-white active:scale-[0.99]">
          <div className="flex items-center justify-between">
            <Clock3 size={17} className="text-amber-600" />
            <span className="text-2xl font-bold text-stone-900">{pendingReviews.length}</span>
          </div>
          <div className="mt-2 text-xs font-semibold text-stone-700">待复盘</div>
          <div className="mt-0.5 truncate text-[10px] text-stone-400">
            {nextReview ? `${new Date(nextReview.review_at).toLocaleDateString()} 到期` : '暂无紧急事项'}
          </div>
        </Link>
        <Link to="/notifications" className="rounded-3xl border border-stone-100 bg-white/75 p-4 transition-all hover:bg-white active:scale-[0.99]">
          <div className="flex items-center justify-between">
            <Bell size={17} className="text-teal-700" />
            <span className="text-2xl font-bold text-stone-900">{reminderTotal}</span>
          </div>
          <div className="mt-2 text-xs font-semibold text-stone-700">今日提醒</div>
          <div className="mt-0.5 text-[10px] text-stone-400">只提醒需要重新看一眼的事</div>
        </Link>
        <Link to={recentRecord ? `/analysis/${recentRecord.id}/result` : '/analysis/pre-trade'} className="rounded-3xl border border-stone-100 bg-white/75 p-4 transition-all hover:bg-white active:scale-[0.99]">
          <div className="flex items-center justify-between">
            <ClipboardList size={17} className="text-stone-500" />
            <span className="text-2xl font-bold text-stone-900">{records.length}</span>
          </div>
          <div className="mt-2 text-xs font-semibold text-stone-700">决策卡</div>
          <div className="mt-0.5 truncate text-[10px] text-stone-400">
            {recentRecord ? recentRecord.stock_name || recentRecord.stock_id : '先生成第一张'}
          </div>
        </Link>
      </section>

      <section className="soft-card rounded-[28px] p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 space-y-1">
            <div className="section-kicker text-teal-700">主 Demo</div>
            <h2 className="text-xl font-bold leading-snug text-stone-950">小林想分期买 5999 元手机</h2>
            <p className="text-sm leading-relaxed text-stone-600">
              大一新生，每月生活费 2000 元，本月已花 1500 元。因为同学都换新机而心动，先看看这次分期是否越过预算边界。
            </p>
          </div>
          <div className="hidden h-16 w-16 shrink-0 items-center justify-center rounded-[24px] bg-clay text-amber-800 sm:flex">
            <CalendarCheck size={26} />
          </div>
        </div>

        <div className="mt-5 rounded-3xl bg-stone-50/90 p-4">
          <div className="flex items-center justify-between text-xs text-stone-500">
            <span>本月生活费使用</span>
            <span className="font-mono font-semibold text-stone-800">1500 / 2000</span>
          </div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-white">
            <div className="h-full w-3/4 rounded-full bg-teal-700" />
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
            {[
              { label: '计划分期', value: '12 期' },
              { label: '每期约', value: '500 元' },
              { label: '触发原因', value: '同学都换新机' },
              { label: '当前情绪', value: '5 / 5' },
            ].map((item) => (
              <div key={item.label} className="rounded-2xl bg-white px-3 py-2">
                <div className="font-bold text-stone-400">{item.label}</div>
                <div className="mt-1 font-semibold text-stone-900">{item.value}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {['冲动消费', '盲目跟风', '预算透支', '分期依赖'].map((tag) => (
            <span key={tag} className="rounded-full border border-amber-100 bg-amber-50 px-3 py-1 text-[10px] font-bold text-amber-700">
              {tag}
            </span>
          ))}
        </div>

        <div className="mt-4 rounded-2xl border border-amber-100 bg-amber-50/70 p-3 flex gap-3 items-start">
          <AlertCircle className="mt-0.5 shrink-0 text-amber-600" size={18} />
          <p className="text-xs leading-relaxed text-amber-900">
            当前使用模拟数据演示闭环，未真实调用外部 PCG API；后续由腾讯财经提供风险教育数据，微信 / QQ 承接校园提醒与分享入口，腾讯云承载部署和模型服务。
          </p>
        </div>
      </section>

      <section className="space-y-3">
        <SectionHeader title="现在可以做什么" icon={ShieldCheck} />
        <div className="space-y-2">
          {Object.entries(SCENARIOS).map(([key, scenario]) => {
            const Icon = key === 'single_stock_check' ? Search : key === 'pre_trade_check' ? ShieldCheck : History;
            const meta = key === 'pre_trade_check' ? '3 分钟' : key === 'post_trade_review' ? '复盘' : '观察';
            return (
              <Link
                key={key}
                to={scenario.path}
                className="group flex items-center justify-between rounded-3xl border border-stone-100 bg-white/80 p-4 transition-all hover:bg-white hover:shadow-sm active:scale-[0.99]"
              >
                <div className="flex min-w-0 items-center gap-4">
                  <div className={cn('flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl', scenario.color)}>
                    <Icon size={23} />
                  </div>
                  <div className="min-w-0">
                    <h3 className="truncate text-base font-bold text-stone-950">{scenario.title}</h3>
                    <p className="truncate text-xs text-stone-500">{scenario.description}</p>
                  </div>
                </div>
                <div className="ml-3 flex shrink-0 items-center gap-2 text-xs font-semibold text-stone-400 group-hover:text-teal-700">
                  {meta}
                  <ChevronRight size={15} />
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {profile && (
        <Link to="/profile" className="block rounded-3xl border border-stone-100 bg-white/80 p-4 transition-all hover:bg-white active:scale-[0.99]">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-2">
              <UserCircle size={20} className="shrink-0 text-teal-700" />
              <span className="truncate font-semibold">用户画像摘要</span>
            </div>
            <span className="shrink-0 text-xs font-medium text-teal-700">编辑画像</span>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full bg-stone-100 px-2.5 py-1 text-[10px] font-medium text-stone-600">
              承受能力：
              {profile.risk_tolerance === 'low'
                ? '低'
                : profile.risk_tolerance === 'medium'
                  ? '中'
                  : '高'}
            </span>
            <span className="rounded-full bg-stone-100 px-2.5 py-1 text-[10px] font-medium text-stone-600">
              规划周期：
              {profile.holding_horizon === 'short'
                ? '短期'
                : profile.holding_horizon === 'medium'
                  ? '中期'
                  : '长期'}
            </span>
            {profile.behavior_tags.map((tag) => (
              <span key={tag} className="rounded-full bg-mist px-2.5 py-1 text-[10px] font-medium text-teal-700">
                {tag === 'chasing_rise'
                  ? '盲目跟风'
                  : tag === 'panic_sell'
                    ? '过度焦虑'
                    : tag === 'frequent_trading'
                      ? '分期依赖'
                      : '预算纪律稳定'}
              </span>
            ))}
          </div>
        </Link>
      )}

      {portfolio && portfolio.summary.holding_count > 0 && (
        <Link to="/portfolio" className="block rounded-3xl border border-stone-100 bg-white/80 p-4 transition-all hover:bg-white active:scale-[0.99]">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <PieChart size={20} className="text-teal-700" />
              <span className="font-semibold">预算目标概览</span>
            </div>
            <span className="text-xs font-medium text-teal-700">查看预算</span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div className="rounded-2xl bg-stone-50 p-3">
              <div className="text-[10px] text-stone-400">已规划金额</div>
              <div className="mt-1 text-sm font-bold">¥{portfolio.summary.total_market_value.toFixed(0)}</div>
            </div>
            <div className="rounded-2xl bg-stone-50 p-3">
              <div className="text-[10px] text-stone-400">预算偏差</div>
              <div className={cn('mt-1 text-sm font-bold', portfolio.summary.total_unrealized_pnl >= 0 ? 'text-amber-700' : 'text-teal-700')}>
                ¥{portfolio.summary.total_unrealized_pnl.toFixed(0)}
              </div>
            </div>
            <div className="rounded-2xl bg-stone-50 p-3">
              <div className="text-[10px] text-stone-400">最大目标占比</div>
              <div className="mt-1 text-sm font-bold">{(portfolio.summary.max_position_weight * 100).toFixed(1)}%</div>
            </div>
          </div>
          {portfolio.summary.concentration_alert && (
            <p className="mt-3 line-clamp-2 text-xs text-amber-700">{portfolio.summary.concentration_alert}</p>
          )}
        </Link>
      )}

      {notifications && notifications.summary.total > 0 && (
        <section className="space-y-3">
          <SectionHeader title="今日关注" action={`查看全部 (${notifications.summary.total})`} to="/notifications" icon={Bell} />
          <div className="rounded-3xl border border-stone-100 bg-white/80 p-3">
            <div className="grid grid-cols-4 gap-2">
              {[
                { label: '已逾期', value: notifications.summary.overdue_count, active: notifications.summary.overdue_count > 0, tone: 'rose' },
                { label: '即将到期', value: notifications.summary.due_soon_count, active: notifications.summary.due_soon_count > 0, tone: 'amber' },
                { label: '观察提醒', value: notifications.summary.watchlist_alert_count, active: notifications.summary.watchlist_alert_count > 0, tone: 'teal' },
                { label: '结论预警', value: notifications.summary.invalidation_count, active: notifications.summary.invalidation_count > 0, tone: 'stone' },
              ].map((item) => (
                <div
                  key={item.label}
                  className={cn(
                    'rounded-2xl p-2 text-center',
                    !item.active && 'bg-stone-50 text-stone-400',
                    item.active && item.tone === 'rose' && 'bg-rose-50 text-rose-700',
                    item.active && item.tone === 'amber' && 'bg-amber-50 text-amber-700',
                    item.active && item.tone === 'teal' && 'bg-mist text-teal-700',
                    item.active && item.tone === 'stone' && 'bg-stone-100 text-stone-700',
                  )}
                >
                  <div className="text-lg font-bold">{item.value}</div>
                  <div className="text-[10px] font-medium opacity-70">{item.label}</div>
                </div>
              ))}
            </div>
          </div>

          {notifications.notifications.length > 0 && (
            <div className="space-y-2">
              {notifications.notifications.slice(0, 3).map((item: NotificationItem) => (
                <Link
                  key={item.id}
                  to={item.action_url || '/notifications'}
                  className="block rounded-2xl border border-stone-100 bg-white/80 p-3 transition-colors hover:bg-white"
                >
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-teal-700" />
                    <span className="truncate text-sm font-semibold">{item.title}</span>
                  </div>
                  <p className="line-clamp-1 text-xs text-stone-500">{item.description}</p>
                </Link>
              ))}
            </div>
          )}
        </section>
      )}

      <section className="space-y-3">
        <SectionHeader title="财务观察事项" action={watchlist.length > 0 ? `查看全部 (${watchlist.length})` : undefined} to={watchlist.length > 0 ? '/watchlist' : undefined} icon={Star} />
        {watchlist.length > 0 ? (
          <div className="space-y-2">
            {watchlist.slice(0, 3).map((item) => (
              <Link
                key={item.id}
                to={`/analysis/single-stock?stock_id=${item.stock_id}&stock_name=${encodeURIComponent(item.stock_name)}`}
                className="block rounded-2xl border border-stone-100 bg-white/80 p-3 transition-colors hover:bg-white"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold">{item.stock_name}</div>
                    <div className="mt-0.5 font-mono text-[10px] text-stone-400">{item.stock_id}</div>
                    {item.focus_reason && (
                      <div className="mt-1 line-clamp-1 text-[10px] text-stone-400">理由：{item.focus_reason}</div>
                    )}
                  </div>
                  <Star size={16} className="shrink-0 fill-amber-400 text-amber-400" />
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <EmptyState
            title="观察清单是空的"
            description="把需要后续核对的预算目标或金融产品放进这里。"
            to="/stock/search"
            action="添加观察事项"
          />
        )}
      </section>

      <section className="space-y-3">
        <SectionHeader title="待复盘提醒" action={pendingReviews.length > 0 ? '查看全部' : undefined} to={pendingReviews.length > 0 ? '/reviews' : undefined} icon={Clock3} />
        {pendingReviews.length > 0 ? (
          <div className="space-y-2">
            {pendingReviews.slice(0, 2).map((review) => {
              const isExpired = review.status === 'expired';
              const overdueDays = isExpired
                ? Math.ceil((Date.now() - new Date(review.review_at).getTime()) / (1000 * 60 * 60 * 24))
                : 0;
              return (
                <Link
                  key={review.id}
                  to={`/analysis/post-trade?stock_id=${review.stock_id || ''}&stock_name=${encodeURIComponent(review.stock_name)}`}
                  className={cn(
                    'block rounded-2xl border p-3 transition-colors hover:bg-white',
                    isExpired
                      ? 'border-amber-200 bg-amber-50/80'
                      : 'border-stone-100 bg-white/80',
                  )}
                >
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-semibold">{review.stock_name}</span>
                    {isExpired && (
                      <span className="shrink-0 rounded-full bg-white px-2 py-0.5 text-[10px] font-bold text-amber-700">
                        已逾期 {overdueDays} 天
                      </span>
                    )}
                  </div>
                  <div className="mt-0.5 text-[10px] text-stone-500">
                    {new Date(review.review_at).toLocaleDateString()} 到期
                  </div>
                </Link>
              );
            })}
          </div>
        ) : (
          <EmptyState
            title="暂无待复盘任务"
            description="新的决策卡会自动给出复盘时间，方便之后回看判断质量。"
          />
        )}
      </section>

      <section className="space-y-3">
        <SectionHeader title="最近决策卡" action={records.length > 0 ? '查看历史' : undefined} to={records.length > 0 ? '/records' : undefined} icon={ClipboardList} />
        {records.length > 0 ? (
          <div className="space-y-2">
            {records.slice(0, 3).map((record) => (
              <Link
                key={record.id}
                to={`/analysis/${record.id}/result`}
                className="block rounded-2xl border border-stone-100 bg-white/80 p-3 transition-colors hover:bg-white"
              >
                <div className="mb-1 flex items-center justify-between gap-3">
                  <span className="truncate text-sm font-bold">{record.stock_name || record.stock_id}</span>
                  <span className="shrink-0 rounded-full bg-stone-100 px-2 py-0.5 text-[10px] font-bold text-stone-500">
                    {SCENARIOS[record.scenario]?.title}
                  </span>
                </div>
                <p className="line-clamp-1 text-xs text-stone-500">{record.headline}</p>
              </Link>
            ))}
          </div>
        ) : (
          <EmptyState
            title="还没有决策卡"
            description="先完成一次消费自检或风险评估，系统会把判断、证据和复盘时间整理好。"
            to="/analysis/pre-trade"
            action="生成第一张决策卡"
          />
        )}
      </section>
    </div>
  );
}
