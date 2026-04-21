import React, { useEffect, useState, useRef } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import {
  AlertCircle,
  AlertTriangle,
  Calendar,
  CheckCircle2,
  ChevronDown,
  Clock,
  Info,
  MessageSquare,
  RefreshCw,
  ShieldAlert,
  Star,
  X,
} from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';

import { apiGet, apiPost, getLearningHistory, patchReviewResult, postLearningFeedback } from '../api';
import type { AnalysisDetail, OutputMarkType } from '../types';
import { addFocusReason, addToWatchlist, cn, getWatchlist } from '../utils';
import LearningFeedbackCard from '../components/LearningFeedbackCard';
import { computeLearningFeedback } from '../utils/learningFeedback';
import type { LearningFeedbackData } from '../components/LearningFeedbackCard';


function formatDateTime(value?: string | null) {
  if (!value) return '--';
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}


function formatDate(value?: string | null) {
  if (!value) return '--';
  return new Date(value).toLocaleDateString('zh-CN');
}


function formatPrice(value?: number | null) {
  if (value === null || value === undefined) return '--';
  return value.toFixed(2);
}


function formatPercent(value?: number | null) {
  if (value === null || value === undefined) return '--';
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}


function formatLargeNumber(value?: number | null) {
  if (value === null || value === undefined) return '--';
  if (Math.abs(value) >= 100000000) {
    return `${(value / 100000000).toFixed(2)} 亿`;
  }
  if (Math.abs(value) >= 10000) {
    return `${(value / 10000).toFixed(2)} 万`;
  }
  return value.toFixed(0);
}


const outputTagStyles: Record<OutputMarkType, string> = {
  data_fact: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  model_inference: 'bg-blue-100 text-blue-700 border-blue-200',
  uncertainty: 'bg-amber-100 text-amber-700 border-amber-200',
};

const outputTagLabels: Record<OutputMarkType, string> = {
  data_fact: '事实',
  model_inference: '推理',
  uncertainty: '不确定',
};


function OutputTag({ type }: { type: OutputMarkType }) {
  return (
    <span className={`px-2 py-1 rounded-full text-[10px] font-bold border ${outputTagStyles[type]}`}>
      {outputTagLabels[type]}
    </span>
  );
}


function ProcessingState({ stockId }: { stockId?: string }) {
  return (
    <div className="p-8 flex flex-col items-center justify-center space-y-4 min-h-[60vh]">
      <div className="w-12 h-12 border-4 border-stone-200 border-t-ink rounded-full animate-spin" />
      <div className="text-center space-y-1">
        <p className="font-bold text-lg">正在生成真实数据分析</p>
        <p className="text-xs text-stone-400">
          {stockId ? `已开始处理 ${stockId} 的最新行情、公告和公司信息...` : '正在整理行情、公告和风险提示...'}
        </p>
      </div>
    </div>
  );
}


