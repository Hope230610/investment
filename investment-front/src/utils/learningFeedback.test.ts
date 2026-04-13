/**
 * Unit tests for learningFeedback.ts
 *
 * Coverage:
 * - Judgment quality scoring
 * - Hard-to-tell case (不计入历史，但展示中性卡面)
 * - Tag inference (追涨倾向 / 恐慌卖出 / user-confirmed patterns)
 * - Emotion history fallback vs real API data
 * - Delta calculation (no delta on first entry)
 * - Trend direction (up / down / stable / insufficient)
 * - Null return when no history and invalid quality option
 */

import { describe, it, expect } from 'vitest';
import {
  computeLearningFeedback,
  type ReviewFormData,
} from './learningFeedback';


// ─── Shared helpers ────────────────────────────────────────────────────────────

function makeForm(overrides: Partial<ReviewFormData> = {}): ReviewFormData {
  return {
    actionTaken: 'continued',
    outcomeSummary: '赚了5%',
    planDeviation: false,
    judgementQuality: '主要来自判断',
    behaviorPatterns: [],
    emotionLevel: 2,
    ...overrides,
  };
}


// ─── Judgment quality scoring ─────────────────────────────────────────────────

describe('Judgment quality scoring', () => {
  it('maps 主要来自判断 to 100%', () => {
    const result = computeLearningFeedback(makeForm({ judgementQuality: '主要来自判断' }), null, []);
    expect(result).not.toBeNull();
    expect(result!.judgmentQualityPercent).toBe(100);
    expect(result!.judgmentLevel).toBe('high');
  });

  it('maps 部分判断 + 部分运气 to 50% (level = low, since 50 < 60 threshold)', () => {
    const result = computeLearningFeedback(makeForm({ judgementQuality: '部分判断 + 部分运气' }), null, []);
    expect(result).not.toBeNull();
    expect(result!.judgmentQualityPercent).toBe(50);
    expect(result!.judgmentLevel).toBe('low');
  });

  it('maps 主要来自运气 to 0%', () => {
    const result = computeLearningFeedback(makeForm({ judgementQuality: '主要来自运气' }), null, []);
    expect(result).not.toBeNull();
    expect(result!.judgmentQualityPercent).toBe(0);
    expect(result!.judgmentLevel).toBe('low');
  });
});


// ─── Hard-to-tell case ────────────────────────────────────────────────────────

describe('难以区分 (hard-to-tell)', () => {
  it('returns neutral card (not null) even with no existing history', () => {
    const result = computeLearningFeedback(
      makeForm({ judgementQuality: '难以区分' }),
      null,
      [],
    );
    expect(result).not.toBeNull();
    expect(result!.isHardToTell).toBe(true);
  });

  it('sets breakdown hard-to-tell to 100%', () => {
    const result = computeLearningFeedback(
      makeForm({ judgementQuality: '难以区分' }),
      null,
      [80],
    );
    expect(result!.judgmentBreakdown.hardToTell).toBe(100);
    expect(result!.judgmentBreakdown.mainlyJudgment).toBe(0);
    expect(result!.judgmentBreakdown.partialJudgment).toBe(0);
    expect(result!.judgmentBreakdown.mainlyLuck).toBe(0);
  });

  it('does NOT add hard-to-tell score to history aggregation', () => {
    const result = computeLearningFeedback(
      makeForm({ judgementQuality: '难以区分' }),
      null,
      [80],
    );
    expect(result!.judgmentQualityPercent).toBe(80);
  });

  it('suggestion is neutral accumulate message', () => {
    const result = computeLearningFeedback(
      makeForm({ judgementQuality: '难以区分' }),
      null,
      [60],
    );
    expect(result!.suggestion).toContain('继续保持复盘习惯');
  });
});


// ─── History aggregation ──────────────────────────────────────────────────────

