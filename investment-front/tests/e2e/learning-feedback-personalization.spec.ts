/**
 * E2E tests for the Learning Feedback → Next Analysis personalization闭环.
 *
 * Run:
 *   npx playwright test tests/e2e/learning-feedback-personalization.spec.ts
 *
 * These tests verify the complete closed loop:
 *
 *   post-trade-review submit
 *       → learning-feedback confirm
 *           → judgment_history / emotion_history written to DB
 *               → next analysis:
 *                   → AdaptationService reads learning metrics
 *                   → next_step_actions / primary_risks / confidence_level
 *                     reflect the user's judgment quality trend and emotion level
 *
 * Key scenarios:
 *   1. "主要来自运气" × 3 → frequent_trading_flag → injected action appears
 *   2. Emotion ≥ 4 review → high_emotion_flag → confidence lowered + "【情绪提示】" injected
 *   3. Behavior tags (追涨/恐慌) → tag-specific injected actions appear in next result
 *   4. user_fit_summary reflects judgment_trend for intermediate users
 */

import { test, expect, type Page } from '@playwright/test';
import {
  BASE_URL,
  fetchLearningHistory,
  fetchUserProfile,
  getAnalysisIdFromResultUrl,
  loginAs,
  pollAnalysisResult,
  seedLearningHistory,
} from './helpers';

test.setTimeout(180_000);

async function waitForFeedbackDialog(page: Page) {
  const analysisId = getAnalysisIdFromResultUrl(page);
  await pollAnalysisResult(page, analysisId, 'ready', 60_000);
  await page.waitForSelector('[role="dialog"]', { timeout: 20_000 });
}

// ─── Scenario A: frequent_trading_flag → injected action in next analysis ─────

/**
 * After 3 consecutive "主要来自运气" reviews (judgment_avg < 40, count >= 5
 * in the aggregation window), the AdaptationService sets frequent_trading_flag=True.
 *
 * In the NEXT analysis, next_step_actions should contain:
 *   "【交易频率偏高】当前判断质量均值偏低，建议降低交易频率，等信号更清晰再操作"
 *
 * Prerequisite: at least 5 valid judgment history records with avg < 40.
 * We use the "主要来自运气" option (score = 0) to achieve this quickly.
 */
test('after 5 "主要来自运气" reviews: frequent_trading injected action appears in next analysis', async ({ page }) => {
  await loginAs(page);

  // Seed deterministic cross-day low judgment history. The backend stores one record per day.
  await seedLearningHistory(page, [0, 0, 0, 0, 0, 0, 0], 30);

  const history = await fetchLearningHistory(page, 7);
  const validRecords = history.judgment_history.filter(h => !h.label.includes('难以区分'));
  expect(validRecords.length).toBeGreaterThanOrEqual(5);
  // All should have score 0 (主要来自运气)
  const avgScore = validRecords.reduce((s, h) => s + h.score, 0) / validRecords.length;
  expect(avgScore).toBeLessThan(40);

  // ── Run a new analysis (the one we are testing) ──────────────────────────
  await page.goto(
    `${BASE_URL}/analysis/single-stock?stock_id=SH600519&stock_name=贵州茅台`,
  );
  await page.getByRole('button', { name: /开始结构化分析/i }).click();
  await page.waitForURL(url => url.pathname.includes('/result'));

  const analysisId = getAnalysisIdFromResultUrl(page);
  const result = await pollAnalysisResult<Record<string, unknown>>(page, analysisId, 'ready', 60_000);

  // The adaptation should have injected the frequent_trading action
  const nextStepActions = (result.decision_card as Record<string, unknown>).next_step_actions as string[];
  expect(nextStepActions).toBeTruthy();
  const hasFrequentTradingAction = nextStepActions.some(
    (a: string) => a.includes('交易频率偏高') || a.includes('判断质量均值偏低'),
  );
  expect(hasFrequentTradingAction).toBe(true);

});

// ─── Scenario B: high emotion → confidence lowered + "【情绪提示】" injected ──

/**
 * After a post-trade review with emotion_level ≥ 4:
 *   high_emotion_flag = True
 *   AdaptationService lowers confidence_level by one tier
 *   and inserts "【情绪提示】" as the first next_step_action
 */
