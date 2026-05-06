import React, { useState } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { AlertCircle, CheckCircle2, ChevronRight, Search, XCircle } from 'lucide-react';

import { apiPost } from '../api';
import { cn } from '../utils';
import type { ReviewFormData } from '../utils/learningFeedback';


const behaviorPatternOptions = [
  '冲动消费',
  '盲目跟风',
  '分期依赖',
  '预算纪律稳定',
  '计划执行偏差',
  '情绪主导决策',
];


export default function PostTradeInput() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const stockId = searchParams.get('stock_id') || '';
  const stockName = searchParams.get('stock_name') || '';
  const pendingReviewTaskId = searchParams.get('pending_review_task_id') || '';

  const [action, setAction] = useState('');
  const [outcome, setOutcome] = useState('');
  const [deviation, setDeviation] = useState<boolean | null>(null);
  const [judgementQuality, setJudgementQuality] = useState('');
  const [emotionLevel, setEmotionLevel] = useState(3);
  const [behaviorPatterns, setBehaviorPatterns] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleBehaviorPattern = (pattern: string) => {
    setBehaviorPatterns((current) =>
      current.includes(pattern)
        ? current.filter((item) => item !== pattern)
        : [...current, pattern]
    );
  };

  const handleSubmit = async () => {
    if (!stockId || !action.trim() || !outcome.trim() || submitting) return;

    setSubmitting(true);
    setError(null);

    try {
      const data = await apiPost<{ id: string }>('/api/v1/analysis', {
        scenario: 'post_trade_review',
        stock_id: stockId,
        scenario_payload: {
          action_taken: action.trim(),
          outcome_summary: outcome.trim(),
          plan_deviation: deviation,
          judgement_quality: judgementQuality,
          behavior_patterns: behaviorPatterns,
          emotion_level: emotionLevel,
          stock_name: stockName || undefined,
          // 如果是从 ReviewsPage 入口来的，携带原始 review task UUID
          pending_review_task_id: pendingReviewTaskId || undefined,
        },
      });

      // Pack review form data into location state so ResultPage can use it
      const reviewFormData: ReviewFormData = {
        actionTaken: action.trim(),
        outcomeSummary: outcome.trim(),
        planDeviation: deviation,
        judgementQuality,
        behaviorPatterns,
        emotionLevel,
      };

      navigate(`/analysis/${data.id}/result`, { state: { reviewFormData, pendingReviewTaskId } });
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : '创建复盘失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-4 space-y-8 pb-32">
      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">财务行为复盘</h2>
        <p className="text-sm text-stone-400">把这次消费或预算决策拆开看清楚，留下可重复的判断方法，剔除冲动和攀比。</p>
      </div>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">复盘对象</label>
        <button
          onClick={() => navigate('/stock/search?callback=/analysis/post-trade')}
          className="w-full p-4 bg-white border border-stone-200 rounded-2xl flex items-center justify-between"
        >
          {stockId ? (
            <div className="text-left">
              <div className="font-bold text-lg">{stockName}</div>
              <div className="text-xs text-stone-400 font-mono">{stockId}</div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-stone-400">
              <Search size={18} />
              <span className="text-sm">选择决策对象或预算事项</span>
            </div>
          )}
          <ChevronRight size={18} className="text-stone-300" />
        </button>
      </section>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">实际行动</label>
        <input
          type="text"
          placeholder="例如：暂缓购买 5999 元手机，或改看 3000 元以内替代方案"
          className="w-full bg-white border border-stone-200 rounded-xl p-4 text-sm focus:ring-2 focus:ring-ink"
          value={action}
          onChange={(event) => setAction(event.target.value)}
        />
      </section>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">后续结果</label>
        <textarea
          placeholder="记录本月余额变化、是否仍想购买、有没有找到替代方案，以及这次做得好的/不好的地方"
          className="w-full bg-white border border-stone-200 rounded-2xl p-4 text-sm h-28 focus:ring-2 focus:ring-ink resize-none"
          value={outcome}
          onChange={(event) => setOutcome(event.target.value)}
        />
      </section>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">是否偏离原计划</label>
        <div className="flex gap-2">
          {[
            { value: false, label: '严格执行', icon: CheckCircle2 },
            { value: true, label: '有所偏离', icon: XCircle },
          ].map((option) => (
            <button
              key={String(option.value)}
              onClick={() => setDeviation(option.value)}
              className={cn(
                'flex-1 py-3 rounded-xl border font-bold text-xs transition-all flex items-center justify-center gap-2',
                deviation === option.value
                  ? 'border-ink bg-ink text-white'
                  : 'border-stone-200 bg-white text-stone-400'
              )}
            >
              <option.icon size={16} />
              {option.label}
            </button>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">判断质量 vs 情绪</label>
        <div className="flex flex-wrap gap-2">
          {['主要来自理性判断', '部分判断 + 部分情绪', '主要来自情绪冲动', '难以区分'].map((option) => (
            <button
              key={option}
              onClick={() => setJudgementQuality(option)}
              className={cn(
                'px-4 py-2 rounded-full border text-xs font-medium transition-all',
                judgementQuality === option
                  ? 'border-ink bg-ink text-white'
                  : 'border-stone-200 bg-white text-stone-500 hover:bg-stone-50'
              )}
            >
              {option}
            </button>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-bold uppercase tracking-widest text-stone-400">当前情绪</label>
          <span className="text-xs font-bold text-stone-600">
            {emotionLevel <= 2 ? '比较冷静' : emotionLevel === 3 ? '有些波动' : '明显冲动'}
          </span>
        </div>
        <input
          aria-label="emotion level"
          type="range"
          min="1"
          max="5"
          step="1"
          className="w-full accent-ink"
          value={emotionLevel}
          onChange={(event) => setEmotionLevel(parseInt(event.target.value, 10))}
        />
        <div className="flex justify-between text-[10px] text-stone-300 font-bold uppercase tracking-tighter">
          <span>冷静</span>
          <span>中性</span>
          <span>冲动</span>
        </div>
      </section>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">行为模式识别</label>
        <div className="grid grid-cols-2 gap-2">
          {behaviorPatternOptions.map((pattern) => (
            <button
              key={pattern}
              onClick={() => toggleBehaviorPattern(pattern)}
              className={cn(
                'py-2.5 px-3 rounded-lg border text-xs font-medium transition-all text-left',
                behaviorPatterns.includes(pattern)
                  ? 'border-blue-200 bg-blue-50 text-blue-700'
                  : 'border-stone-200 bg-white text-stone-500 hover:bg-stone-50'
              )}
            >
              {pattern}
            </button>
          ))}
        </div>
      </section>

      <div className="bg-amber-50 border border-amber-100 p-4 rounded-2xl flex gap-3 items-start">
        <AlertCircle size={18} className="text-amber-500 shrink-0 mt-0.5" />
        <p className="text-xs text-amber-800 leading-relaxed">
          复盘的重点不是证明这次花没花对，而是确认下次遇到同类消费时，能不能更早看见风险。
        </p>
      </div>

      {error && (
        <div className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="pt-4">
        <button
          disabled={!stockId || !action.trim() || !outcome.trim() || submitting}
          onClick={handleSubmit}
          className="w-full py-4 bg-ink text-white rounded-2xl font-bold text-lg active:scale-[0.98] transition-all disabled:opacity-30 disabled:scale-100"
        >
          {submitting ? '分析中...' : '提交复盘'}
        </button>
      </div>
    </div>
  );
}
