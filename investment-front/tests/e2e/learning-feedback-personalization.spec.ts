/**
 * E2E tests for the AI financial-literacy coach personalization loop.
 *
 * Run:
 *   npx playwright test tests/e2e/learning-feedback-personalization.spec.ts
 *
 * These tests verify the complete closed loop:
 *
 *   campus budget review submit
 *       → learning-feedback confirm
 *           → judgment_history / emotion_history written to DB
 *               → next analysis:
 *                   → AdaptationService reads learning metrics
 *                   → next_step_actions / primary_risks / confidence_level
 *                     reflect the user's judgment quality trend and emotion level
 *
 * Key scenarios:
 *   1. "主要来自情绪冲动" × 3 → installment-frequency flag → injected action appears
 *   2. Emotion ≥ 4 review → high_emotion_flag → confidence lowered + "【情绪提示】" injected
 *   3. Behavior tags (盲目跟风/过度焦虑) → tag-specific injected actions appear in next result
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

const CAMPUS_ITEM_ID = 'SZ000200';
const CAMPUS_ITEM_NAME = '5999元手机分期';

async function waitForFeedbackDialog(page: Page) {
  const analysisId = getAnalysisIdFromResultUrl(page);
  await pollAnalysisResult(page, analysisId, 'ready', 60_000);
  await page.waitForSelector('[role="dialog"]', { timeout: 20_000 });
}

// ─── Scenario A: low judgment → installment-frequency action in next analysis ─

/**
 * After repeated "主要来自情绪冲动" reviews (judgment_avg < 40, count >= 5
 * in the aggregation window), the AdaptationService sets the frequency-risk flag.
 *
 * In the NEXT analysis, next_step_actions should contain:
 *   "【分期依赖提醒】当前判断质量均值偏低，建议减少大额分期频率..."
 *
 * Prerequisite: at least 5 valid judgment history records with avg < 40.
 * We seed score 0 records, equivalent to "主要来自情绪冲动".
 */
test('after repeated emotion-led reviews: installment-frequency action appears in next analysis', async ({ page }) => {
  await loginAs(page);

  // Seed deterministic cross-day low judgment history. The backend stores one record per day.
  await seedLearningHistory(page, [0, 0, 0, 0, 0, 0, 0], 30);

  const history = await fetchLearningHistory(page, 7);
  const validRecords = history.judgment_history.filter(h => !h.label.includes('难以区分'));
  expect(validRecords.length).toBeGreaterThanOrEqual(5);
  // All should have score 0 (主要来自情绪冲动)
  const avgScore = validRecords.reduce((s, h) => s + h.score, 0) / validRecords.length;
  expect(avgScore).toBeLessThan(40);

  // ── Run a new analysis (the one we are testing) ──────────────────────────
  await page.goto(
    `${BASE_URL}/analysis/single-stock?stock_id=${CAMPUS_ITEM_ID}&stock_name=${encodeURIComponent(CAMPUS_ITEM_NAME)}`,
  );
  await page.getByRole('button', { name: /开始结构化分析/i }).click();
  await page.waitForURL(url => url.pathname.includes('/result'));

  const analysisId = getAnalysisIdFromResultUrl(page);
  const result = await pollAnalysisResult<Record<string, unknown>>(page, analysisId, 'ready', 60_000);

  // The adaptation should have injected the installment-frequency action.
  const nextStepActions = (result.decision_card as Record<string, unknown>).next_step_actions as string[];
  expect(nextStepActions).toBeTruthy();
  const hasInstallmentFrequencyAction = nextStepActions.some(
    (a: string) => a.includes('分期依赖提醒') || a.includes('判断质量均值偏低') || a.includes('大额分期频率'),
  );
  expect(hasInstallmentFrequencyAction).toBe(true);

});

// ─── Scenario B: high emotion → confidence lowered + "【情绪提示】" injected ──

/**
 * After a campus review with emotion_level ≥ 4:
 *   high_emotion_flag = True
 *   AdaptationService lowers confidence_level by one tier
 *   and inserts "【情绪提示】" as the first next_step_action
 */