describe('History aggregation', () => {
  it('averages across existing history', () => {
    // [80, 80] + 0 → (80+80+0)/3 ≈ 53
    const result = computeLearningFeedback(
      makeForm({ judgementQuality: '主要来自运气' }),
      null,
      [80, 80],
    );
    expect(result!.judgmentQualityPercent).toBe(53);
  });

  it('returns null when judgementQuality is unknown and no history', () => {
    const result = computeLearningFeedback(makeForm({ judgementQuality: '随便乱填' }), null, []);
    expect(result).toBeNull();
  });

  it('delta is 0 on first entry', () => {
    const result = computeLearningFeedback(makeForm({ judgementQuality: '主要来自判断' }), null, []);
    expect(result!.judgmentQualityDelta).toBe(0);
  });

  it('delta is new_avg - old_avg when history exists', () => {
    // existing avg: (100+100)/2=100, new score: 50
    // new avg: (100+100+50)/3≈83, delta: 83-100=-17
    const result = computeLearningFeedback(
      makeForm({ judgementQuality: '部分判断 + 部分运气' }),
      null,
      [100, 100],
    );
    expect(result!.judgmentQualityDelta).toBe(-17);
  });
});


// ─── Tag inference ───────────────────────────────────────────────────────────

describe('Tag inference', () => {
  it('infers 追涨倾向 when buy intent + 连续上涨 trigger', () => {
    const result = computeLearningFeedback(makeForm(), { intent: 'buy', trigger_reason: '连续上涨' }, [50]);
    expect(result!.tagUpdates).toContainEqual(
      expect.objectContaining({ tag: '追涨倾向', type: 'add' }),
    );
  });

  it('infers 追涨倾向 when add_position + 看到大涨', () => {
    const result = computeLearningFeedback(makeForm(), { intent: 'add_position', trigger_reason: '看到大涨' }, [50]);
    expect(result!.tagUpdates).toContainEqual(
      expect.objectContaining({ tag: '追涨倾向', type: 'add' }),
    );
  });

  it('infers 恐慌卖出 when sell intent + 快速下跌', () => {
    const result = computeLearningFeedback(makeForm(), { intent: 'sell', trigger_reason: '快速下跌' }, [50]);
    expect(result!.tagUpdates).toContainEqual(
      expect.objectContaining({ tag: '恐慌卖出', type: 'add' }),
    );
  });

  it('infers 恐慌卖出 when reduce_position + 恐慌性抛盘', () => {
    const result = computeLearningFeedback(makeForm(), { intent: 'reduce_position', trigger_reason: '恐慌性抛盘' }, [50]);
    expect(result!.tagUpdates).toContainEqual(
      expect.objectContaining({ tag: '恐慌卖出', type: 'add' }),
    );
  });

  it('adds user-confirmed patterns from behaviorPatterns array', () => {
    const result = computeLearningFeedback(
      makeForm({ behaviorPatterns: ['追涨倾向', '频繁交易'] }),
      null,
      [50],
    );
    const tags = result!.tagUpdates.map(u => u.tag);
    expect(tags).toContain('追涨倾向');
    expect(tags).toContain('频繁交易');
  });

  it('does not duplicate tags already inferred from payload', () => {
    const result = computeLearningFeedback(
      makeForm({ behaviorPatterns: ['追涨倾向'] }),
      { intent: 'buy', trigger_reason: '连续上涨' },
      [50],
    );
    const count = result!.tagUpdates.filter(u => u.tag === '追涨倾向').length;
    expect(count).toBe(1);
  });

  it('infers nothing when no matching triggers', () => {
    const result = computeLearningFeedback(makeForm(), { intent: 'hold', trigger_reason: '观望' }, [50]);
    expect(result!.tagUpdates).toHaveLength(0);
  });
});


// ─── Emotion history ───────────────────────────────────────────────────────────

