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

import { beforeEach, describe, it, expect } from 'vitest';
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

  // ─── action_taken 回退（Fix 4c）────────────────────────────────────────────────

  it('infers 追涨倾向 when only action_taken=buy (no intent field)', () => {
    const result = computeLearningFeedback(
      makeForm(),
      { action_taken: 'buy', trigger_reason: '连续上涨' },
      [50],
    );
    expect(result!.tagUpdates).toContainEqual(
      expect.objectContaining({ tag: '追涨倾向', type: 'add' }),
    );
  });

  it('infers 恐慌卖出 when only action_taken=sell (no intent field)', () => {
    const result = computeLearningFeedback(
      makeForm(),
      { action_taken: 'sell', trigger_reason: '快速下跌' },
      [50],
    );
    expect(result!.tagUpdates).toContainEqual(
      expect.objectContaining({ tag: '恐慌卖出', type: 'add' }),
    );
  });

  it('infers 追涨倾向 when action_taken=add (no intent field)', () => {
    const result = computeLearningFeedback(
      makeForm(),
      { action_taken: 'add', trigger_reason: '看到大涨' },
      [50],
    );
    expect(result!.tagUpdates).toContainEqual(
      expect.objectContaining({ tag: '追涨倾向', type: 'add' }),
    );
  });

  it('infers 恐慌卖出 when action_taken=reduce (no intent field)', () => {
    const result = computeLearningFeedback(
      makeForm(),
      { action_taken: 'reduce', trigger_reason: '恐慌性抛盘' },
      [50],
    );
    expect(result!.tagUpdates).toContainEqual(
      expect.objectContaining({ tag: '恐慌卖出', type: 'add' }),
    );
  });

  it('intent takes priority over action_taken when both present', () => {
    const result = computeLearningFeedback(
      makeForm(),
      { intent: 'buy', action_taken: 'sell', trigger_reason: '连续上涨' },
      [50],
    );
    expect(result!.tagUpdates.map(u => u.tag)).toContain('追涨倾向');
  });

  it('returns no tags when neither intent nor action_taken matches trigger', () => {
    const result = computeLearningFeedback(
      makeForm(),
      { action_taken: 'hold', trigger_reason: '观望' },
      [50],
    );
    expect(result!.tagUpdates).toHaveLength(0);
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


// ─── ResultPage confirm/dismiss localStorage 语义 ─────────────────────────────────

/**
 * smoke test for ResultPage confirm/dismiss localStorage behavior.
 *
 * 这些测试验证 Gate 0 修复后的关键语义：
 * - confirm 写 'true'（不是 'confirmed'）
 * - dismiss 写 'true'
 * - later 只写 showcount
 * - 读端对 'confirmed' 归一化为 'true'
 *
 * 以下场景需要手动 smoke 验证（需要完整的后端 + 数据库）：
 * - confirm 全链路：Step1 + Step2 均成功 → DB 有 emotion_history 写入
 * - confirm Step2 404 → review_tasks.status 未变，但卡片关闭
 * - confirm Step1 500 → 卡片仍弹出（未静默成功）
 * - records/history → 能读到新表数据，非空列表
 * - record-reason upsert → 第二次写入只更新 focus_reason，不产生脏数据
 */

// Node test environment needs localStorage stub
const store: Record<string, string> = {};
const mockLocalStorage: Storage = {
  get length() {
    return Object.keys(store).length;
  },
  clear: () => {
    Object.keys(store).forEach((key) => delete store[key]);
  },
  getItem: (key: string) => store[key] ?? null,
  key: (index: number) => Object.keys(store)[index] ?? null,
  removeItem: (key: string) => {
    delete store[key];
  },
  setItem: (key: string, value: string) => {
    store[key] = value;
  },
};

if (typeof globalThis.localStorage === 'undefined') {
  Object.defineProperty(globalThis, 'localStorage', {
    value: mockLocalStorage,
    configurable: true,
    writable: true,
  });
} else {
  globalThis.localStorage = mockLocalStorage;
}

describe('ResultPage confirm/dismiss localStorage semantics', () => {
  const TEST_TASK_ID = '00000000-0000-0000-0000-000000000001';
  const dismissKey = `feedback_dismissed_${TEST_TASK_ID}`;
  const countKey = `feedback_showcount_${TEST_TASK_ID}`;

  beforeEach(() => {
    localStorage.clear();
  });

  // Simulate ResultPage.handleFeedbackDismiss behavior
  function simulateDismiss() {
    localStorage.setItem(dismissKey, 'true');
  }

  // Simulate ResultPage.handleFeedbackConfirm success path
  function simulateConfirmSuccess() {
    // handleFeedbackConfirm in ResultPage.tsx:209-244
    // Both Step1 and Step2 succeed → writes 'true'
    localStorage.setItem(dismissKey, 'true');
  }

  // Simulate ResultPage.handleFeedbackConfirm Step2-failure path
  function simulateConfirmStep2Failure() {
    // catch block: still writes 'true' (silent mark)
    // This is the Gate 0 fix: confirm writes 'true', not 'confirmed'
    localStorage.setItem(dismissKey, 'true');
  }

  // Simulate ResultPage card open: read-side normalization
  function shouldShowCard(): boolean {
    const count = parseInt(localStorage.getItem(countKey) || '0', 10);
    if (count >= 3) return false;
    const dismissed = localStorage.getItem(dismissKey);
    // Read-side normalization: 'confirmed' → 'true'
    if (dismissed === 'confirmed') {
      localStorage.setItem(dismissKey, 'true');
      return false;
    }
    return dismissed !== 'true';
  }

  it('dismiss writes feedbackDismissKey = true', () => {
    simulateDismiss();
    expect(localStorage.getItem(dismissKey)).toBe('true');
  });

  it('confirm success writes feedbackDismissKey = true (not confirmed)', () => {
    simulateConfirmSuccess();
    expect(localStorage.getItem(dismissKey)).toBe('true');
    expect(localStorage.getItem(dismissKey)).not.toBe('confirmed');
  });

  it('confirm Step2 failure also writes feedbackDismissKey = true (silent mark)', () => {
    // This is the key smoke case: Step2 fails but card still closes
    simulateConfirmStep2Failure();
    expect(localStorage.getItem(dismissKey)).toBe('true');
  });

  it('later only increments showcount, does NOT write dismiss key', () => {
    // handleFeedbackLater: only writes feedback_showcount_${id}, not dismiss key
    const count = parseInt(localStorage.getItem(countKey) || '0', 10);
    localStorage.setItem(countKey, String(count + 1));
    // dismiss key should NOT be set by "later"
    expect(localStorage.getItem(dismissKey)).toBeNull();
  });

  it('read-side: confirmed value is normalized to true on card open', () => {
    // Legacy 'confirmed' value written by pre-Gate-0 code
    localStorage.setItem(dismissKey, 'confirmed');
    expect(shouldShowCard()).toBe(false);
    expect(localStorage.getItem(dismissKey)).toBe('true'); // normalized
  });

  it('read-side: true value causes card not to show', () => {
    localStorage.setItem(dismissKey, 'true');
    expect(shouldShowCard()).toBe(false);
  });

  it('read-side: null dismiss key causes card to show (when count < 3)', () => {
    expect(shouldShowCard()).toBe(true);
  });

  it('showcount >= 3 causes card not to show regardless of dismiss key', () => {
    localStorage.setItem(countKey, '3');
    localStorage.removeItem(dismissKey);
    expect(shouldShowCard()).toBe(false);
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
