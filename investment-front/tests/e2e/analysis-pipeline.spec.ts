/**
 * E2E tests for the full AI financial literacy coach pipeline:
 * campus decision check / pre-purchase cooling-off / post-decision review.
 *
 * Run:
 *   npx playwright test tests/e2e/analysis-pipeline.spec.ts
 *
 * These tests verify:
 *   1. All three analysis scenarios can be created and reach a terminal state
 *   2. Result page loads and renders key structural elements
 *   3. The navigation path from home → input → result is intact
 *   4. Failed / partial-ready states are handled gracefully
 */

import { test, expect, type Page } from '@playwright/test';
import {
  BASE_URL,
  getAnalysisIdFromResultUrl,
  loginAs,
  pollAnalysisResult,
  waitForFeedbackCard,
} from './helpers';

// ─── Shared selectors ───────────────────────────────────────────────────────────

const STOCK_ID  = 'SZ000200';
const STOCK_NAME = '5999元手机分期';

const POST_TRADE_STOCK_ID   = 'SZ000200';
const POST_TRADE_STOCK_NAME = '5999元手机分期';

// ─── Scenario: Single Stock Analysis ─────────────────────────────────────────

test('campus product analysis: submit → result page renders coach guidance', async ({ page }) => {
  await loginAs(page);

  // Navigate via the home page scenario link
  await page.goto(BASE_URL);
  await page.waitForLoadState('networkidle');

  // Click the product risk assessment scenario card.
  await page.locator('a[href="/analysis/single-stock"]').first().click();
  await page.waitForURL(url => url.pathname.includes('single-stock'));

  // Pre-fill stock via URL param (avoid search UI)
  await page.goto(
    `${BASE_URL}/analysis/single-stock?stock_id=${STOCK_ID}&stock_name=${encodeURIComponent(STOCK_NAME)}`,
  );
  await page.waitForLoadState('networkidle');

  // Submit
  await page.getByRole('button', { name: /开始结构化分析/i }).click();
  await page.waitForURL(url => url.pathname.includes('/result'));

  // Poll for result
  const analysisId = getAnalysisIdFromResultUrl(page);
  const result = await pollAnalysisResult<{
    status: string;
    decision_card: { headline_judgement: string };
  }>(page, analysisId, 'ready', 60_000);

  // ── Result page structural assertions ───────────────────────────────────────

  // Headline judgment rendered
  const headlineText = result.decision_card.headline_judgement;
  expect(headlineText).toBeTruthy();
  await expect(page.getByText(headlineText).first()).toBeVisible();

  // Stock identity visible
  await expect(page.getByRole('heading', { name: STOCK_NAME })).toBeVisible();

  // "核心理由" section
  await expect(page.getByText(/核心理由/i)).toBeVisible();

  // "下一步建议动作" section
  await expect(page.getByText(/下一步建议/i)).toBeVisible();

  // Real-market runs may return a compliant degraded result when external data is incomplete.
  expect(['ready', 'partial_ready']).toContain(result.status);
});

// ─── Scenario: Pre-Trade Check ───────────────────────────────────────────────

test('pre-purchase check: high-emotion campus flow → cooling-off self-check shown', async ({ page }) => {
  await loginAs(page);

  await page.goto(
    `${BASE_URL}/analysis/pre-trade?stock_id=${STOCK_ID}&stock_name=${encodeURIComponent(STOCK_NAME)}`,
  );
  await page.waitForLoadState('networkidle');

  // Select intent: "购买 / 分期"
  await page.getByRole('button', { name: /购买\s*\/\s*分期/i }).click();

  // Select trigger: peer influence on campus.
  await page.getByRole('button', { name: /^同学都换新机$/i }).click();

  // Emotion: slide to 4 (冲动)
  await page.locator('input[type="range"]').fill('4');

  // Cooling-off entry should appear (emotion > 3)
  await expect(page.getByRole('button', { name: /进入消费冷静期/i })).toBeVisible();

  // Submit should not navigate — it should reveal the self-check panel
  await page.getByRole('button', { name: /进入消费冷静期/i }).click();

  // Self-check panel appears
  await expect(page.getByRole('heading', { name: /消费冷静期自检/i }).first()).toBeVisible();

  // Answer all questions
  const yesButtons = page.locator('button', { hasText: '是' });
  const count = await yesButtons.count();
  for (let i = 0; i < count; i++) {
    await yesButtons.nth(i).click();
  }

  // "完成自检并生成决策卡" should be enabled
  await page.getByRole('button', { name: /完成自检并生成决策卡/i }).click();

  await page.waitForURL(url => url.pathname.includes('/result'));

  // Poll for result (pre-trade results can be fast)
  const analysisId = getAnalysisIdFromResultUrl(page);
  const result = await pollAnalysisResult<Record<string, unknown>>(page, analysisId, 'ready', 60_000);

  expect(['ready', 'partial_ready']).toContain(result.status);
  // intervention should be present when emotion is high + peer influence trigger
  const intervention = result.intervention as Record<string, unknown> | undefined;
  expect(intervention).toBeTruthy();
  expect(intervention?.behavior_type).toBeTruthy();
});