describe('Emotion history', () => {
  it('uses real API data when provided', () => {
    const realHistory = [
      { date: '2026-04-10', level: 2 },
      { date: '2026-04-11', level: 3 },
    ];
    const result = computeLearningFeedback(
      makeForm({ emotionLevel: 4 }),
      null,
      [50],
      realHistory,
    );
    expect(result!.emotionHistory).toEqual(realHistory);
  });

  it('falls back to synthetic data when no real history', () => {
    const result = computeLearningFeedback(makeForm({ emotionLevel: 3 }), null, [50]);
    expect(result!.emotionHistory.length).toBeGreaterThan(0);
    result!.emotionHistory.forEach(point => {
      expect(typeof point.date).toBe('string');
      expect(point.level).toBeGreaterThanOrEqual(1);
      expect(point.level).toBeLessThanOrEqual(5);
    });
  });

  it('synthetic data generates exactly 30 days', () => {
    const result = computeLearningFeedback(makeForm({ emotionLevel: 2 }), null, [50]);
    expect(result!.emotionHistory).toHaveLength(30);
  });
});


// ─── Judgment level thresholds ────────────────────────────────────────────────

describe('Judgment level thresholds', () => {
  it('high when aggregated percent >= 80', () => {
    // [100] + 100 → avg = 100 → high
    const result = computeLearningFeedback(makeForm({ judgementQuality: '主要来自判断' }), null, [100]);
    expect(result!.judgmentLevel).toBe('high');
  });

  it('medium when aggregated percent >= 60 and < 80', () => {
    // [50] + 100 → avg = 75, which is >= 60 and < 80 → medium
    const result = computeLearningFeedback(makeForm({ judgementQuality: '主要来自判断' }), null, [50]);
    expect(result!.judgmentLevel).toBe('medium');
  });

  it('low when aggregated percent < 60', () => {
    // [20, 20] + 100 → avg = (100+20+20)/3 ≈ 47 → low
    const result = computeLearningFeedback(makeForm({ judgementQuality: '主要来自判断' }), null, [20, 20]);
    expect(result!.judgmentLevel).toBe('low');
  });
});


// ─── Judgment trend ───────────────────────────────────────────────────────────

describe('Judgment trend', () => {
  it('marks insufficient when valid history count < 3', () => {
    // [50, 50] + 新分数 100 → validHistory 长度 = 3，不是 < 3
    // 用 [50] → validHistory 长度 = 2，< 3 → insufficient
    const result = computeLearningFeedback(makeForm(), null, [50]);
    expect(result!.judgmentTrend.insufficient).toBe(true);
  });

  it('marks sufficient when valid history count >= 3', () => {
    // [50, 50] + 新分数 100 → 3 项 → sufficient
    const result = computeLearningFeedback(makeForm(), null, [50, 50]);
    expect(result!.judgmentTrend.insufficient).toBe(false);
  });
});


// ─── Suggestion text ─────────────────────────────────────────────────────────

describe('Suggestion text', () => {
  it('high level: positive message', () => {
    // [100] alone → avg = (100+100)/2 = 100 → high
    const result = computeLearningFeedback(makeForm({ judgementQuality: '主要来自判断' }), null, [100]);
    expect(result!.suggestion).toContain('继续保持');
  });

  it('medium level: caution message', () => {
    // [50] + 100 → avg = 75 → medium
    const result = computeLearningFeedback(makeForm({ judgementQuality: '主要来自判断' }), null, [50]);
    expect(result!.suggestion).toContain('注意');
  });

  it('low level: reduce frequency message', () => {
    // [20, 20] + 100 → avg ≈ 47 → low
    const result = computeLearningFeedback(makeForm({ judgementQuality: '主要来自判断' }), null, [20, 20]);
    expect(result!.suggestion).toContain('降低交易频率');
  });
});


// ─── Null safety ──────────────────────────────────────────────────────────────

describe('Null safety', () => {
  it('returns feedback card when scenarioPayload is null', () => {
    const result = computeLearningFeedback(makeForm(), null, [50]);
    expect(result).not.toBeNull();
    expect(result!.tagUpdates).toHaveLength(0);
  });

  it('returns feedback card when scenarioPayload is empty object', () => {
    const result = computeLearningFeedback(makeForm(), {}, [50]);
    expect(result).not.toBeNull();
  });

  it('handles null planDeviation', () => {
    const result = computeLearningFeedback(makeForm({ planDeviation: null }), null, [50]);
    expect(result).not.toBeNull();
  });
});
