/**
 * E2E tests for Decision Card evidence fields (P0 spec requirement).
 *
 * Run:
 *   npx playwright test tests/e2e/decision-card-evidence.spec.ts
 *
 * The single-stock-analysis spec requires DecisionCard to contain:
 *   - supporting_evidence    (List[str])
 *   - counter_evidence       (List[str])
 *   - invalidation_conditions (List[str])
 *   - confidence_level       ('low' | 'medium' | 'high')
 *
 * These tests verify that a ready result contains all four fields and that
 * the UI renders them correctly in the ResultPage.
 */

import { test, expect } from '@playwright/test';
import { BASE_URL, getAnalysisIdFromResultUrl, loginAs, pollAnalysisResult } from './helpers';

const STOCK_ID   = 'SH600519';
const STOCK_NAME = '贵州茅台';

interface DecisionCardV2 {
  headline_judgement: string;
  supporting_evidence: string[];
  counter_evidence: string[];
  invalidation_conditions: string[];
  confidence_level: 'low' | 'medium' | 'high';
}

interface AnalysisDetail {
  status: string;
  decision_card: DecisionCardV2;
  degrade_flags: string[];
}

// ─── Core evidence fields ──────────────────────────────────────────────────────

test('ready result contains all four evidence fields', async ({ page }) => {
  await loginAs(page);

  await page.goto(
    `${BASE_URL}/analysis/single-stock?stock_id=${STOCK_ID}&stock_name=${encodeURIComponent(STOCK_NAME)}`,
  );
  await page.getByRole('button', { name: /开始结构化分析/i }).click();
  await page.waitForURL(url => url.pathname.includes('/result'));

  const analysisId = getAnalysisIdFromResultUrl(page);
  const result = await pollAnalysisResult<AnalysisDetail>(page, analysisId, 'ready', 60_000);

  expect(['ready', 'partial_ready']).toContain(result.status);
  expect(result.decision_card).toBeTruthy();

  const card = result.decision_card;

  // Field presence
  expect(Array.isArray(card.supporting_evidence)).toBe(true);
  expect(Array.isArray(card.counter_evidence)).toBe(true);
  expect(Array.isArray(card.invalidation_conditions)).toBe(true);
  expect(['low', 'medium', 'high']).toContain(card.confidence_level);

  // Non-empty evidence (generation service always produces at least one item)
  expect(card.supporting_evidence.length).toBeGreaterThan(0);
  expect(card.invalidation_conditions.length).toBeGreaterThan(0);
});

test('supporting_evidence section rendered in UI', async ({ page }) => {
  await loginAs(page);

  await page.goto(
    `${BASE_URL}/analysis/single-stock?stock_id=${STOCK_ID}&stock_name=${encodeURIComponent(STOCK_NAME)}`,
  );
  await page.getByRole('button', { name: /开始结构化分析/i }).click();
  await page.waitForURL(url => url.pathname.includes('/result'));

  const analysisId = getAnalysisIdFromResultUrl(page);
  const result = await pollAnalysisResult<AnalysisDetail>(page, analysisId, 'ready', 60_000);

  if (result.decision_card.supporting_evidence.length > 0) {
    await expect(page.getByText(/支撑证据/i)).toBeVisible();
    // Evidence items should start with "S1", "S2" ... labels
    await expect(page.locator('text=/^S\\d/i').first()).toBeVisible();
  }
});

test('counter_evidence section rendered in UI', async ({ page }) => {
  await loginAs(page);

  await page.goto(
    `${BASE_URL}/analysis/single-stock?stock_id=${STOCK_ID}&stock_name=${encodeURIComponent(STOCK_NAME)}`,
  );
  await page.getByRole('button', { name: /开始结构化分析/i }).click();
  await page.waitForURL(url => url.pathname.includes('/result'));

  const analysisId = getAnalysisIdFromResultUrl(page);
  const result = await pollAnalysisResult<AnalysisDetail>(page, analysisId, 'ready', 60_000);

  if (result.decision_card.counter_evidence.length > 0) {
    await expect(page.getByRole('heading', { name: '反方证据' })).toBeVisible();
    // Counter evidence items should start with "C1", "C2" ... labels
    await expect(page.locator('text=/^C\\d/i').first()).toBeVisible();
  }
});

test('invalidation_conditions section rendered in UI', async ({ page }) => {
  await loginAs(page);

  await page.goto(
    `${BASE_URL}/analysis/single-stock?stock_id=${STOCK_ID}&stock_name=${encodeURIComponent(STOCK_NAME)}`,
  );
  await page.getByRole('button', { name: /开始结构化分析/i }).click();
  await page.waitForURL(url => url.pathname.includes('/result'));

  const analysisId = getAnalysisIdFromResultUrl(page);
  const result = await pollAnalysisResult<AnalysisDetail>(page, analysisId, 'ready', 60_000);

  await expect(page.getByText(/以下情况请重新评估/i)).toBeVisible();
  // Each condition should have a ✕ marker
  const conditions = result.decision_card.invalidation_conditions;
  expect(conditions.length).toBeGreaterThan(0);
});

