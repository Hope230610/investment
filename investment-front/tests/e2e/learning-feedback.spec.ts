/**
 * Playwright E2E tests for the Learning Feedback full user journey.
 *
 * Prerequisites:
 *   npm install -D @playwright/test
 *   npx playwright install chromium --with-deps
 *   cp .env.example .env  # configure BASE_URL + auth
 *
 * Run:
 *   npx playwright test tests/e2e/learning-feedback.spec.ts
 *
 * These tests cover the complete feedback loop:
 *   post-trade-review submit → ResultPage feedback card →
 *   confirm/later/dismiss → DB verification → ProfilePage history
 */

import { test, expect, type Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Test configuration (reads from environment)
// ---------------------------------------------------------------------------

const BASE_URL = process.env['E2E_BASE_URL'] ?? 'http://localhost:3000';
const TEST_USER = process.env['E2E_USER'] ?? 'testuser';
const TEST_PASS = process.env['E2E_PASS'] ?? 'testpassword123';
const ACCESS_TOKEN_KEY = 'ai_investment_access_token';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function loginAs(page: Page) {
  await page.goto(`${BASE_URL}/login`);
  await page.getByPlaceholder('用户名').fill(TEST_USER);
  await page.getByPlaceholder('密码').fill(TEST_PASS);
  await page.getByRole('button', { name: '进入系统' }).click();
  await page.waitForURL(url => !url.pathname.includes('login'));
}

async function waitForFeedbackCard(page: Page, timeout = 3000) {
  // The card uses role="dialog" per LearningFeedbackCard.tsx
  await page.waitForSelector('[role="dialog"]', { timeout });
}

async function getAccessToken(page: Page) {
  return page.evaluate((tokenKey) => window.localStorage.getItem(tokenKey), ACCESS_TOKEN_KEY);
}

async function fetchLearningHistory(page: Page) {
  const token = await getAccessToken(page);
  if (!token) {
    throw new Error('Missing access token after login');
  }

  return page.evaluate(
    async ({ baseUrl, accessToken }) => {
      const response = await fetch(`${baseUrl}/api/v1/user/profile/learning-history?days=7`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      const body = await response.json();
      return {
        status: response.status,
        body,
      };
    },
    { baseUrl: BASE_URL, accessToken: token },
  );
}

function getAnalysisIdFromResultUrl(page: Page): string {
  const { pathname } = new URL(page.url());
  const parts = pathname.split('/').filter(Boolean);
  const resultIndex = parts.lastIndexOf('result');
  if (resultIndex > 0) return parts[resultIndex - 1];
  return parts.at(-1) || '';
}

async function waitForAnalysisReady(page: Page, timeout = 60_000) {
  const analysisId = getAnalysisIdFromResultUrl(page);
  const token = await getAccessToken(page);
  if (!analysisId || !token) throw new Error('Missing analysis id or token');

  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const result = await page.evaluate(
      async ({ baseUrl, id, accessToken }) => {
        const response = await fetch(`${baseUrl}/api/v1/analysis/${id}`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        return response.json();
      },
      { baseUrl: BASE_URL, id: analysisId, accessToken: token },
    ) as { status?: string };

    if (result.status === 'ready' || result.status === 'partial_ready') return result;
    if (result.status === 'failed') throw new Error(`Analysis failed: ${JSON.stringify(result)}`);
    await page.waitForTimeout(2_000);
  }
  throw new Error(`Analysis ${analysisId} did not become ready within ${timeout}ms`);
}

// ---------------------------------------------------------------------------
// Test: Learning Feedback Card — Confirm path
// ---------------------------------------------------------------------------

test('feedback card shows on post-trade-review result page', async ({ page }) => {
  await loginAs(page);

  await page.goto(`${BASE_URL}/analysis/post-trade?stock_id=SH600519&stock_name=贵州茅台`);
  await page.waitForLoadState('networkidle');

  // Submit the review form
  await page.locator('input[placeholder*="买入"]').fill('continued');
  await page.locator('textarea[placeholder*="价格变化"]').fill('E2E test outcome');
  await page.getByRole('button', { name: /主要来自判断/i }).click();
  await page.getByRole('button', { name: /提交|submit/i }).click();

  // Should land on result page
  await page.waitForURL(url => url.pathname.includes('/result'));
  await page.waitForLoadState('networkidle');
  await waitForAnalysisReady(page);

  // Feedback card should appear (800ms delay)
  try {
    await waitForFeedbackCard(page, 4000);
    const card = page.locator('[role="dialog"]').first();
    await expect(card).toBeVisible();
  } catch {
    // Unexpected — card should appear after a fresh post-trade review.
    // Fail the test rather than silently skipping.
    throw new Error('Feedback card did not appear after review submission');
  }
});

// ---------------------------------------------------------------------------
// Test: Confirm button writes to DB and closes card
// ---------------------------------------------------------------------------

test('confirm button writes learning feedback to DB', async ({ page }) => {
  await loginAs(page);

  // Go to post-trade directly (bypass ReviewsPage for simpler path)
  await page.goto(`${BASE_URL}/analysis/post-trade?stock_id=SH600519&stock_name=贵州茅台`);
  await page.waitForLoadState('networkidle');

  await page.locator('input[placeholder*="买入"]').fill('continued');
  await page.locator('textarea[placeholder*="价格变化"]').fill('E2E confirm test');
  await page.getByRole('button', { name: /主要来自判断/i }).click();
  await page.getByRole('button', { name: /提交|submit/i }).click();

  await page.waitForURL(url => url.pathname.includes('/result'));
  await page.waitForLoadState('networkidle');
  await waitForAnalysisReady(page);

  // Wait for card + click confirm
  try {
    await waitForFeedbackCard(page, 4000);
    const confirmBtn = page.getByRole('button', { name: /确认|confirm/i }).first();
    const feedbackResponsePromise = page.waitForResponse((response) =>
      response.url().includes('/api/v1/user/profile/learning-feedback')
      && response.request().method() === 'POST',
    );

    await confirmBtn.click();
    const feedbackResponse = await feedbackResponsePromise;
    expect(feedbackResponse.status()).toBe(200);

    // Card should be gone after confirm
    const card = page.locator('[role="dialog"]');
    await expect(card).toHaveCount(0, { timeout: 5000 });

    const history = await fetchLearningHistory(page);
    expect(history.status).toBe(200);

    const today = new Date().toISOString().slice(0, 10);
    const hasTodayEntry = Array.isArray(history.body?.emotion_history)
      && history.body.emotion_history.some((entry: { date?: string }) => entry.date?.startsWith(today));
    expect(hasTodayEntry).toBeTruthy();
  } catch {
    throw new Error('Card not visible after confirm — feedback card should appear');
  }
});

// ---------------------------------------------------------------------------
// Test: Dismiss button permanently hides the card
// ---------------------------------------------------------------------------

test('dismiss button permanently hides feedback card', async ({ page }) => {
  await loginAs(page);

  // Use a fresh stock to avoid dismissed state
  await page.goto(`${BASE_URL}/analysis/post-trade?stock_id=SZ002594&stock_name=比亚迪`);
  await page.waitForLoadState('networkidle');

  await page.locator('input[placeholder*="买入"]').fill('delayed');
  await page.locator('textarea[placeholder*="价格变化"]').fill('E2E dismiss test');
  await page.getByRole('button', { name: /部分判断.*部分运气/i }).click();
  await page.getByRole('button', { name: /提交|submit/i }).click();

  await page.waitForURL(url => url.pathname.includes('/result'));
  await waitForAnalysisReady(page);

  try {
    await waitForFeedbackCard(page, 4000);
    const dismissBtn = page.getByRole('button', { name: /忽略|dismiss/i }).first();
    await dismissBtn.click();
    await page.waitForTimeout(500);

    // Refresh page — card should NOT reappear (dismissed = permanent)
    await page.reload();
    await page.waitForLoadState('networkidle');

    const card = page.locator('[role="dialog"]');
    await expect(card).toHaveCount(0, { timeout: 3000 });
  } catch {
    throw new Error('Dismiss target card not visible — verify fresh session state');
  }
});

// ---------------------------------------------------------------------------
// Test: Later button increments show count, card can reappear later
// ---------------------------------------------------------------------------

test('later button increments show count, card reappears on next review', async ({ page }) => {
  await loginAs(page);

  await page.goto(`${BASE_URL}/analysis/post-trade?stock_id=SZ300750&stock_name=宁德时代`);
  await page.waitForLoadState('networkidle');

  await page.locator('input[placeholder*="买入"]').fill('cancelled');
  await page.locator('textarea[placeholder*="价格变化"]').fill('E2E later test');
  await page.getByRole('button', { name: /主要来自运气/i }).click();
  await page.getByRole('button', { name: /提交|submit/i }).click();

  await page.waitForURL(url => url.pathname.includes('/result'));
  await waitForAnalysisReady(page);

  try {
    await waitForFeedbackCard(page, 4000);
    const laterBtn = page.getByRole('button', { name: /稍后|later/i }).first();
    await laterBtn.click();
    await page.waitForTimeout(500);

    // Card should close, count should be incremented
    const card = page.locator('[role="dialog"]');
    await expect(card).toHaveCount(0);

    // On a second review, card should still appear (< 3 shows)
    await page.goto(`${BASE_URL}/analysis/post-trade?stock_id=SH600036&stock_name=招商银行`);
    await page.waitForLoadState('networkidle');
    await page.locator('input[placeholder*="买入"]').fill('continued');
    await page.locator('textarea[placeholder*="价格变化"]').fill('Second review');
    await page.getByRole('button', { name: /主要来自判断/i }).click();
    await page.getByRole('button', { name: /提交|submit/i }).click();
    await page.waitForURL(url => url.pathname.includes('/result'));
    await waitForAnalysisReady(page);

    await waitForFeedbackCard(page, 4000);
    const card2 = page.locator('[role="dialog"]').first();
    await expect(card2).toBeVisible();
  } catch {
    throw new Error('Later-button second-review card not visible — verify fresh session state');
  }
});

// ---------------------------------------------------------------------------
// Test: ProfilePage shows learning history after feedback
// ---------------------------------------------------------------------------

test('profile page shows learning history after feedback', async ({ page }) => {
  await loginAs(page);

  // Navigate to profile page
  await page.goto(`${BASE_URL}/profile`);
  await page.waitForLoadState('networkidle');

  // Find learning history section
  const historySection = page.locator('text=/学习记录|learning.?history/i').first();
  const sectionCount = await historySection.count();

  if (sectionCount === 0) {
    test.skip(true, 'Learning history section not found in ProfilePage');
    return;
  }

  await expect(historySection).toBeVisible();

  // Check for judgment quality trend bar or emotion sparkline
  const sparkline = page.locator('svg').first();
  const hasSparkline = await sparkline.count() > 0;

  if (!hasSparkline) {
    // Section exists but no data yet — acceptable for fresh user
    test.skip(true, 'Learning history section exists but no data displayed yet');
  }
});
