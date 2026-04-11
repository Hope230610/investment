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
): { direction: 'up' | 'down' | 'stable'; description: string } {
  if (recentPcts.length < 2) return { direction: 'stable', description: '数据不足' };
  const recent = recentPcts.slice(-7); // last 7 entries
  const avg = recent.reduce((a, b) => a + b, 0) / recent.length;
  const prev = recentPcts.length > 7
    ? recentPcts.slice(-14, -7).reduce((a, b) => a + b, 0) / 7
    : avg;
  const delta = avg - prev;
  if (delta >= 3) return { direction: 'up', description: '近7天持续提升' };
  if (delta <= -3) return { direction: 'down', description: '近7天有所下滑' };
  return { direction: 'stable', description: '近7天基本稳定' };
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
): EmotionDataPoint[] {
  // TODO(backend): replace with real API call to emotion history endpoint
  // For now, generate synthetic history for demo
  const history: EmotionDataPoint[] = [];
  const now = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    // Synthetic: slight random variation around 2.4 mean
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
): LearningFeedbackData | null {
  const payload = scenarioPayload || {};

  const judgementScore = JUDGMENT_SCORE[formData.judgementQuality] ?? -1;
  if (judgementScore < 0) return null;

  // Blend with existing history
  const recentHistory = [...existingJudgmentHistory, judgementScore];
  const totalScore = recentHistory.reduce((s, v) => s + v, 0);
  const count = recentHistory.length;
  const qualityPercent = Math.round(totalScore / count);
  const delta = existingJudgmentHistory.length > 0
    ? qualityPercent - Math.round(existingJudgmentHistory.reduce((s, v) => s + v, 0) / existingJudgmentHistory.length)
    : 0;

  const breakdown = { ...JUDGMENT_BREAKDOWN_PCT };
  if (formData.judgementQuality === '难以区分') {
    breakdown['难以区分'] = 100;
    breakdown['主要来自判断'] = 0;
    breakdown['部分判断+运气'] = 0;
    breakdown['主要来自运气'] = 0;
  }

  return {
    tagUpdates: inferTagUpdates(payload, formData.behaviorPatterns),
    judgmentQualityPercent: qualityPercent,
    judgmentQualityDelta: delta,
    judgmentLevel: computeJudgmentLevel(qualityPercent),
    judgmentBreakdown: {
      mainlyJudgment: breakdown['主要来自判断'],
      partialJudgment: breakdown['部分判断+运气'],
      mainlyLuck: breakdown['主要来自运气'],
      hardToTell: breakdown['难以区分'],
    },
    judgmentTrend: computeJudgmentTrend(recentHistory),
    suggestion: computeJudgmentSuggestion(computeJudgmentLevel(qualityPercent)),
    emotionHistory: buildEmotionHistory(formData.emotionLevel, payload),
    currentEmotionLevel: formData.emotionLevel,
  };
}