export default function ResultPage() {
  const { id } = useParams();
  const location = useLocation();

  const [analysis, setAnalysis] = useState<AnalysisDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showExplain, setShowExplain] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [showFocusReasonModal, setShowFocusReasonModal] = useState(false);
  const [focusReason, setFocusReason] = useState('');
  const [isInWatchlist, setIsInWatchlist] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [savingReason, setSavingReason] = useState(false);

  // Learning feedback card state
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackData, setFeedbackData] = useState<LearningFeedbackData | null>(null);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [feedbackShowCount, setFeedbackShowCount] = useState(0);
  const [learningHistory, setLearningHistory] = useState<{
    emotion_history: { date: string; level: number }[];
    judgment_history: { date: string; score: number; label: string; is_hard_to_tell: boolean }[];
  } | null>(null);

  /**
   * Session-level flag: 防止"稍后"按钮点击后 effect 重新运行导致卡片又弹出。
   * useEffect 依赖 feedbackShowCount 时，点击"稍后"会触发 effect 重跑，
   * 在 timer 还未清除前就又设了新的 timer，导致卡片重新弹出。
   * 使用 ref 跟踪本次会话内是否已经主动关闭过卡片。
   */
  const feedbackSessionDismissedRef = useRef(false);

  // Retrieve review form data passed from PostTradeInput
  const reviewFormData = (location.state as { reviewFormData?: import('../utils/learningFeedback').ReviewFormData })?.reviewFormData;

  // LocalStorage keys for feedback card tracking
  const feedbackDismissKey = `feedback_dismissed_${id}`;
  const feedbackCountKey = `feedback_showcount_${id}`;

  // Check localStorage on mount — don't show if permanently dismissed
  useEffect(() => {
    if (!id) return;
    const dismissed = localStorage.getItem(feedbackDismissKey);
    if (dismissed === 'true') {
      setShowFeedback(false);
      return;
    }
    const count = parseInt(localStorage.getItem(feedbackCountKey) || '0', 10);
    setFeedbackShowCount(count);
    if (count >= 3) {
      // Max shows reached, don't auto-show
      setShowFeedback(false);
    }
  }, [id]);

  // Fetch learning history (emotion + judgment) on mount for post_trade_review
  useEffect(() => {
    if (!id) return;
    if (analysis?.scenario !== 'post_trade_review') return;

    getLearningHistory(30)
      .then(setLearningHistory)
      .catch(() => {
        // Silently fail — use empty history, UI still works with fallback
        setLearningHistory({ emotion_history: [], judgment_history: [] });
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, analysis?.scenario]);

  // Compute feedback once analysis is loaded and this is a post_trade_review
  useEffect(() => {
    if (!analysis || analysis.status !== 'ready') return;
    if (analysis.scenario !== 'post_trade_review') return;
    if (!reviewFormData) return;
    // Don't show if permanently dismissed, max shows reached, or session-dismissed
    if (feedbackSessionDismissedRef.current) return;
    const count = parseInt(localStorage.getItem(feedbackCountKey) || '0', 10);
    if (count >= 3) return;
    if (localStorage.getItem(feedbackDismissKey) === 'true') return;
    // Normalize legacy 'confirmed' value to 'true' for consistent gate semantics
    if (localStorage.getItem(feedbackDismissKey) === 'confirmed') {
      localStorage.setItem(feedbackDismissKey, 'true');
      return;
    }

    const scenarioPayload = analysis.scenario_payload ?? null;

    // Extract existing judgment scores from history (exclude is_hard_to_tell records)
    const existingJudgmentHistory = (learningHistory?.judgment_history || [])
      .filter(h => !h.is_hard_to_tell)
      .map(h => h.score);

    const computed = computeLearningFeedback(
      reviewFormData,
      scenarioPayload,
      existingJudgmentHistory,
      learningHistory?.emotion_history,
    );
    if (computed) {
      setFeedbackData(computed);
      // Show card with a slight delay so user can orient on the result first
      const timer = window.setTimeout(() => setShowFeedback(true), 800);
      return () => clearTimeout(timer);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysis, reviewFormData, learningHistory]);

  const handleFeedbackConfirm = async () => {
    if (!feedbackData || !id) return;
    setFeedbackLoading(true);
    try {
      // 1. 写入 learning feedback（画像学习）
      await postLearningFeedback({
        analysis_task_id: id,
        tag_updates: feedbackData.tagUpdates.map(t => ({
          tag: t.tag,
          type: t.type,
          source: t.source,
        })),
        judgment_quality: reviewFormData?.judgementQuality ?? '难以区分',
        emotion_level: feedbackData.currentEmotionLevel,
        intent: analysis?.scenario_payload?.intent as string | undefined,
        trigger_reason: analysis?.scenario_payload?.trigger_reason as string | undefined,
      });

      // 2. 更新 ReviewTask.review_result 并标记为已完成
      await patchReviewResult(id, {
        action_taken: reviewFormData?.actionTaken,
        outcome_summary: reviewFormData?.outcomeSummary,
        plan_deviation: reviewFormData?.planDeviation,
        judgement_quality: reviewFormData?.judgementQuality,
        behavior_patterns: reviewFormData?.behaviorPatterns,
        emotion_level: feedbackData.currentEmotionLevel,
      });

      localStorage.setItem(feedbackDismissKey, 'true');
    } catch {
      // 即使 API 失败也关闭，不阻塞用户
      localStorage.setItem(feedbackDismissKey, 'true');
    } finally {
      setFeedbackLoading(false);
      setShowFeedback(false);
    }
  };

  const handleFeedbackLater = async () => {
    // 设置 session flag，防止 effect 重跑导致卡片又弹出
    feedbackSessionDismissedRef.current = true;
    setShowFeedback(false);

    // 将 ReviewTask 标记为已完成（用户已"稍后"处理，等于承认了这次复盘）
    if (id) {
      try {
        await patchReviewResult(id, { review_result: null, mark_completed: true });
      } catch {
        // 非阻塞，localStorage 标记仍生效
      }
      const newCount = parseInt(localStorage.getItem(feedbackCountKey) || '0', 10) + 1;
      localStorage.setItem(feedbackCountKey, String(newCount));
      setFeedbackShowCount(newCount);
    }
  };

  const handleFeedbackDismiss = () => {
    // 设置 session flag + 永久跳过标记
    feedbackSessionDismissedRef.current = true;
    if (id) {
      localStorage.setItem(feedbackDismissKey, 'true');
    }
    setShowFeedback(false);
  };

  useEffect(() => {
    if (!id) {
      setError('分析记录不存在');
      setLoading(false);
      return;
    }

    let cancelled = false;
    let timer: number | undefined;

    const loadAnalysis = async () => {
      try {
        const data = await apiGet<AnalysisDetail>(`/api/v1/analysis/${id}`);
        if (cancelled) return;

        setAnalysis(data);
        setError(null);
        setLoading(false);

        if (data.status === 'processing') {
          timer = window.setTimeout(loadAnalysis, 2000);
        }
      } catch (loadError) {
        if (cancelled) return;
        setError(loadError instanceof Error ? loadError.message : '获取分析结果失败');
        setLoading(false);
      }
    };

    loadAnalysis();

    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [id]);

  useEffect(() => {
    if (!analysis?.stock_id) return;
    const watchlist = getWatchlist();
    setIsInWatchlist(watchlist.some((item) => item.stock_id === analysis.stock_id));
  }, [analysis?.stock_id]);

  const decisionCard = analysis?.decision_card;
  const quote = analysis?.stock_snapshot;
  const companyProfile = analysis?.company_profile;
  const recentEvents = analysis?.recent_events || [];
  const stockName = analysis?.stock_name || analysis?.stock_id || '分析结果';
  const stockIndustry = analysis?.stock_industry || companyProfile?.board_name || '未识别行业';
  const market = analysis?.stock_market || analysis?.stock_id.slice(0, 2) || '--';
  const validUntil = analysis?.valid_until;
  const dataAsOf = analysis?.data_as_of;
  const isExpired = validUntil ? Date.now() > new Date(validUntil).getTime() : analysis?.status === 'expired';

  const handleAddToWatchlist = () => {
    if (!analysis) return;

    addToWatchlist({
      stock_id: analysis.stock_id,
      stock_name: stockName,
      market,
      industry: stockIndustry,
    });
    setIsInWatchlist(true);
    setToastMessage(`已将 ${stockName} 加入观察列表`);
    window.setTimeout(() => setToastMessage(null), 2000);
  };

  const handleSaveFocusReason = async () => {
    if (!analysis || !focusReason.trim() || !id || savingReason) return;

    setSavingReason(true);

    try {
      const result = await apiPost<{ id: string }>(`/api/v1/analysis/${id}/record-reason`, {
        stock_id: analysis.stock_id,
        reason: focusReason.trim(),
      });

      addFocusReason({
        analysis_id: result.id,
        stock_id: analysis.stock_id,
        reason: focusReason.trim(),
      });

      addToWatchlist({
        stock_id: analysis.stock_id,
        stock_name: stockName,
        market,
        industry: stockIndustry,
        focus_reason: focusReason.trim(),
      });

      setIsInWatchlist(true);
      setShowFocusReasonModal(false);
      setFocusReason('');
      setToastMessage('已记录关注理由');
      window.setTimeout(() => setToastMessage(null), 2000);
    } catch (saveError) {
      setToastMessage(saveError instanceof Error ? saveError.message : '保存关注理由失败');
      window.setTimeout(() => setToastMessage(null), 2400);
    } finally {
      setSavingReason(false);
    }
  };

  if (loading) {
    return <ProcessingState />;
  }

  if (error) {
    return (
      <div className="p-6 min-h-[60vh] flex items-center justify-center">
        <div className="bg-white rounded-3xl border border-stone-100 p-6 shadow-sm max-w-sm w-full space-y-4 text-center">
          <div className="w-12 h-12 mx-auto rounded-full bg-red-50 flex items-center justify-center">
            <AlertCircle className="text-red-500" size={22} />
          </div>
          <div className="space-y-2">
            <h2 className="text-lg font-bold">分析结果暂时不可用</h2>
            <p className="text-sm text-stone-500 leading-relaxed">{error}</p>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="w-full py-3 bg-ink text-white rounded-2xl font-bold flex items-center justify-center gap-2"
          >
            <RefreshCw size={16} />
            重新加载
          </button>
        </div>
      </div>
    );
  }

  if (!analysis || analysis.status === 'processing' || (!decisionCard && analysis.status !== 'partial_ready')) {
    return <ProcessingState stockId={analysis?.stock_id} />;
  }

  if (analysis.status === 'failed') {
    return (
      <div className="p-6 min-h-[60vh] flex items-center justify-center">
        <div className="bg-white rounded-3xl border border-stone-100 p-6 shadow-sm max-w-sm w-full space-y-4 text-center">
          <div className="w-12 h-12 mx-auto rounded-full bg-red-50 flex items-center justify-center">
            <AlertTriangle className="text-red-500" size={22} />
          </div>
          <div className="space-y-2">
            <h2 className="text-lg font-bold">分析生成失败</h2>
            <p className="text-sm text-stone-500 leading-relaxed">
              这次没有成功拿到完整数据，建议稍后重新发起分析。
            </p>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="w-full py-3 bg-ink text-white rounded-2xl font-bold"
          >
            重新加载
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-6 pb-32">
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-20 left-1/2 -translate-x-1/2 z-50 bg-ink text-white px-4 py-2 rounded-xl text-sm font-medium shadow-lg"
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 size={16} />
              <span>{toastMessage}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="text-[10px] text-stone-400 text-center uppercase tracking-widest py-2 border-b border-stone-100">
        以下内容用于辅助判断，不构成直接投资建议
      </div>

      {analysis.status === 'partial_ready' && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-amber-50 border border-amber-100 rounded-2xl px-4 py-3 flex gap-3 items-start"
        >
          <Info size={16} className="text-amber-500 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-800 leading-relaxed">
            <span className="font-bold">部分就绪</span>：部分模块数据暂时缺失，分析结论已可用，但部分内容可能不够完整，请留意各板块的降级提示。
          </div>
        </motion.div>
      )}

      {analysis.intervention && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-red-50 border border-red-100 rounded-2xl p-4 space-y-3"
        >
          <div className="flex items-center gap-2 text-red-600">
            <ShieldAlert size={20} />
            <span className="font-bold">行为干预提醒</span>
          </div>
          <p className="text-xs text-red-800 leading-relaxed">
            系统识别到当前场景可能带有情绪化触发，建议先回答下面这些问题，再决定是否动作。
          </p>
          <div className="space-y-2">
            {analysis.intervention.questions.map((question, index) => (
              <div
                key={`${question}-${index}`}
                className="bg-white/70 p-3 rounded-xl text-xs text-red-900 border border-red-100/60"
              >
                {question}
              </div>
            ))}
          </div>
        </motion.div>
      )}

      <section className={cn(
        'bg-white rounded-3xl p-6 border border-stone-100 shadow-sm space-y-6',
        isExpired && 'opacity-70'
      )}>
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2 flex-1 min-w-0">
            <div>
              <div className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">分析标的</div>
              <h1 className="text-2xl font-bold truncate">{stockName}</h1>
              <div className="text-xs text-stone-400 font-mono mt-1">
                {analysis.stock_id} | {market} | {stockIndustry}
              </div>
            </div>
            <div className="text-[10px] text-stone-400">
              数据时间：{formatDateTime(dataAsOf)}
            </div>
          </div>
          <button
            onClick={handleAddToWatchlist}
            disabled={isInWatchlist}
            className={cn(
              'p-2 rounded-xl transition-all',
              isInWatchlist
                ? 'bg-yellow-100 text-yellow-600'
                : 'bg-stone-100 text-stone-400 hover:bg-yellow-50 hover:text-yellow-600'
            )}
            title={isInWatchlist ? '已在观察列表' : '加入观察列表'}
          >
            <Star size={20} className={isInWatchlist ? 'fill-yellow-500' : undefined} />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-2xl bg-stone-50 p-4">
            <div className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">最新价</div>
            <div className="text-2xl font-bold mt-2">{formatPrice(quote?.latest_price)}</div>
            <div
              className={cn(
                'text-xs font-medium mt-1',
                (quote?.change_percent || 0) >= 0 ? 'text-red-600' : 'text-emerald-600'
              )}
            >
              {formatPercent(quote?.change_percent)}
            </div>
          </div>
          <div className="rounded-2xl bg-stone-50 p-4">
            <div className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">换手率 / 振幅</div>
            <div className="text-lg font-bold mt-2">{formatPercent(quote?.turnover_rate)}</div>
            <div className="text-xs text-stone-500 mt-1">振幅 {formatPercent(quote?.amplitude)}</div>
          </div>
          <div className="rounded-2xl bg-stone-50 p-4">
            <div className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">成交额</div>
            <div className="text-lg font-bold mt-2">{formatLargeNumber(quote?.amount)}</div>
            <div className="text-xs text-stone-500 mt-1">成交量 {formatLargeNumber(quote?.volume)}</div>
          </div>
          <div className="rounded-2xl bg-stone-50 p-4">
            <div className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">估值</div>
            <div className="text-lg font-bold mt-2">PE {formatPrice(quote?.pe_ratio)}</div>
            <div className="text-xs text-stone-500 mt-1">PB {formatPrice(quote?.pb_ratio)}</div>
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">一句话判断</label>
          <h2 className="text-xl font-bold leading-tight">{decisionCard.headline_judgement}</h2>
        </div>

        <div className="grid grid-cols-2 gap-4 pt-4 border-t border-stone-50">
          <div className="space-y-1">
            <label className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">适合谁</label>
            <p className="text-xs font-medium text-emerald-600">{decisionCard.user_fit_summary.fit}</p>
          </div>
          <div className="space-y-1">
            <label className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">不适合谁</label>
            <p className="text-xs font-medium text-red-600">{decisionCard.user_fit_summary.unfit}</p>
          </div>
        </div>
      </section>

      <section className="bg-white rounded-2xl p-5 border border-stone-100 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">核心理由</h3>
          <div className="flex items-center gap-1 text-xs text-stone-400">
            <Info size={14} />
            <span>事实 / 推理 / 不确定</span>
          </div>
        </div>
        <div className="space-y-4">
          {decisionCard.key_reason_summary.map((item, index) => (
            <div key={`${item.text}-${index}`} className="flex gap-3 items-start">
              <div className="w-5 h-5 rounded-full bg-stone-100 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">
                {index + 1}
              </div>
              <div className="flex-1 space-y-1">
                <p className="text-sm text-stone-600 leading-relaxed">{item.text}</p>
                <OutputTag type={item.mark_type} />
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="text-xs font-bold text-stone-400 uppercase tracking-widest px-1">下一步建议动作</h3>
        <div className="space-y-2">
          {decisionCard.next_step_actions.map((action, index) => (
            <div key={`${action}-${index}`} className="bg-white rounded-2xl p-4 border border-stone-100">
              <span className="text-sm font-medium">{action}</span>
            </div>
          ))}
        </div>
      </section>

      <section className={cn(
        'rounded-3xl p-6 space-y-5',
        isExpired ? 'bg-stone-200' : 'bg-stone-900 text-white'
      )}>
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-amber-400">
            <AlertCircle size={18} />
            <label className="text-[10px] font-bold uppercase tracking-widest">主要风险与失效条件</label>
          </div>
          <p className={cn('text-sm leading-relaxed', isExpired ? 'text-stone-700' : 'text-stone-300')}>
            {decisionCard.primary_risks}
          </p>
        </div>

        <div className={cn('grid grid-cols-2 gap-4 pt-4 border-t', isExpired ? 'border-stone-300' : 'border-white/10')}>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Calendar size={16} className={isExpired ? 'text-stone-500' : 'text-stone-400'} />
              <span className={cn('text-xs', isExpired ? 'text-stone-600' : 'text-stone-400')}>建议复盘时间</span>
            </div>
            <div className={cn('text-sm font-bold', isExpired ? 'text-stone-800' : 'text-white')}>
              {formatDate(decisionCard.review_at)}
            </div>
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Clock size={16} className={isExpired ? 'text-stone-500' : 'text-stone-400'} />
              <span className={cn('text-xs', isExpired ? 'text-stone-600' : 'text-stone-400')}>结论有效期</span>
            </div>
            <div className={cn('text-sm font-bold', isExpired ? 'text-stone-800' : 'text-white')}>
              {formatDate(validUntil)}
            </div>
          </div>
        </div>
      </section>

      <section className="bg-white rounded-2xl p-4 border border-stone-100 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">市场背景</h3>
          {analysis.status === 'partial_ready' ? (
            <span className="text-[10px] text-amber-500">数据暂时缺失</span>
          ) : (
            <OutputTag type={analysis.market_context?.mark_type || 'model_inference'} />
          )}
        </div>
        {analysis.market_context ? (
          <div className="space-y-1">
            <div className="text-sm font-bold">{analysis.market_context.market_event || '--'}</div>
            <p className="text-xs text-stone-500">{analysis.market_context.impact_boundary || '--'}</p>
          </div>
        ) : (
          <p className="text-xs text-stone-400">暂时没有获取到市场背景信息。</p>
        )}
      </section>

      <section className="bg-white rounded-2xl p-4 border border-stone-100 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">公司概况</h3>
          {analysis.status === 'partial_ready' ? (
            <span className="text-[10px] text-amber-500">数据暂时缺失</span>
          ) : companyProfile?.board_name ? (
            <span className="text-[10px] px-2 py-1 rounded-full bg-stone-100 text-stone-500">
              {companyProfile.board_name}
            </span>
          ) : null}
        </div>
        <p className="text-sm text-stone-600 leading-relaxed">
          {companyProfile?.description || '暂时没有抓取到更完整的公司介绍。'}
        </p>
        {companyProfile?.business_scope && (
          <div className="rounded-xl bg-stone-50 p-3 text-xs text-stone-500 leading-relaxed">
            {companyProfile.business_scope}
          </div>
        )}
      </section>

      <section className="bg-white rounded-2xl p-4 border border-stone-100 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">最近公告与事件</h3>
          <span className="text-xs text-stone-400">{recentEvents.length} 条</span>
        </div>
        {recentEvents.length > 0 ? (
          <div className="space-y-3">
            {recentEvents.map((event, index) => (
              <a
                key={`${event.title}-${index}`}
                href={event.url || '#'}
                target={event.url ? '_blank' : undefined}
                rel={event.url ? 'noreferrer' : undefined}
                className="block rounded-2xl border border-stone-100 p-4 hover:bg-stone-50 transition-colors"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="text-sm font-semibold text-stone-900">{event.title}</div>
                    <div className="text-xs text-stone-500">
                      {event.event_type || '公司公告'} | {formatDate(event.published_at)}
                    </div>
                  </div>
                  <span className="text-[10px] text-stone-300 uppercase">{event.source}</span>
                </div>
              </a>
            ))}
          </div>
        ) : (
          <div className="rounded-2xl bg-stone-50 p-4 text-sm text-stone-500">
            近一段时间没有抓到更明确的公告事件，建议把这部分视作信息缺口。
          </div>
        )}
      </section>

      <button
        onClick={() => setShowDetails((current) => !current)}
        className="w-full py-4 text-stone-400 text-xs font-bold uppercase tracking-widest flex items-center justify-center gap-2"
      >
        {showDetails ? '收起更多数据' : '展开更多数据'}
        <ChevronDown size={14} className={cn('transition-transform', showDetails && 'rotate-180')} />
      </button>

      {showDetails && (
        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="space-y-4 overflow-hidden">
          <div className="bg-stone-100 rounded-2xl p-4 space-y-4">
            <div className="space-y-2">
              <h4 className="text-[10px] font-bold text-stone-400 uppercase tracking-widest">关键指标</h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="rounded-xl bg-white p-3">开盘价：{formatPrice(quote?.open_price)}</div>
                <div className="rounded-xl bg-white p-3">昨收：{formatPrice(quote?.previous_close)}</div>
                <div className="rounded-xl bg-white p-3">最高：{formatPrice(quote?.high_price)}</div>
                <div className="rounded-xl bg-white p-3">最低：{formatPrice(quote?.low_price)}</div>
                <div className="rounded-xl bg-white p-3">总市值：{formatLargeNumber(quote?.total_market_cap)}</div>
                <div className="rounded-xl bg-white p-3">流通市值：{formatLargeNumber(quote?.circulating_market_cap)}</div>
              </div>
            </div>
            <div className="space-y-2">
              <h4 className="text-[10px] font-bold text-stone-400 uppercase tracking-widest">数据来源</h4>
              <div className="flex flex-wrap gap-2">
                {analysis.data_sources.map((source) => (
                  <span
                    key={source}
                    className="px-2 py-1 rounded-full bg-white text-xs text-stone-500 border border-stone-200"
                  >
                    {source}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      )}

      <button
        onClick={() => setShowExplain(true)}
        className="w-full bg-blue-50 border border-blue-100 rounded-2xl p-4 flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white">
            <MessageSquare size={20} />
          </div>
          <div className="text-left">
            <div className="text-sm font-bold text-blue-900">AI 解释层</div>
            <div className="text-[10px] text-blue-600 font-medium">
              {analysis.status === 'partial_ready' && !analysis.explanation_layer
                ? '解释层数据暂时缺失'
                : '把这张分析卡片讲得更直白一点'}
            </div>
          </div>
        </div>
        <ChevronDown size={20} className="text-blue-300 -rotate-90" />
      </button>

      <AnimatePresence>
        {showExplain && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowExplain(false)}
              className="fixed inset-0 bg-black/40 z-50 backdrop-blur-sm"
            />
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-md bg-white rounded-t-[32px] z-50 p-6 safe-bottom"
            >
              <div className="w-12 h-1.5 bg-stone-200 rounded-full mx-auto mb-6" />
              <div className="space-y-6">
                <div className="space-y-2">
                  <h3 className="text-xl font-bold">AI 解释层</h3>
                  <p className="text-sm text-stone-600 leading-relaxed">
                    {analysis.explanation_layer?.plain_text || '暂无解释文本'}
                  </p>
                </div>
                <div className="bg-blue-50 p-4 rounded-2xl space-y-2">
                  <h4 className="text-xs font-bold text-blue-900 uppercase tracking-widest">生活化类比</h4>
                  <p className="text-sm text-blue-800 italic">
                    “{analysis.explanation_layer?.case_example || '暂无类比说明'}”
                  </p>
                </div>
                <button
                  onClick={() => setShowExplain(false)}
                  className="w-full py-4 bg-ink text-white rounded-2xl font-bold"
                >
                  我知道了
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showFocusReasonModal && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowFocusReasonModal(false)}
              className="fixed inset-0 bg-black/40 z-50 backdrop-blur-sm"
            />
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-md bg-white rounded-t-[32px] z-50 p-6 safe-bottom"
            >
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold">记录关注理由</h3>
                <button
                  onClick={() => setShowFocusReasonModal(false)}
                  className="p-2 -mr-2 text-stone-400 hover:text-stone-600"
                >
                  <X size={20} />
                </button>
              </div>
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-semibold">你为什么要继续关注这只股票？</label>
                  <textarea
                    placeholder="例如：等下一份财报、观察公告兑现情况、确认价格是否企稳"
                    className="w-full bg-stone-50 border border-stone-200 rounded-2xl p-4 text-sm h-32 focus:ring-2 focus:ring-ink resize-none"
                    maxLength={100}
                    value={focusReason}
                    onChange={(event) => setFocusReason(event.target.value)}
                  />
                  <div className="text-right text-xs text-stone-400">{focusReason.length}/100</div>
                </div>
                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => setShowFocusReasonModal(false)}
                    className="flex-1 py-4 bg-stone-100 text-stone-700 rounded-2xl font-bold"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleSaveFocusReason}
                    disabled={!focusReason.trim() || savingReason}
                    className="flex-1 py-4 bg-ink text-white rounded-2xl font-bold disabled:opacity-30"
                  >
                    {savingReason ? '保存中...' : '保存'}
                  </button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <LearningFeedbackCard
        visible={showFeedback}
        data={feedbackData}
        onConfirm={handleFeedbackConfirm}
        onLater={handleFeedbackLater}
        onDismiss={handleFeedbackDismiss}
        loading={feedbackLoading}
        showCount={feedbackShowCount}
      />

      <div className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-md bg-white/80 backdrop-blur-xl border-t border-stone-100 p-4 safe-bottom z-30">
        <div className="flex gap-3">
          <button
            onClick={() => setShowFocusReasonModal(true)}
            className="flex-1 py-3 bg-stone-100 text-ink rounded-xl font-bold text-sm hover:bg-stone-200 transition-colors"
          >
            记录关注理由
          </button>
          <button
            onClick={handleAddToWatchlist}
            disabled={isInWatchlist}
            className="flex-1 py-3 bg-ink text-white rounded-xl font-bold text-sm hover:bg-stone-800 transition-colors disabled:opacity-40"
          >
            {isInWatchlist ? '已在观察列表' : '加入观察列表'}
          </button>
        </div>
      </div>
    </div>
  );
}
