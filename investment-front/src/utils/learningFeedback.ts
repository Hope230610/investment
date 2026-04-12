/**
 * Learning Feedback computation utilities.
 *
 * Takes the PostTradeInput form payload + the analysis detail response,
 * computes the LearningFeedbackData structure that powers the
 * LearningFeedbackCard component.
 */

import type {
  LearningFeedbackData,
  JudgmentQualityLevel,
  TagUpdate,
  EmotionDataPoint,
} from '../components/LearningFeedbackCard';


// ─── Judgment quality mapping ────────────────────────────────────────────────────

const JUDGMENT_SCORE: Record<string, number> = {
  '主要来自判断': 100,
  '部分判断 + 部分运气': 50,
  '主要来自运气': 0,
  '难以区分': -1, // excluded from calculation
};

const JUDGMENT_BREAKDOWN_PCT = {
  '主要来自判断': 45,
  '部分判断 + 部分运气': 30,
  '主要来自运气': 20,
  '难以区分': 5,
};

function computeJudgmentLevel(pct: number): JudgmentQualityLevel {
  if (pct >= 80) return 'high';
  if (pct >= 60) return 'medium';
  return 'low';
}

function computeJudgmentTrend(
  recentPcts: number[],
  count: number,
): { direction: 'up' | 'down' | 'stable'; description: string; insufficient: boolean } {
  if (count < 3) {
    return { direction: 'stable', description: '数据积累中', insufficient: true };
  }
  const recent = recentPcts.slice(-7); // last 7 entries
  const avg = recent.reduce((a, b) => a + b, 0) / recent.length;
  const prev = recentPcts.length > 7
    ? recentPcts.slice(-14, -7).reduce((a, b) => a + b, 0) / 7
    : avg;
  const delta = avg - prev;
  if (delta >= 3) return { direction: 'up', description: '近7天持续提升', insufficient: false };
  if (delta <= -3) return { direction: 'down', description: '近7天有所下滑', insufficient: false };
  return { direction: 'stable', description: '近7天基本稳定', insufficient: false };
}

function computeJudgmentSuggestion(level: JudgmentQualityLevel): string {
  if (level === 'high') return '继续保持当前的决策节奏，你的判断质量稳定';
  if (level === 'medium') return '注意在情绪略高时暂停决策，降低冲动交易比例';
  return '建议近期降低交易频率，等情绪平复后再做判断';
}


// ─── Tag inference ─────────────────────────────────────────────────────────────

function inferTagUpdates(
  scenarioPayload: Record<string, unknown>,
  behaviorPatterns: string[],
): TagUpdate[] {
  const updates: TagUpdate[] = [];
  const intent = scenarioPayload?.intent as string | undefined;
  const trigger = scenarioPayload?.trigger_reason as string | undefined;
  const patterns = behaviorPatterns || [];

  // System-detected: chasing
  if (
    (intent === 'buy' || intent === 'add_position') &&
    (trigger === '连续上涨' || trigger === '看到大涨')
  ) {
    updates.push({
      tag: '追涨倾向',
      type: 'add',
      source: '连续上涨触发 + 本次复盘确认',
    });
  }

  // System-detected: panic sell
  if (
    (intent === 'sell' || intent === 'reduce_position') &&
    (trigger === '快速下跌' || trigger === '恐慌性抛盘')
  ) {
    updates.push({
      tag: '恐慌卖出',
      type: 'add',
      source: '快速下跌触发 + 本次复盘确认',
    });
  }

  // User-confirmed patterns
  const tagNameMap: Record<string, string> = {
    '追涨倾向': '追涨倾向',
    '恐慌卖出': '恐慌卖出',
    '频繁交易': '频繁交易',
    '纪律稳定': '纪律稳定',
    '计划执行偏差': '计划执行偏差',
    '情绪主导决策': '情绪主导决策',
  };

  for (const pattern of patterns) {
    const existing = updates.find(u => u.tag === pattern);
    if (!existing) {
      updates.push({
        tag: tagNameMap[pattern] || pattern,
        type: 'add',
        source: '本次复盘确认',
      });
    }
  }

  return updates;
}