// ─── Scenario: Post-Trade Review ──────────────────────────────────────────────

test('post-decision campus review: submit → result page → learning feedback card shown', async ({ page }) => {
  await loginAs(page);

  await page.goto(
    `${BASE_URL}/analysis/post-trade?stock_id=${POST_TRADE_STOCK_ID}&stock_name=${encodeURIComponent(POST_TRADE_STOCK_NAME)}`,
  );
  await page.waitForLoadState('networkidle');

  // Fill in required fields
  await page.locator('input[placeholder*="暂缓购买"]').fill('暂缓购买 5999 元手机，先比较校内二手和 3000 元替代方案');
  await page.locator('textarea[placeholder*="本月余额变化"]').fill('E2E 校园预算复盘：本月余额保持安全，冲动感下降');
  await page.getByRole('button', { name: /主要来自理性判断/i }).click();

  // Submit
  await page.getByRole('button', { name: /提交复盘/i }).click();
  await page.waitForURL(url => url.pathname.includes('/result'));

  // Poll for result
  const analysisId = getAnalysisIdFromResultUrl(page);
  const result = await pollAnalysisResult<Record<string, unknown>>(page, analysisId, 'ready', 60_000);
  expect(['ready', 'partial_ready']).toContain(result.status);

  // Learning feedback card should appear (800ms delay in ResultPage)
  await waitForFeedbackCard(page, 6_000);
  const card = page.locator('[role="dialog"]').first();
  await expect(card).toBeVisible();

  // Card should show the "本次复盘" header.
  await expect(page.getByText(/本次复盘.*系统学到了这些/i)).toBeVisible();
});

// ─── Scenario: Analysis with partial-ready degrade ──────────────────────────────

test('partial-ready: degrade banner shown, result still accessible', async ({ page }) => {
  await loginAs(page);

  await page.goto(
    `${BASE_URL}/analysis/single-stock?stock_id=${STOCK_ID}&stock_name=${encodeURIComponent(STOCK_NAME)}`,
  );
  await page.waitForLoadState('networkidle');
  await page.getByRole('button', { name: /开始结构化分析/i }).click();
  await page.waitForURL(url => url.pathname.includes('/result'));

  const analysisId = getAnalysisIdFromResultUrl(page);

  // Poll for partial-ready OR ready (either is acceptable)
  let result: Record<string, unknown>;
  try {
    result = await pollAnalysisResult<Record<string, unknown>>(page, analysisId, 'partial_ready', 30_000);
  } catch {
    result = await pollAnalysisResult<Record<string, unknown>>(page, analysisId, 'ready', 30_000);
  }

  // partial_ready should show the amber degrade banner
  if (result.status === 'partial_ready') {
    await expect(page.getByText(/受限结论/i)).toBeVisible();
    // degrade_flags should be rendered
    const degradeSection = page.getByText(/证据链不足|行情数据暂时不完整|分析生成异常/i);
    await expect(degradeSection).toBeVisible();
  }

  // 'ready' status: full content should be there
  if (result.status === 'ready') {
    await expect(page.getByText(/下一步建议/i)).toBeVisible();
  }
});