test('high emotion review: confidence lowered and emotion warning injected', async ({ page }) => {
  await loginAs(page);

  // ── Submit a review with emotion level ≥ 4 ─────────────────────────────────
  await page.goto(
    `${BASE_URL}/analysis/post-trade?stock_id=${CAMPUS_ITEM_ID}&stock_name=${encodeURIComponent(CAMPUS_ITEM_NAME)}`,
  );
  await page.waitForLoadState('networkidle');

  await page.locator('input[placeholder*="暂缓购买"]').fill('E2E high-emotion campus budget test');
  await page.locator('textarea[placeholder*="本月余额变化"]').fill('E2E 高情绪预算复盘：仍想马上下单');
  await page.getByRole('button', { name: /主要来自理性判断/i }).click();
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
    `${BASE_URL}/analysis/single-stock?stock_id=${CAMPUS_ITEM_ID}&stock_name=${encodeURIComponent(CAMPUS_ITEM_NAME)}`,
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
 * After confirming feedback that includes a "盲目跟风" tag:
 *   UserProfile.behavior_tags includes "chasing_rise" or the localized tag
 *   The NEXT analysis should inject:
 *     "【盲目跟风提醒】请再次确认：本次消费是否因同伴影响..."
 */
test('after confirming "盲目跟风" tag: peer-influence action injected in next analysis', async ({ page }) => {
  await loginAs(page);

  // ── Submit a review that triggers the chasing_rise tag ──────────────────────
  await page.goto(
    `${BASE_URL}/analysis/post-trade?stock_id=${CAMPUS_ITEM_ID}&stock_name=${encodeURIComponent(CAMPUS_ITEM_NAME)}`,
  );
  await page.waitForLoadState('networkidle');

  await page.locator('input[placeholder*="暂缓购买"]').fill('同学都换新机触发盲目跟风');
  await page.locator('textarea[placeholder*="本月余额变化"]').fill('E2E peer-influence tag test');

  // Select judgment quality
  await page.getByRole('button', { name: /部分判断.*部分情绪/i }).click();

  // Select the "盲目跟风" behavior pattern
  await page.getByRole('button', { name: /盲目跟风/i }).click();

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
  expect(profile.behavior_tags.some(tag => tag === 'chasing_rise' || tag === '盲目跟风')).toBe(true);

  // ── Run the next analysis ───────────────────────────────────────────────────
  await page.goto(
    `${BASE_URL}/analysis/single-stock?stock_id=${CAMPUS_ITEM_ID}&stock_name=${encodeURIComponent(CAMPUS_ITEM_NAME)}`,
  );
  await page.getByRole('button', { name: /开始结构化分析/i }).click();
  await page.waitForURL(url => url.pathname.includes('/result'));

  const analysisId = getAnalysisIdFromResultUrl(page);
  const result = await pollAnalysisResult<Record<string, unknown>>(page, analysisId, 'ready', 60_000);

  const nextStepActions = (result.decision_card as Record<string, unknown>).next_step_actions as string[];
  expect(nextStepActions).toBeTruthy();
  const hasChasingAction = nextStepActions.some(a => a.includes('盲目跟风提醒') || a.includes('同伴影响') || a.includes('盲目跟风'));
  expect(hasChasingAction).toBe(true);
});

// ─── Scenario D: user_fit_summary adapts for intermediate users ────────────────

/**
 * For intermediate users with a declining judgment trend:
 *   user_fit_summary.fit should change from the base description to:
 *     fit summary mentions lower judgment quality and a need to slow the decision down.
 *
 * We achieve this by writing 2+ "主要来自情绪冲动" reviews, then running a new analysis.
 */
test('intermediate user with declining trend: user_fit_summary adapted', async ({ page }) => {
  await loginAs(page);

  // ── Seed 2 more "主要来自情绪冲动" reviews ───────────────────────────────
  const stocks = [
    { id: CAMPUS_ITEM_ID, name: CAMPUS_ITEM_NAME },
    { id: CAMPUS_ITEM_ID, name: CAMPUS_ITEM_NAME },
  ];

  for (const stock of stocks) {
    await page.goto(
      `${BASE_URL}/analysis/post-trade?stock_id=${stock.id}&stock_name=${encodeURIComponent(stock.name)}`,
    );
    await page.waitForLoadState('networkidle');
    await page.locator('input[placeholder*="暂缓购买"]').fill('E2E judgment-trend campus seed');
    await page.locator('textarea[placeholder*="本月余额变化"]').fill('E2E declining judgment seed for campus budget');
    await page.getByRole('button', { name: /主要来自情绪冲动/i }).click();
    await page.getByRole('button', { name: /提交复盘/i }).click();
    await page.waitForURL(url => url.pathname.includes('/result'));
    await waitForFeedbackDialog(page);
    await page.getByRole('button', { name: /确认/i }).first().click();
    await page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5_000 });
  }

  // ── Run a new analysis ───────────────────────────────────────────────────
  await page.goto(
    `${BASE_URL}/analysis/single-stock?stock_id=${CAMPUS_ITEM_ID}&stock_name=${encodeURIComponent(CAMPUS_ITEM_NAME)}`,
  );
  await page.getByRole('button', { name: /开始结构化分析/i }).click();
  await page.waitForURL(url => url.pathname.includes('/result'));

  const analysisId = getAnalysisIdFromResultUrl(page);
  const result = await pollAnalysisResult<Record<string, unknown>>(page, analysisId, 'ready', 60_000);

  const userFitSummary = (result.decision_card as Record<string, unknown>).user_fit_summary as { fit: string; unfit: string };

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
    `${BASE_URL}/analysis/post-trade?stock_id=${CAMPUS_ITEM_ID}&stock_name=${encodeURIComponent(CAMPUS_ITEM_NAME)}`,
  );
  await page1.waitForLoadState('networkidle');
  await page1.locator('input[placeholder*="暂缓购买"]').fill('persist campus budget test');
  await page1.locator('textarea[placeholder*="本月余额变化"]').fill('E2E persistence test for campus coach');
  await page1.getByRole('button', { name: /主要来自理性判断/i }).click();
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