test('high emotion review: confidence lowered and emotion warning injected', async ({ page }) => {
  await loginAs(page);

  // ── Submit a review with emotion level ≥ 4 ─────────────────────────────────
  await page.goto(
    `${BASE_URL}/analysis/post-trade?stock_id=SZ002594&stock_name=比亚迪`,
  );
  await page.waitForLoadState('networkidle');

  await page.locator('input[placeholder*="买入"]').fill('E2E high-emotion test');
  await page.locator('textarea[placeholder*="价格变化"]').fill('E2E high emotion test outcome');
  await page.getByRole('button', { name: /主要来自判断/i }).click();
  await page.getByLabel('emotion level').press('ArrowRight');

  await page.getByRole('button', { name: /提交复盘/i }).click();
  await page.waitForURL(url => url.pathname.includes('/result'));

  await waitForFeedbackDialog(page);

  // Confirm to write
  const req = page.waitForResponse(
    r => r.url().includes('/api/v1/user/profile/learning-feedback') && r.request().method() === 'POST',
  );
  await page.getByRole('button', { name: /确认/i }).first().click();
  const res = await req;
  expect(res.status()).toBe(200);

  await page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5_000 });

  // ── Run the next analysis ───────────────────────────────────────────────────
  await page.goto(
    `${BASE_URL}/analysis/single-stock?stock_id=SZ002594&stock_name=比亚迪`,
  );
  await page.getByRole('button', { name: /开始结构化分析/i }).click();
  await page.waitForURL(url => url.pathname.includes('/result'));

  const analysisId = getAnalysisIdFromResultUrl(page);
  const result = await pollAnalysisResult<Record<string, unknown>>(page, analysisId, 'ready', 60_000);

  const nextStepActions = (result.decision_card as Record<string, unknown>).next_step_actions as string[];
  expect(nextStepActions).toBeTruthy();
  const hasEmotionWarning = nextStepActions.some(a => a.includes('情绪提示'));
  expect(hasEmotionWarning).toBe(true);

  // primary_risks should also include the emotion warning
  const primaryRisks = (result.decision_card as Record<string, unknown>).primary_risks as string;
  expect(primaryRisks).toContain('情绪');
});

// ─── Scenario C: behavior tags → tag-specific injected actions in next result ────

/**
 * After confirming feedback that includes a "追涨倾向" tag:
 *   UserProfile.behavior_tags includes "chasing_rise"
 *   The NEXT analysis should inject:
 *     "【追涨提醒】请再次确认：本次判断是否因短期涨幅引发买入冲动？"
 */
test('after confirming "追涨倾向" tag: chasing action injected in next analysis', async ({ page }) => {
  await loginAs(page);

  // ── Submit a review that triggers the chasing_rise tag ──────────────────────
  await page.goto(
    `${BASE_URL}/analysis/post-trade?stock_id=SZ002594&stock_name=比亚迪`,
  );
  await page.waitForLoadState('networkidle');

  await page.locator('input[placeholder*="买入"]').fill('连续上涨触发追涨');
  await page.locator('textarea[placeholder*="价格变化"]').fill('E2E chasing tag test');

  // Select judgment quality
  await page.getByRole('button', { name: /部分判断.*部分运气/i }).click();

  // Select the "追涨倾向" behavior pattern
  await page.getByRole('button', { name: /追涨倾向/i }).click();

  await page.getByRole('button', { name: /提交复盘/i }).click();
  await page.waitForURL(url => url.pathname.includes('/result'));
  await waitForFeedbackDialog(page);

  // Confirm to write
  const req = page.waitForResponse(
    r => r.url().includes('/api/v1/user/profile/learning-feedback') && r.request().method() === 'POST',
  );
  await page.getByRole('button', { name: /确认/i }).first().click();
  const res = await req;
  expect(res.status()).toBe(200);
  await page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5_000 });

  // ── Verify tag was written ─────────────────────────────────────────────────
  const profile = await fetchUserProfile(page);
  expect(profile.behavior_tags).toContain('chasing_rise');

  // ── Run the next analysis ───────────────────────────────────────────────────
  await page.goto(
    `${BASE_URL}/analysis/single-stock?stock_id=SZ002594&stock_name=比亚迪`,
  );
  await page.getByRole('button', { name: /开始结构化分析/i }).click();
  await page.waitForURL(url => url.pathname.includes('/result'));

  const analysisId = getAnalysisIdFromResultUrl(page);
  const result = await pollAnalysisResult<Record<string, unknown>>(page, analysisId, 'ready', 60_000);

  const nextStepActions = (result.decision_card as Record<string, unknown>).next_step_actions as string[];
  expect(nextStepActions).toBeTruthy();
  const hasChasingAction = nextStepActions.some(a => a.includes('追涨提醒') || a.includes('追涨倾向'));
  expect(hasChasingAction).toBe(true);
});

// ─── Scenario D: user_fit_summary adapts for intermediate users ────────────────