// ─── Emotion history ────────────────────────────────────────────────────────────

function buildEmotionHistory(
  currentLevel: number,
  _scenarioPayload: Record<string, unknown>,
  realEmotionHistory?: { date: string; level: number }[],
): { date: string; level: number }[] {
  // 优先使用真实 API 数据（从 learningHistory 传入）
  if (realEmotionHistory && realEmotionHistory.length > 0) {
    return realEmotionHistory;
  }
  // Fallback: 合成数据（Phase 2 接入初期保留，API 失败时降级）
  // TODO(backend): 生产验证后移除此 fallback
  const history: { date: string; level: number }[] = [];
  const now = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const noise = (Math.sin(i * 0.7) * 0.8 + (Math.random() - 0.5) * 1.2);
    const level = Math.max(1, Math.min(5, Math.round(2.4 + noise)));
    history.push({
      date: d.toISOString().slice(0, 10),
      level,
    });
  }
  return history;
}


// ─── Main export ───────────────────────────────────────────────────────────────

export interface ReviewFormData {
  actionTaken: string;
  outcomeSummary: string;
  planDeviation: boolean | null;
  judgementQuality: string;
  behaviorPatterns: string[];
  emotionLevel: number;
}

/**
 * Compute LearningFeedbackData from the review form payload and
 * the analysis detail response.
 *
 * Returns null when insufficient data is available.
 */
export function computeLearningFeedback(
  formData: ReviewFormData,
  scenarioPayload: Record<string, unknown> | null,
  existingJudgmentHistory: number[] = [], // past judgment quality percentages
  emotionHistory?: { date: string; level: number }[], // 真实 API 数据
): LearningFeedbackData | null {
  const payload = scenarioPayload || {};

  const judgementScore = JUDGMENT_SCORE[formData.judgementQuality] ?? -1;

  // "难以区分"：不计入历史，不算百分比重写，但行为标签和情绪数据仍展示
  const isHardToTell = formData.judgementQuality === '难以区分';

  // 非"难以区分"选项且无历史时返回 null
  if (!isHardToTell && judgementScore < 0 && existingJudgmentHistory.length === 0) return null;

  // 聚合：排除"难以区分"后再算百分比
  const validHistory = isHardToTell ? existingJudgmentHistory : [...existingJudgmentHistory, judgementScore];
  const qualityPercent = validHistory.length > 0
    ? Math.round(validHistory.reduce((s, v) => s + v, 0) / validHistory.length)
    : 0;
  const delta = existingJudgmentHistory.length > 0 && !isHardToTell
    ? qualityPercent - Math.round(existingJudgmentHistory.reduce((s, v) => s + v, 0) / existingJudgmentHistory.length)
    : 0;

  const breakdown = { ...JUDGMENT_BREAKDOWN_PCT };
  if (isHardToTell) {
    breakdown['难以区分'] = 100;
    breakdown['主要来自判断'] = 0;
    breakdown['部分判断+运气'] = 0;
    breakdown['主要来自运气'] = 0;
  }

  return {
    tagUpdates: inferTagUpdates(payload, formData.behaviorPatterns),
    judgmentQualityPercent: qualityPercent,
    judgmentQualityDelta: delta,
    judgmentLevel: isHardToTell ? 'medium' : computeJudgmentLevel(qualityPercent),
    judgmentBreakdown: {
      mainlyJudgment: breakdown['主要来自判断'],
      partialJudgment: breakdown['部分判断+运气'],
      mainlyLuck: breakdown['主要来自运气'],
      hardToTell: breakdown['难以区分'],
    },
    judgmentTrend: computeJudgmentTrend(validHistory, validHistory.length),
    suggestion: isHardToTell
      ? '判断质量待积累，继续保持复盘习惯'
      : computeJudgmentSuggestion(computeJudgmentLevel(qualityPercent)),
    emotionHistory: buildEmotionHistory(formData.emotionLevel, payload, emotionHistory),
    currentEmotionLevel: formData.emotionLevel,
    isHardToTell,
  };
}
