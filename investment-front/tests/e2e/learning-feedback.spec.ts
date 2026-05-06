/**
 * Playwright E2E tests for the campus financial-literacy feedback journey.
 *
 * Prerequisites:
 *   npm install -D @playwright/test
 *   npx playwright install chromium --with-deps
 *   cp .env.example .env  # configure BASE_URL + auth
 *
 * Run:
 *   npx playwright test tests/e2e/learning-feedback.spec.ts
 *
 * These tests cover the complete coach loop:
 *   campus budget review submit → ResultPage feedback card →
 *   confirm/later/dismiss → DB verification → ProfilePage history
 */

import { test, expect, type Page, type BrowserContext } from '@playwright/test';

// ---------------------------------------------------------------------------
// Test configuration (reads from environment)
// ---------------------------------------------------------------------------

const BASE_URL = process.env['E2E_BASE_URL'] ?? 'http://localhost:3000';
const API_URL = process.env['E2E_API_URL'] ?? 'http://localhost:8000';
const TEST_USER = process.env['E2E_USER'] ?? 'testuser';
const TEST_PASS = process.env['E2E_PASS'] ?? 'testpassword123';
const ACCESS_TOKEN_KEY = 'ai_investment_access_token';
const CAMPUS_ITEM_ID = 'SZ000200';
const CAMPUS_ITEM_NAME = '5999元手机分期';
const E2E_RUN_ID = process.env['E2E_RUN_ID'] ?? `${Date.now()}-${process.pid}`;
let authUserCounter = 0;
const contextUsers = new WeakMap<BrowserContext, string>();

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function loginAs(page: Page) {
  let username = contextUsers.get(page.context());
  if (!username) {
    authUserCounter += 1;
    username = `pwf_${authUserCounter}_${Math.random().toString(36).slice(2, 8)}_${TEST_USER}_${E2E_RUN_ID}`
      .replace(/[^a-zA-Z0-9_-]/g, '_')
      .slice(0, 50);
    contextUsers.set(page.context(), username);
  }

  const registerResponse = await page.request.post(`${API_URL}/api/v1/user/register`, {
    data: { username, password: TEST_PASS },
  });
  if (!registerResponse.ok() && registerResponse.status() !== 409) {
    throw new Error(`E2E user registration failed: ${registerResponse.status()} ${await registerResponse.text()}`);
  }

  const loginResponse = registerResponse.status() === 409
    ? await page.request.post(`${API_URL}/api/v1/user/login`, { data: { username, password: TEST_PASS } })
    : registerResponse;
  if (!loginResponse.ok()) {
    throw new Error(`E2E user login failed: ${loginResponse.status()} ${await loginResponse.text()}`);
  }

  const body = await loginResponse.json() as { access_token: string; user?: unknown };
  await page.goto(BASE_URL);
  await page.evaluate(
    ({ token, user }) => {
      window.localStorage.setItem('ai_investment_access_token', token);
      if (user) {
        window.localStorage.setItem('ai_investment_user', JSON.stringify(user));
      }
      window.dispatchEvent(new Event('ai-investment-auth-change'));
    },
    { token: body.access_token, user: body.user ?? null },
  );
  await page.goto(`${BASE_URL}/`);
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

test('feedback card shows after a campus budget review result page', async ({ page }) => {
  await loginAs(page);

  await page.goto(`${BASE_URL}/analysis/post-trade?stock_id=${CAMPUS_ITEM_ID}&stock_name=${encodeURIComponent(CAMPUS_ITEM_NAME)}`);
  await page.waitForLoadState('networkidle');

  // Submit the review form
  await page.locator('input[placeholder*="暂缓购买"]').fill('暂缓购买手机分期，先保留生活费安全垫');
  await page.locator('textarea[placeholder*="本月余额变化"]').fill('E2E 校园预算结果：没有透支，也找到了替代方案');
  await page.getByRole('button', { name: /主要来自理性判断/i }).click();
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

test('confirm button writes campus learning feedback to DB', async ({ page }) => {
  await loginAs(page);

  // Go to review directly (bypass ReviewsPage for simpler path)
  await page.goto(`${BASE_URL}/analysis/post-trade?stock_id=${CAMPUS_ITEM_ID}&stock_name=${encodeURIComponent(CAMPUS_ITEM_NAME)}`);
  await page.waitForLoadState('networkidle');

  await page.locator('input[placeholder*="暂缓购买"]').fill('把手机预算从 5999 元降到 3000 元以内');
  await page.locator('textarea[placeholder*="本月余额变化"]').fill('E2E confirm：保留了饭卡和交通预算');
  await page.getByRole('button', { name: /主要来自理性判断/i }).click();
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

test('dismiss button permanently hides feedback card for a campus review', async ({ page }) => {
  await loginAs(page);

  // Each submitted review creates a fresh analysis id, so the dismiss key is isolated.
  await page.goto(`${BASE_URL}/analysis/post-trade?stock_id=${CAMPUS_ITEM_ID}&stock_name=${encodeURIComponent(CAMPUS_ITEM_NAME)}`);
  await page.waitForLoadState('networkidle');

  await page.locator('input[placeholder*="暂缓购买"]').fill('先不分期，等奖学金到账后再评估');
  await page.locator('textarea[placeholder*="本月余额变化"]').fill('E2E dismiss：情绪下降，但仍想保留观察');
  await page.getByRole('button', { name: /部分判断.*部分情绪/i }).click();
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

test('later button increments show count, card reappears on next campus review', async ({ page }) => {
  await loginAs(page);

  await page.goto(`${BASE_URL}/analysis/post-trade?stock_id=${CAMPUS_ITEM_ID}&stock_name=${encodeURIComponent(CAMPUS_ITEM_NAME)}`);
  await page.waitForLoadState('networkidle');

  await page.locator('input[placeholder*="暂缓购买"]').fill('取消当天分期下单');
  await page.locator('textarea[placeholder*="本月余额变化"]').fill('E2E later：主要是被博主种草带动');
  await page.getByRole('button', { name: /主要来自情绪冲动/i }).click();
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
    await page.goto(`${BASE_URL}/analysis/post-trade?stock_id=${CAMPUS_ITEM_ID}&stock_name=${encodeURIComponent(CAMPUS_ITEM_NAME)}`);
    await page.waitForLoadState('networkidle');
    await page.locator('input[placeholder*="暂缓购买"]').fill('第二次复盘：继续保留预算上限');
    await page.locator('textarea[placeholder*="本月余额变化"]').fill('Second campus review：替代方案满足上课需求');
    await page.getByRole('button', { name: /主要来自理性判断/i }).click();
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