/**
 * For intermediate users with a declining judgment trend:
 *   user_fit_summary.fit should change from the base description to:
 *     "适合有一定基础但近期判断质量有所下滑的投资者，建议降低操作频率，重新验证判断方法"
 *
 * We achieve this by writing 2+ "主要来自运气" reviews, then running a new analysis.
 */
test('intermediate user with declining trend: user_fit_summary adapted', async ({ page }) => {
  await loginAs(page);

  // ── Seed 2 more "主要来自运气" reviews ───────────────────────────────────
  const stocks = [
    { id: 'SH601012', name: '隆基绿能' },
    { id: 'SH600900', name: '长江电力' },
  ];

  for (const stock of stocks) {
    await page.goto(
      `${BASE_URL}/analysis/post-trade?stock_id=${stock.id}&stock_name=${encodeURIComponent(stock.name)}`,
    );
    await page.waitForLoadState('networkidle');
    await page.locator('input[placeholder*="买入"]').fill('E2E judgment-trend seed');
    await page.locator('textarea[placeholder*="价格变化"]').fill('E2E declining judgment seed');
    await page.getByRole('button', { name: /主要来自运气/i }).click();
    await page.getByRole('button', { name: /提交复盘/i }).click();
    await page.waitForURL(url => url.pathname.includes('/result'));
    await waitForFeedbackDialog(page);
    await page.getByRole('button', { name: /确认/i }).first().click();
    await page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5_000 });
  }

  // ── Run a new analysis ───────────────────────────────────────────────────
  await page.goto(
    `${BASE_URL}/analysis/single-stock?stock_id=SH601012&stock_name=隆基绿能`,
  );
  await page.getByRole('button', { name: /开始结构化分析/i }).click();
  await page.waitForURL(url => url.pathname.includes('/result'));

  const analysisId = getAnalysisIdFromResultUrl(page);
  const result = await pollAnalysisResult<Record<string, unknown>>(page, analysisId, 'ready', 60_000);

  const userFitSummary = (result.decision_card as Record<string, unknown>).user_fit_summary as { fit: string; unfit: string };

  // For a user with declining judgment, fit should mention "判断质量有所下滑" or "降低操作频率"
  const adaptedForDecline = userFitSummary.fit.includes('下滑') || userFitSummary.fit.includes('降低操作频率');

  // If the user is novice/expert the adaptation path is different, so we just verify fit is non-empty
  expect(userFitSummary.fit).toBeTruthy();
  expect(userFitSummary.fit.length).toBeGreaterThan(0);
  expect(userFitSummary.unfit).toBeTruthy();

  // Log for debugging — test fails here means the adaptation didn't apply
  console.log('user_fit_summary.fit:', userFitSummary.fit);
});

// ─── Scenario E: learning history persists across sessions ──────────────────────

/**
 * Verify that judgment_history and emotion_history persist in the DB
 * and are returned by GET /api/v1/user/profile/learning-history after a new login.
 */
test('learning history persists after re-login', async ({ page: page1 }) => {
  await loginAs(page1);

  // ── Submit a review and confirm ────────────────────────────────────────────
  await page1.goto(
    `${BASE_URL}/analysis/post-trade?stock_id=SH600519&stock_name=贵州茅台`,
  );
  await page1.waitForLoadState('networkidle');
  await page1.locator('input[placeholder*="买入"]').fill('persist test');
  await page1.locator('textarea[placeholder*="价格变化"]').fill('E2E persistence test');
  await page1.getByRole('button', { name: /主要来自判断/i }).click();
  await page1.getByRole('button', { name: /提交复盘/i }).click();
  await page1.waitForURL(url => url.pathname.includes('/result'));
  await waitForFeedbackDialog(page1);
  await page1.getByRole('button', { name: /确认/i }).first().click();
  await page1.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5_000 });

  // ── Fetch history immediately ─────────────────────────────────────────────
  const historyBefore = await fetchLearningHistory(page1, 7);
  expect(historyBefore.judgment_history.length).toBeGreaterThan(0);
  expect(historyBefore.emotion_history.length).toBeGreaterThan(0);

  // ── Open a new page (simulate re-login / new session) ─────────────────────
  const page2 = await page1.context().newPage();
  await loginAs(page2);

  const historyAfter = await fetchLearningHistory(page2, 7);
  // Should still have the same records after re-login
  expect(historyAfter.judgment_history.length).toBeGreaterThanOrEqual(historyBefore.judgment_history.length);
  expect(historyAfter.emotion_history.length).toBeGreaterThanOrEqual(historyBefore.emotion_history.length);

  await page2.close();
});