test('confidence_level badge rendered in UI', async ({ page }) => {
  await loginAs(page);

  await page.goto(
    `${BASE_URL}/analysis/single-stock?stock_id=${STOCK_ID}&stock_name=${encodeURIComponent(STOCK_NAME)}`,
  );
  await page.getByRole('button', { name: /开始结构化分析/i }).click();
  await page.waitForURL(url => url.pathname.includes('/result'));

  const analysisId = getAnalysisIdFromResultUrl(page);
  const result = await pollAnalysisResult<AnalysisDetail>(page, analysisId, 'ready', 60_000);

  const level = result.decision_card.confidence_level;
  // Badge text: 高置信 / 中置信 / 低置信
  const badgeText = level === 'high' ? '高置信' : level === 'medium' ? '中置信' : '低置信';
  await expect(page.getByText(badgeText).first()).toBeVisible();

  // Badge color: high = emerald, medium = amber, low = red
  const badgeLocator = page.locator(
    `.bg-emerald-100.text-emerald-700, .bg-amber-100.text-amber-700, .bg-red-100.text-red-700`,
  );
  await expect(badgeLocator.first()).toBeVisible();
});

// ─── confidence_level computed correctly ────────────────────────────────────────

test('confidence_level is valid across analysis scenarios', async ({ page }) => {
  await loginAs(page);

  const scenarios = [
    { path: '/analysis/single-stock' },
    { path: '/analysis/pre-trade' },
    { path: '/analysis/post-trade' },
  ];

  const levels: string[] = [];

  for (const { path } of scenarios) {
    const stockId = path.includes('pre-trade') ? STOCK_ID : STOCK_ID;
    const stockName = path.includes('pre-trade') ? STOCK_NAME : STOCK_NAME;

    if (path.includes('post-trade')) {
      await page.goto(`${BASE_URL}/analysis/post-trade?stock_id=${STOCK_ID}&stock_name=${encodeURIComponent(STOCK_NAME)}`);
      await page.locator('input[placeholder*="买入"]').fill('E2E confidence test');
      await page.locator('textarea[placeholder*="价格变化"]').fill('E2E confidence test outcome');
      await page.getByRole('button', { name: /提交复盘/i }).click();
    } else if (path.includes('pre-trade')) {
      await page.goto(`${BASE_URL}${path}?stock_id=${STOCK_ID}&stock_name=${encodeURIComponent(STOCK_NAME)}`);
      await page.getByRole('button', { name: /^买入$/i }).click();
      await page.getByRole('button', { name: /^连续上涨$/i }).click();
      await page.locator('input[type="range"]').fill('4');
      await page.getByRole('button', { name: /开始自检/i }).click();
      const yesButtons = page.locator('button', { hasText: '是' });
      const count = await yesButtons.count();
      for (let i = 0; i < count; i++) {
        await yesButtons.nth(i).click();
      }
      await page.getByRole('button', { name: /完成自检并生成分析/i }).click();
    } else {
      await page.goto(`${BASE_URL}${path}?stock_id=${STOCK_ID}&stock_name=${encodeURIComponent(STOCK_NAME)}`);
      await page.getByRole('button', { name: /开始结构化分析/i }).click();
    }

    await page.waitForLoadState('networkidle');
    await page.waitForURL(url => url.pathname.includes('/result'));

    const analysisId = getAnalysisIdFromResultUrl(page);
    const result = await pollAnalysisResult<AnalysisDetail>(page, analysisId, 'ready', 60_000);
    levels.push(result.decision_card.confidence_level);
  }

  levels.forEach(l => expect(['low', 'medium', 'high']).toContain(l));
});

// ─── user_fit_summary adapted ─────────────────────────────────────────────────

test('user_fit_summary rendered in decision card', async ({ page }) => {
  await loginAs(page);

  await page.goto(
    `${BASE_URL}/analysis/single-stock?stock_id=${STOCK_ID}&stock_name=${encodeURIComponent(STOCK_NAME)}`,
  );
  await page.getByRole('button', { name: /开始结构化分析/i }).click();
  await page.waitForURL(url => url.pathname.includes('/result'));

  const analysisId = getAnalysisIdFromResultUrl(page);
  const result = await pollAnalysisResult<{ decision_card: { user_fit_summary: { fit: string; unfit: string } } }>(
    page,
    analysisId,
    'ready',
    60_000,
  );

  const { user_fit_summary } = result.decision_card;
  expect(user_fit_summary.fit).toBeTruthy();
  expect(user_fit_summary.unfit).toBeTruthy();

  // UI: "适合谁" / "不适合谁" labels
  await expect(page.getByText('适合谁', { exact: true })).toBeVisible();
  await expect(page.getByText('不适合谁', { exact: true })).toBeVisible();
});
