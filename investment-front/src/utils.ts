import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

import type { FocusReason, ReviewTask } from './types';


export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}


export const SCENARIOS = {
  single_stock_check: {
    title: '金融产品风险评估',
    description: '拆解夸张宣传和真实风险',
    icon: 'Search',
    color: 'bg-blue-50 text-blue-600',
    path: '/analysis/single-stock',
  },
  pre_trade_check: {
    title: '消费决策自检',
    description: '分期、大额消费前先慢下来',
    icon: 'ShieldCheck',
    color: 'bg-emerald-50 text-emerald-600',
    path: '/analysis/pre-trade',
  },
  post_trade_review: {
    title: '财务行为复盘',
    description: '复盘超支和行为模式',
    icon: 'History',
    color: 'bg-amber-50 text-amber-700',
    path: '/analysis/post-trade',
  },
} as const;


export const EXPERIENCE_LEVELS = [
  { value: 'novice', label: '大一新生 / 初学者' },
  { value: 'intermediate', label: '有兼职收入学生' },
  { value: 'expert', label: '研究生 / 有规划经验' },
];

export const HOLDING_HORIZONS = [
  { value: 'short', label: '本月内' },
  { value: 'medium', label: '本学期' },
  { value: 'long', label: '一年以上' },
];

export const RISK_TOLERANCES = [
  { value: 'low', label: '低' },
  { value: 'medium', label: '中' },
  { value: 'high', label: '高' },
];

export const BEHAVIOR_TAGS = [
  { value: 'chasing_rise', label: '盲目跟风' },
  { value: 'panic_sell', label: '过度焦虑' },
  { value: 'frequent_trading', label: '分期依赖' },
  { value: 'stable_discipline', label: '预算纪律稳定' },
];


export const STORAGE_KEYS = {
  FOCUS_REASONS: 'ai_financial_literacy_focus_reasons',
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
