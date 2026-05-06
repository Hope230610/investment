import React, { useEffect, useState, useRef } from 'react';
import { Link, useParams, useLocation } from 'react-router-dom';
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
  Share2,
  ShieldAlert,
  Star,
  X,
} from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';

import { apiGet, apiPost, createShareSnapshot, deleteWatchlistItem, getLearningHistory, getWatchlistItems, patchReviewResult, postLearningFeedback, postWatchlistItem } from '../api';
import type { AnalysisDetail, OutputMarkType } from '../types';
import { addFocusReason, cn } from '../utils';
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function toFiniteNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function toDisplayText(value: unknown): string {
  return typeof value === 'string' && value.trim() ? value : '--';
}

function formatMaybeNumber(value: unknown, fractionDigits = 2) {
  const numberValue = toFiniteNumber(value);
  return numberValue === null ? '--' : numberValue.toFixed(fractionDigits);
}

function payloadNumber(payload: Record<string, unknown> | null | undefined, key: string) {
  const value = payload?.[key];
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim() && Number.isFinite(Number(value))) return Number(value);
  return null;
}

export function normalizeHoldingContext(value: unknown) {
  if (!isRecord(value)) return null;
  const weight = toFiniteNumber(value.weight);
  return {
    stockName: toDisplayText(value.stock_name),
    weightPercent: weight === null ? '--' : (weight * 100).toFixed(1),
    costPrice: formatMaybeNumber(value.cost_price),
    currentPrice: formatMaybeNumber(value.current_price),
    unrealizedPnl: formatMaybeNumber(value.unrealized_pnl),
    positionUpdatedAt: typeof value.position_updated_at === 'string' ? value.position_updated_at : null,
  };
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


function formatDegradeFlag(flag: string) {
  if (flag === 'missing_market_data') return '场景数据暂时不完整';
  if (flag === 'missing_announcements') return '公告/事件信息不足';
  if (flag === 'insufficient_evidence') return '证据链不足，当前结论仅供观察';
  if (flag === 'model_fallback') return '已使用规则兜底结果';
  if (flag.startsWith('analysis_error')) {
    const detail = flag.replace('analysis_error: ', '').trim();
    return detail ? `分析生成异常：${detail}` : '分析过程出现异常';
  }
  return flag;
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
    <div className="flex min-h-[62vh] items-center justify-center p-6">
      <div className="soft-card w-full max-w-sm rounded-[28px] p-6 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-3xl bg-mist">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-100 border-t-teal-700" />
        </div>
        <div className="mt-4 space-y-1">
          <p className="text-lg font-bold">正在生成决策卡</p>
          <p className="text-xs leading-relaxed text-stone-500">
            正在整理场景信息、证据和风险提示{stockId ? `：${stockId}` : '，请稍等片刻'}。
          </p>
        </div>
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
  const [watchlistItemId, setWatchlistItemId] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [savingReason, setSavingReason] = useState(false);
  const [sharing, setSharing] = useState(false);

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
  const reviewFormData = (location.state as { reviewFormData?: import('../utils/learningFeedback').ReviewFormData; pendingReviewTaskId?: string })?.reviewFormData;
  // 来自 ReviewsPage "去复盘" 的原始 pending review（如果用户是走提醒入口进来的）
  const pendingReviewTaskId = (location.state as { pendingReviewTaskId?: string })?.pendingReviewTaskId;

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
      await patchReviewResult(pendingReviewTaskId || id, {
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
        await patchReviewResult(pendingReviewTaskId || id, { review_result: null, mark_completed: true });
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
    getWatchlistItems()
      .then((list) => {
        const found = list.find((item) => item.stock_id === analysis.stock_id);
        setIsInWatchlist(!!found);
        setWatchlistItemId(found?.id ?? null);
      })
      .catch(() => {
        setIsInWatchlist(false);
        setWatchlistItemId(null);
      });
  }, [analysis?.stock_id]);

  const decisionCard = analysis?.decision_card;
  const quote = analysis?.stock_snapshot;
  const companyProfile = analysis?.company_profile;
  const recentEvents = analysis?.recent_events || [];
  const isCampusConsumption = analysis?.scenario === 'pre_trade_check'
    && analysis?.scenario_payload?.decision_domain === 'campus_consumption';
  const stockName = analysis?.stock_name || analysis?.stock_id || '分析结果';
  const stockIndustry = isCampusConsumption ? '校园消费场景' : (analysis?.stock_industry || companyProfile?.board_name || '未识别行业');
  const market = isCampusConsumption ? '消费自检' : (analysis?.stock_market || analysis?.stock_id.slice(0, 2) || '--');
  const validUntil = analysis?.valid_until;
  const dataAsOf = analysis?.data_as_of;
  const confidence = decisionCard?.confidence ?? decisionCard?.confidence_level ?? 'medium';
  const isExpired = validUntil ? Date.now() > new Date(validUntil).getTime() : analysis?.status === 'expired';
  const holdingContext = normalizeHoldingContext(analysis?.holding_context);
  const monthlyAllowance = payloadNumber(analysis?.scenario_payload, 'monthly_allowance');
  const spentThisMonth = payloadNumber(analysis?.scenario_payload, 'spent_this_month');
  const itemPrice = payloadNumber(analysis?.scenario_payload, 'item_price');
  const installmentMonths = payloadNumber(analysis?.scenario_payload, 'installment_months');
  const remainingBudget = monthlyAllowance !== null && spentThisMonth !== null ? monthlyAllowance - spentThisMonth : null;
  const monthlyPayment = itemPrice !== null && installmentMonths ? itemPrice / installmentMonths : null;
  const campusRiskTags = ['冲动消费', '盲目跟风', '预算透支', '分期依赖'];
  const campusStudentActions = [
    '等待 48 小时后再重新判断',
    '比较 3000 元以内替代方案',
    '算清总成本、手续费和逾期成本',
    '至少保留一个月生活费安全垫',
    '加入月底财务复盘',
  ];

  const handleRemoveFromWatchlist = async () => {
    if (!watchlistItemId) return;
    try {
      await deleteWatchlistItem(watchlistItemId);
      setIsInWatchlist(false);
      setWatchlistItemId(null);
      setToastMessage(`已将 ${stockName} 移出观察列表`);
      window.setTimeout(() => setToastMessage(null), 2000);
    } catch {
      setToastMessage('移除失败，请重试');
      window.setTimeout(() => setToastMessage(null), 2000);
    }
  };

  const handleAddToWatchlist = async () => {
    if (!analysis) return;

    try {
      const item = await postWatchlistItem({
        stock_id: analysis.stock_id,
        focus_reason: undefined,
      });
      setIsInWatchlist(true);
      setWatchlistItemId(item.id);
      setToastMessage(`已将 ${stockName} 加入观察列表`);
      window.setTimeout(() => setToastMessage(null), 2000);
    } catch {
      setToastMessage('添加失败，请重试');
      window.setTimeout(() => setToastMessage(null), 2000);
    }
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

      const watchlistItem = await postWatchlistItem({
        stock_id: analysis.stock_id,
        focus_reason: focusReason.trim(),
      });

      setIsInWatchlist(true);
      setWatchlistItemId(watchlistItem.id);
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

  const handleCreateShare = async () => {
    if (!id || sharing) return;
    setSharing(true);
    try {
      const snapshot = await createShareSnapshot({
        source_type: 'analysis',
        source_id: id,
        privacy_level: 'unlisted',
        expires_in_days: 30,
      });
      const url = `${window.location.origin}/share/${snapshot.share_id}`;
      await navigator.clipboard?.writeText(url);
      setToastMessage('分享卡片已生成，链接已复制');
      window.setTimeout(() => setToastMessage(null), 2400);
    } catch (shareError) {
      setToastMessage(shareError instanceof Error ? shareError.message : '分享卡片生成失败');
      window.setTimeout(() => setToastMessage(null), 2400);
    } finally {
      setSharing(false);
    }
  };

  if (loading) {
    return <ProcessingState />;
  }

  if (error) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center p-6">
        <div className="soft-card w-full max-w-sm space-y-4 rounded-[28px] p-6 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-50">
            <AlertCircle className="text-amber-600" size={22} />
          </div>
          <div className="space-y-2">
            <h2 className="text-lg font-bold">分析结果暂时不可用</h2>
            <p className="text-sm text-stone-500 leading-relaxed">{error}</p>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="primary-action w-full"
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
    const failReason = analysis.degrade_flags && analysis.degrade_flags.length > 0
      ? analysis.degrade_flags[0].replace('analysis_error: ', '')
      : null;
    const fallbackActions = decisionCard?.next_step_actions?.length
      ? decisionCard.next_step_actions
      : ['稍后重新发起分析，并先检查输入对象、数据服务和网络状态。'];
    const fallbackBoundaries = decisionCard?.invalidation_conditions?.length
      ? decisionCard.invalidation_conditions
      : ['本次分析没有形成完整证据前，当前占位结论无效。'];

    return (
      <div className="flex min-h-[60vh] items-center justify-center p-6">
        <div className="soft-card w-full max-w-sm space-y-5 rounded-[28px] p-6">
          <div className="text-center space-y-3">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-50">
              <AlertTriangle className="text-amber-600" size={22} />
            </div>
            <div className="space-y-2">
              <h2 className="text-lg font-bold">分析生成失败</h2>
              <p className="text-sm text-stone-500 leading-relaxed">
                {failReason
                  ? `失败原因：${formatDegradeFlag(failReason)}。当前没有足够证据支持方向性判断。`
                  : '这次没有成功拿到完整数据，当前没有足够证据支持方向性判断。'}
              </p>
            </div>
          </div>

          <div className="space-y-3 rounded-2xl border border-stone-100 bg-stone-50 p-4">
            <div className="text-[10px] font-bold text-stone-400 uppercase tracking-widest">下一步</div>
            <div className="space-y-2">
              {fallbackActions.map((action, index) => (
                <div key={`${action}-${index}`} className="flex gap-2 items-start text-xs text-stone-600 leading-relaxed">
                  <RefreshCw size={13} className="text-stone-400 shrink-0 mt-0.5" />
                  <span>{action}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-3 rounded-2xl border border-amber-100 bg-amber-50 p-4">
            <div className="text-[10px] font-bold text-amber-600 uppercase tracking-widest">检查项</div>
            <div className="space-y-2 text-xs text-amber-800 leading-relaxed">
              <div>确认输入对象是否正确，必要时回到搜索页重新选择。</div>
              <div>如果外部数据或风险信息接口暂时不可用，稍后重试。</div>
              <div>不要基于失败占位内容做购买、借用额度或资金安排。</div>
            </div>
          </div>

          <div className="space-y-2 rounded-2xl border border-rose-100 bg-rose-50 p-4">
            <div className="text-[10px] font-bold uppercase tracking-widest text-rose-600">失效边界</div>
            {fallbackBoundaries.map((item, index) => (
              <div key={`${item}-${index}`} className="text-xs leading-relaxed text-rose-700">
                {item}
              </div>
            ))}
          </div>

          <button
            onClick={() => window.location.reload()}
            className="primary-action w-full"
          >
            <RefreshCw size={16} />
            重新加载
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5 px-4 py-5 pb-32">
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-20 left-1/2 z-50 -translate-x-1/2 rounded-2xl bg-ink px-4 py-2 text-sm font-medium text-white shadow-lg"
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 size={16} />
              <span>{toastMessage}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="rounded-2xl border border-stone-100 bg-white/70 px-3 py-2 text-center text-[10px] font-medium uppercase tracking-widest text-stone-500">
        以下内容用于校园金融素养教育和辅助判断，不替代个人预算规划或专业意见
      </div>

      {isCampusConsumption && (
        <section className="space-y-2 rounded-3xl border border-teal-100 bg-mist p-4">
          <div className="text-[10px] font-bold uppercase tracking-widest text-teal-700">PCG Demo 接入位</div>
          <p className="text-xs leading-relaxed text-teal-900">
            当前 Demo 使用模拟数据跑通校园消费决策闭环，没有真实调用外部 PCG API。这里展示的是后续接入位：腾讯财经提供风险教育数据，微信 / QQ 承接校园提醒与分享入口，腾讯云承载部署和模型服务。
          </p>
        </section>
      )}

      {analysis.status === 'partial_ready' && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-start gap-3 rounded-3xl border border-amber-100 bg-amber-50 px-4 py-3"
        >
          <Info size={16} className="text-amber-500 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-800 leading-relaxed">
            <span className="font-bold">受限结论</span>：当前结果可供阅读，但不能视为完整判断。请优先观察、补充信息或重新评估。
            {analysis.degrade_flags && analysis.degrade_flags.length > 0 ? (
              <ul className="mt-1.5 space-y-0.5 pl-2">
                {analysis.degrade_flags.map((flag, i) => (
                  <li key={i} className="list-disc">
                    {formatDegradeFlag(flag)}
                  </li>
                ))}
              </ul>
            ) : (
              '部分内容可能不够完整，请留意各板块的降级提示。'
            )}
          </div>
        </motion.div>
      )}

      {analysis.intervention && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-3 rounded-3xl border border-amber-100 bg-amber-50 p-4"
        >
          <div className="flex items-center gap-2 text-teal-700">
            <ShieldAlert size={20} />
            <span className="font-bold">行为干预提醒</span>
          </div>
          <p className="text-xs leading-relaxed text-amber-900">
            系统识别到当前场景可能带有情绪化触发，建议先回答下面这些问题，再决定是否动作。
          </p>
          <div className="space-y-2">
            {analysis.intervention.questions.map((question, index) => (
              <div
                key={`${question}-${index}`}
                className="rounded-2xl border border-amber-100/70 bg-white/75 p-3 text-xs text-amber-950"
              >
                {question}
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {holdingContext && !isCampusConsumption && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-3xl border border-amber-100 bg-amber-50 p-4"
        >
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-amber-600">当前预算上下文</div>
              <div className="mt-1 text-sm font-bold text-amber-900">
                {holdingContext.stockName} 占预算目标约 {holdingContext.weightPercent}%
              </div>
            </div>
            <Link to="/portfolio" className="rounded-xl bg-white px-3 py-2 text-xs font-bold text-amber-700">
              查看
            </Link>
          </div>
          <p className="mt-2 text-xs leading-relaxed text-amber-800">
            成本 {holdingContext.costPrice}，现价 {holdingContext.currentPrice}，浮动盈亏约 {holdingContext.unrealizedPnl}。
            预算记录更新于 {formatDateTime(holdingContext.positionUpdatedAt)}，可能不是实时金额；以下内容用于辅助判断，不替你做购买或资金安排。
          </p>
        </motion.div>
      )}

      <section className={cn(
        'soft-card space-y-6 rounded-[30px] p-6',
        isExpired && 'opacity-70'
      )}>
        {isCampusConsumption && (
          <div className="rounded-3xl border border-teal-100 bg-mist p-4">
            <div className="text-[10px] font-bold uppercase tracking-widest text-teal-700">六段式校园决策卡</div>
            <div className="mt-1 text-sm leading-relaxed text-teal-900">当前判断、证据、边界、行动建议和复盘时间一次讲清。</div>
          </div>
        )}
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2 flex-1 min-w-0">
            <div>
              <div className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">决策对象</div>
              <h1 className="truncate text-2xl font-bold">{stockName}</h1>
              <div className="mt-1 truncate font-mono text-xs text-stone-400">
                {isCampusConsumption ? '校园消费 Demo' : analysis.stock_id} | {market} | {stockIndustry}
              </div>
            </div>
            <div className="text-[10px] text-stone-400">
              {isCampusConsumption ? '记录时间' : '数据时间'}：{formatDateTime(dataAsOf)}
            </div>
          </div>
          <button
            onClick={isInWatchlist ? handleRemoveFromWatchlist : handleAddToWatchlist}
            className={cn(
              'p-2 rounded-xl transition-all',
              isInWatchlist
                ? 'bg-amber-50 text-amber-600 hover:bg-amber-100'
                : 'bg-stone-100 text-stone-400 hover:bg-mist hover:text-teal-700'
            )}
            title={isCampusConsumption
              ? (isInWatchlist ? '移出复盘清单' : '加入月底复盘')
              : (isInWatchlist ? '移出观察列表' : '加入观察列表')}
          >
            <Star size={20} className={isInWatchlist ? 'fill-amber-400' : undefined} />
          </button>
        </div>

        {isCampusConsumption ? (
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-3xl bg-stone-50 p-4">
              <div className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">月生活费</div>
              <div className="text-2xl font-bold mt-2">{monthlyAllowance ?? '--'} 元</div>
              <div className="text-xs text-stone-500 mt-1">已消费 {spentThisMonth ?? '--'} 元</div>
            </div>
            <div className="rounded-3xl bg-mist p-4">
              <div className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">可用余额</div>
              <div className="text-2xl font-bold mt-2">{remainingBudget ?? '--'} 元</div>
              <div className="text-xs text-stone-500 mt-1">预算安全线参考</div>
            </div>
            <div className="rounded-3xl bg-stone-50 p-4">
              <div className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">商品价格</div>
              <div className="text-lg font-bold mt-2">{itemPrice ?? '--'} 元</div>
              <div className="text-xs text-stone-500 mt-1">高于本月可用余额</div>
            </div>
            <div className="rounded-3xl bg-clay p-4">
              <div className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">分期压力</div>
              <div className="text-lg font-bold mt-2">{installmentMonths ?? '--'} 期</div>
              <div className="text-xs text-stone-500 mt-1">每期约 {monthlyPayment === null ? '--' : monthlyPayment.toFixed(0)} 元</div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-3xl bg-stone-50 p-4">
              <div className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">最新价</div>
              <div className="text-2xl font-bold mt-2">{formatPrice(quote?.latest_price)}</div>
              <div
                className={cn(
                  'text-xs font-medium mt-1',
                  (quote?.change_percent || 0) >= 0 ? 'text-amber-700' : 'text-teal-700'
                )}
              >
                {formatPercent(quote?.change_percent)}
              </div>
            </div>
            <div className="rounded-3xl bg-stone-50 p-4">
              <div className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">换手率 / 振幅</div>
              <div className="text-lg font-bold mt-2">{formatPercent(quote?.turnover_rate)}</div>
              <div className="text-xs text-stone-500 mt-1">振幅 {formatPercent(quote?.amplitude)}</div>
            </div>
            <div className="rounded-3xl bg-stone-50 p-4">
              <div className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">成交额</div>
              <div className="text-lg font-bold mt-2">{formatLargeNumber(quote?.amount)}</div>
              <div className="text-xs text-stone-500 mt-1">成交量 {formatLargeNumber(quote?.volume)}</div>
            </div>
            <div className="rounded-3xl bg-stone-50 p-4">
              <div className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">估值</div>
              <div className="text-lg font-bold mt-2">PE {formatPrice(quote?.pe_ratio)}</div>
              <div className="text-xs text-stone-500 mt-1">PB {formatPrice(quote?.pb_ratio)}</div>
            </div>
          </div>
        )}

        {isCampusConsumption && (
          <div className="space-y-2">
            <div className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">风险识别标签</div>
            <div className="flex flex-wrap gap-2">
              {campusRiskTags.map((tag) => (
                <span key={tag} className="rounded-full border border-amber-100 bg-amber-50 px-3 py-1 text-[10px] font-bold text-amber-700">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <label className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">
              {isCampusConsumption ? '1 当前判断' : '当前判断'}
            </label>
            {confidence && (
              <span className={cn(
                'px-2 py-0.5 rounded-full text-[10px] font-bold',
                confidence === 'high' && 'bg-emerald-100 text-emerald-700',
                confidence === 'medium' && 'bg-amber-100 text-amber-700',
                confidence === 'low' && 'bg-red-100 text-red-700',
              )}>
                {confidence === 'high' ? '高置信' : confidence === 'medium' ? '中置信' : '低置信'}
              </span>
            )}
          </div>
          <h2 className={cn('break-words font-bold leading-tight', isCampusConsumption ? 'text-2xl text-stone-950' : 'text-xl')}>
            {decisionCard.headline_judgement}
          </h2>
        </div>

        <div className="grid grid-cols-1 gap-3 border-t border-stone-100 pt-4 sm:grid-cols-3">
          <div className="space-y-1 rounded-2xl bg-stone-50 p-3">
            <label className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">适合谁</label>
            <p className="text-xs font-medium leading-relaxed text-teal-700">{isCampusConsumption ? '能等待 48 小时并重算预算的学生' : decisionCard.user_fit_summary.fit}</p>
          </div>
          <div className="space-y-1 rounded-2xl bg-stone-50 p-3">
            <label className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">不适合谁</label>
            <p className="text-xs font-medium leading-relaxed text-amber-700">{isCampusConsumption ? '本月安全垫不足仍想立刻分期的学生' : decisionCard.user_fit_summary.unfit}</p>
          </div>
          <div className="space-y-1 rounded-2xl bg-stone-50 p-3">
            <label className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">置信等级</label>
            <p className={cn(
              'text-xs font-bold',
              confidence === 'high' && 'text-teal-700',
              confidence === 'medium' && 'text-amber-600',
              confidence === 'low' && 'text-rose-700',
            )}>
              {confidence === 'high' ? '高' : confidence === 'medium' ? '中' : '低'}
            </p>
          </div>
        </div>
      </section>

      <section className="space-y-4 rounded-3xl border border-stone-100 bg-white/80 p-5">
        <div className="flex items-center justify-between">
          <h3 className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">
            {isCampusConsumption ? '2 核心理由' : '核心理由'}
          </h3>
          <div className="flex items-center gap-1 text-xs text-stone-400">
            <Info size={14} />
            <span>事实 / 推理 / 不确定</span>
          </div>
        </div>
        <div className="space-y-4">
          {decisionCard.key_reason_summary.map((item, index) => (
            <div key={`${item.text}-${index}`} className="flex gap-3 items-start">
              <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-mist text-[10px] font-bold text-teal-700">
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

      {decisionCard.supporting_evidence && decisionCard.supporting_evidence.length > 0 && (
        <section className="space-y-3 rounded-3xl border border-teal-100 bg-mist p-5">
          <div className="flex items-center gap-2">
            <div className="flex h-4 w-4 items-center justify-center rounded-full bg-teal-600">
              <div className="w-1.5 h-1.5 rounded-full bg-white" />
            </div>
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-teal-700">
              {isCampusConsumption ? '3 支撑证据' : '支撑证据'}
            </h3>
          </div>
          <div className="space-y-2">
            {decisionCard.supporting_evidence.slice(0, 3).map((item, index) => (
              <div key={`sup-${index}`} className="flex gap-2 items-start">
                <span className="mt-0.5 shrink-0 text-[10px] font-bold text-teal-700">S{index + 1}</span>
                <p className="text-xs leading-relaxed text-teal-950">{item}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {decisionCard.counter_evidence && decisionCard.counter_evidence.length > 0 && (
        <section className="space-y-3 rounded-3xl border border-amber-100 bg-amber-50 p-5">
          <div className="flex items-center gap-2">
            <AlertTriangle size={14} className="text-amber-600" />
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-amber-700">
              {isCampusConsumption ? '4 反方证据' : '反方证据'}
            </h3>
          </div>
          <div className="space-y-2">
            {decisionCard.counter_evidence.map((item, index) => (
              <div key={`cnt-${index}`} className="flex gap-2 items-start">
                <span className="mt-0.5 shrink-0 text-[10px] font-bold text-amber-700">C{index + 1}</span>
                <p className="text-xs leading-relaxed text-amber-950">{item}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="space-y-3">
        <h3 className="px-1 text-xs font-bold uppercase tracking-widest text-stone-400">
          {isCampusConsumption ? '5 行动建议' : '下一步建议动作'}
        </h3>
        {isCampusConsumption && (
          <div className="grid grid-cols-1 gap-2">
            {campusStudentActions.map((action, index) => (
              <div key={action} className="flex items-start gap-3 rounded-3xl border border-teal-100 bg-white/80 p-4 text-sm font-medium text-stone-800">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-mist text-xs font-bold text-teal-700">
                  {index + 1}
                </span>
                <span className="leading-relaxed">{action}</span>
              </div>
            ))}
          </div>
        )}
        <div className="overflow-hidden rounded-3xl border border-stone-100 bg-white/80">
          {decisionCard.next_step_actions.map((action, index) => (
            <div
              key={`${action}-${index}`}
              className={cn(
                'flex items-start gap-3 p-4',
                index < decisionCard.next_step_actions.length - 1 && 'border-b border-stone-100',
              )}
            >
              <CheckCircle2 size={17} className="mt-0.5 shrink-0 text-teal-700" />
              <span className="text-sm font-medium leading-relaxed">{action}</span>
            </div>
          ))}
        </div>
      </section>

      <section className={cn(
        'space-y-5 rounded-[28px] border p-5',
        isExpired ? 'border-stone-200 bg-stone-100' : 'border-amber-100 bg-amber-50'
      )}>
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-amber-700">
            <AlertCircle size={18} />
            <label className="text-[10px] font-bold uppercase tracking-widest">
              {isCampusConsumption ? '风险提示与失效条件' : '主要风险与失效条件'}
            </label>
          </div>
          <p className={cn('text-sm leading-relaxed', isExpired ? 'text-stone-700' : 'text-amber-950')}>
            {decisionCard.primary_risks}
          </p>
          {decisionCard.invalidation_conditions && decisionCard.invalidation_conditions.length > 0 && (
            <div className={cn('mt-3 space-y-2 border-t pt-3', isExpired ? 'border-stone-300' : 'border-amber-200')}>
              <p className={cn('text-[10px] font-bold uppercase tracking-widest', isExpired ? 'text-stone-500' : 'text-amber-700')}>
                以下情况请重新评估
              </p>
              {decisionCard.invalidation_conditions.map((cond, index) => (
                <div key={`inv-${index}`} className="flex gap-2 items-start">
                  <span className={cn('mt-0.5 shrink-0 text-[10px] font-bold', isExpired ? 'text-stone-400' : 'text-amber-700')}>
                    ✕
                  </span>
                  <p className={cn('text-xs leading-relaxed', isExpired ? 'text-stone-600' : 'text-amber-900')}>
                    {cond}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className={cn('grid grid-cols-2 gap-4 border-t pt-4', isExpired ? 'border-stone-300' : 'border-amber-200')}>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Calendar size={16} className={isExpired ? 'text-stone-500' : 'text-amber-700'} />
              <span className={cn('text-xs', isExpired ? 'text-stone-600' : 'text-amber-800')}>建议复盘时间</span>
            </div>
            <div className={cn('text-sm font-bold', isExpired ? 'text-stone-800' : 'text-amber-950')}>
              {formatDate(decisionCard.review_at)}
            </div>
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Clock size={16} className={isExpired ? 'text-stone-500' : 'text-amber-700'} />
              <span className={cn('text-xs', isExpired ? 'text-stone-600' : 'text-amber-800')}>结论有效期</span>
            </div>
            <div className={cn('text-sm font-bold', isExpired ? 'text-stone-800' : 'text-amber-950')}>
              {formatDate(validUntil)}
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-3 rounded-3xl border border-stone-100 bg-white/80 p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">{isCampusConsumption ? '场景背景' : '市场背景'}</h3>
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

      {isCampusConsumption && (
        <section className="space-y-3 rounded-3xl border border-teal-100 bg-mist p-5">
          <div className="flex items-center gap-2 text-amber-700">
            <Calendar size={16} />
            <h3 className="text-xs font-bold uppercase tracking-widest text-teal-700">6 复盘闭环</h3>
          </div>
          <p className="text-sm leading-relaxed text-teal-950">
            本次行为已建议加入月底财务复盘。复盘时检查：是否仍想买、预算是否改善、是否找到替代方案。
          </p>
          <p className="text-xs leading-relaxed text-teal-800">
            系统会把本次风险标签用于后续提醒，帮助小林在下一次大额消费前更早看见同类风险。
          </p>
        </section>
      )}

      {!isCampusConsumption && (
      <section className="space-y-3 rounded-3xl border border-stone-100 bg-white/80 p-4">
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
      )}

      {!isCampusConsumption && (
      <section className="space-y-3 rounded-3xl border border-stone-100 bg-white/80 p-4">
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
                className="block rounded-2xl border border-stone-100 p-4 transition-colors hover:bg-stone-50"
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
      )}

      {!isCampusConsumption && (
      <button
        onClick={() => setShowDetails((current) => !current)}
        className="w-full py-4 text-stone-400 text-xs font-bold uppercase tracking-widest flex items-center justify-center gap-2"
      >
        {showDetails ? '收起更多数据' : '展开更多数据'}
        <ChevronDown size={14} className={cn('transition-transform', showDetails && 'rotate-180')} />
      </button>
      )}

      {!isCampusConsumption && showDetails && (
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
            {(analysis.analysis_template_version || analysis.analysis_policy_version) && (
              <div className="space-y-2">
                <h4 className="text-[10px] font-bold text-stone-400 uppercase tracking-widest">分析版本</h4>
                <div className="grid grid-cols-1 gap-2 text-xs">
                  {analysis.analysis_template_version && (
                    <div className="rounded-xl bg-white p-3">模板：{analysis.analysis_template_version}</div>
                  )}
                  {analysis.analysis_policy_version && (
                    <div className="rounded-xl bg-white p-3">策略：{analysis.analysis_policy_version}</div>
                  )}
                </div>
              </div>
            )}
          </div>
        </motion.div>
      )}

      <button
        onClick={() => setShowExplain(true)}
        className="flex w-full items-center justify-between rounded-3xl border border-teal-100 bg-mist p-4"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-teal-700 text-white">
            <MessageSquare size={20} />
          </div>
          <div className="text-left">
            <div className="text-sm font-bold text-teal-950">AI 解释层</div>
            <div className="text-[10px] font-medium text-teal-700">
              {analysis.status === 'partial_ready' && !analysis.explanation_layer
                ? '解释层数据暂时缺失'
                : '把这张分析卡片讲得更直白一点'}
            </div>
          </div>
        </div>
        <ChevronDown size={20} className="-rotate-90 text-teal-500" />
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
              className="safe-bottom fixed bottom-0 left-1/2 z-50 w-full max-w-lg -translate-x-1/2 rounded-t-[32px] bg-white p-6"
            >
              <div className="w-12 h-1.5 bg-stone-200 rounded-full mx-auto mb-6" />
              <div className="space-y-6">
                <div className="space-y-2">
                  <h3 className="text-xl font-bold">AI 解释层</h3>
                  <p className="text-sm text-stone-600 leading-relaxed">
                    {analysis.explanation_layer?.plain_text || '暂无解释文本'}
                  </p>
                </div>
                <div className="space-y-2 rounded-2xl bg-mist p-4">
                  <h4 className="text-xs font-bold uppercase tracking-widest text-teal-900">生活化类比</h4>
                  <p className="text-sm italic text-teal-800">
                    “{analysis.explanation_layer?.case_example || '暂无类比说明'}”
                  </p>
                </div>
                <button
                  onClick={() => setShowExplain(false)}
                  className="primary-action w-full"
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
              className="safe-bottom fixed bottom-0 left-1/2 z-50 w-full max-w-lg -translate-x-1/2 rounded-t-[32px] bg-white p-6"
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
                  <label className="text-sm font-semibold">你为什么要继续关注这个事项？</label>
                  <textarea
                    placeholder="例如：7 天后重新确认必要性、观察预算是否充足、比较替代方案"
                    className="h-32 w-full resize-none rounded-2xl border border-stone-200 bg-stone-50 p-4 text-sm focus:ring-2 focus:ring-teal-700/25"
                    maxLength={100}
                    value={focusReason}
                    onChange={(event) => setFocusReason(event.target.value)}
                  />
                  <div className="text-right text-xs text-stone-400">{focusReason.length}/100</div>
                </div>
                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => setShowFocusReasonModal(false)}
                    className="flex-1 rounded-2xl bg-stone-100 py-4 font-bold text-stone-700"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleSaveFocusReason}
                    disabled={!focusReason.trim() || savingReason}
                    className="flex-1 rounded-2xl bg-teal-700 py-4 font-bold text-white disabled:opacity-30"
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

      <div className="safe-bottom fixed bottom-0 left-1/2 z-30 w-full max-w-lg -translate-x-1/2 border-t border-stone-100 bg-white/90 p-4 backdrop-blur-xl">
        <div className="grid grid-cols-[48px_1fr_1fr] gap-2">
          <button
            onClick={handleCreateShare}
            disabled={sharing}
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-stone-100 text-sm font-bold text-ink transition-colors hover:bg-stone-200 disabled:opacity-40"
            title="生成分享卡片"
          >
            <Share2 size={18} />
          </button>
          <button
            onClick={() => setShowFocusReasonModal(true)}
            className="min-w-0 rounded-2xl bg-stone-100 px-2 py-3 text-sm font-bold text-ink transition-colors hover:bg-stone-200"
          >
            <span className="block truncate">{isCampusConsumption ? '记录复盘理由' : '记录关注理由'}</span>
          </button>
          <button
            onClick={isInWatchlist ? handleRemoveFromWatchlist : handleAddToWatchlist}
            className={cn(
              'min-w-0 rounded-2xl px-2 py-3 text-sm font-bold transition-colors',
              isInWatchlist
                ? 'bg-amber-50 text-amber-700 hover:bg-amber-100'
                : 'bg-teal-700 text-white hover:bg-teal-800'
            )}
          >
            <span className="block truncate">
              {isCampusConsumption
                ? (isInWatchlist ? '移出复盘清单' : '加入月底复盘')
                : (isInWatchlist ? '移出观察列表' : '加入观察列表')}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}
