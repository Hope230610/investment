import React, { useState } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { AlertCircle, CheckCircle2, ChevronRight, Search, XCircle } from 'lucide-react';

import { apiPost } from '../api';
import { cn } from '../utils';
import type { ReviewFormData } from '../utils/learningFeedback';


const behaviorPatternOptions = [
  '追涨倾向',
  '恐慌卖出',
  '频繁交易',
  '纪律稳定',
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
          // Pass emotion level if available from context
          emotion_level: 3,
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
        emotionLevel: 3,
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
        <h2 className="text-2xl font-bold tracking-tight">交易后复盘</h2>
        <p className="text-sm text-stone-400">把这次决策拆开看清楚，留下能重复的部分，剔除运气和情绪。</p>
      </div>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">选择股票</label>
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
              <span className="text-sm">点击搜索 A 股标的</span>
            </div>
          )}
          <ChevronRight size={18} className="text-stone-300" />
        </button>
      </section>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">实际操作</label>
        <input
          type="text"
          placeholder="例如：在 25.6 元买入 30%，或者跌破计划位后减仓"
          className="w-full bg-white border border-stone-200 rounded-xl p-4 text-sm focus:ring-2 focus:ring-ink"
          value={action}
          onChange={(event) => setAction(event.target.value)}
        />
      </section>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">后续结果</label>
        <textarea
          placeholder="记录价格变化、盈亏状态、持仓心态，或者你觉得这次做得好的/不好的地方"
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
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">判断质量 vs 运气</label>
        <div className="flex flex-wrap gap-2">
          {['主要来自判断', '部分判断 + 部分运气', '主要来自运气', '难以区分'].map((option) => (
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
          复盘的重点不是证明这次盈亏对不对，而是确认你下次还该不该重复同样的动作。
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
