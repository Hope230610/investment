import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

import type { FocusReason, ReviewTask } from './types';


export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}


export const SCENARIOS = {
  single_stock_check: {
    title: '单股咨询',
    description: '值得继续关注吗',
    icon: 'Search',
    color: 'bg-blue-50 text-blue-600',
    path: '/analysis/single-stock',
  },
  pre_trade_check: {
    title: '交易前自检',
    description: '检查情绪和触发逻辑',
    icon: 'ShieldCheck',
    color: 'bg-emerald-50 text-emerald-600',
    path: '/analysis/pre-trade',
  },
  post_trade_review: {
    title: '交易后复盘',
    description: '复盘执行和判断质量',
    icon: 'History',
    color: 'bg-amber-50 text-amber-700',
    path: '/analysis/post-trade',
  },
} as const;


export const EXPERIENCE_LEVELS = [
  { value: 'novice', label: '新手' },
  { value: 'intermediate', label: '中级' },
  { value: 'expert', label: '有体系投资者' },
];

export const HOLDING_HORIZONS = [
  { value: 'short', label: '短期' },
  { value: 'medium', label: '中期' },
  { value: 'long', label: '长期' },
];

export const RISK_TOLERANCES = [
  { value: 'low', label: '低' },
  { value: 'medium', label: '中' },
  { value: 'high', label: '高' },
];

export const BEHAVIOR_TAGS = [
  { value: 'chasing_rise', label: '追涨倾向' },
  { value: 'panic_sell', label: '恐慌卖出倾向' },
  { value: 'frequent_trading', label: '频繁交易' },
  { value: 'stable_discipline', label: '纪律稳定' },
];


export const STORAGE_KEYS = {
  FOCUS_REASONS: 'ai_investment_focus_reasons',
};


export const getFocusReasons = (): FocusReason[] => {
  const stored = localStorage.getItem(STORAGE_KEYS.FOCUS_REASONS);
  return stored ? JSON.parse(stored) : [];
};


export const addFocusReason = (
  reason: Omit<FocusReason, 'id' | 'created_at'>
): FocusReason => {
  const reasons = getFocusReasons();
  const newReason: FocusReason = {
    ...reason,
    id: `reason_${Date.now()}`,
    created_at: new Date().toISOString(),
  };
  reasons.push(newReason);
  localStorage.setItem(STORAGE_KEYS.FOCUS_REASONS, JSON.stringify(reasons));
  return newReason;
};


/**
 * 未完成复盘任务 = pending + expired（不含 completed）
 */
export const computeUnfinishedReviews = (reviews: ReviewTask[]) =>
  reviews.filter((t) => t.status === 'pending' || t.status === 'expired');

/**
 * 逾期天数（仅对 expired 任务有意义，pending 返回 0）
 */
export const computeOverdueDays = (reviewAt: string): number => {
  const diff = Date.now() - new Date(reviewAt).getTime();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
};

/**
 * 未完成复盘任务按紧迫程度排序：expired 前，pending 后；同状态内按 review_at 升序
 */
export const sortUnfinishedReviews = (tasks: ReviewTask[]): ReviewTask[] =>
  [...tasks].sort((a, b) => {
    if (a.status === 'expired' && b.status !== 'expired') return -1;
    if (a.status !== 'expired' && b.status === 'expired') return 1;
    return new Date(a.review_at).getTime() - new Date(b.review_at).getTime();
  });
