/**
 * Shared test helpers — login, API helpers, polling utilities.
 *
 * These helpers are imported by all E2E spec files so that auth,
 * DB queries, and wait utilities stay in one place.
 */

import { test as base, type Page, type APIResponse } from '@playwright/test';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const BASE_URL = process.env['E2E_BASE_URL'] ?? 'http://localhost:3000';
const API_URL  = process.env['E2E_API_URL']  ?? 'http://localhost:8000';
const TEST_USER = process.env['E2E_USER']       ?? 'testuser';
const TEST_PASS = process.env['E2E_PASS']       ?? 'testpassword123';

// ---------------------------------------------------------------------------
// Auth helpers
// ---------------------------------------------------------------------------

export { BASE_URL, API_URL, TEST_USER, TEST_PASS };

export function getAnalysisIdFromResultUrl(page: Page): string {
  const { pathname } = new URL(page.url());
  const parts = pathname.split('/').filter(Boolean);
  const resultIndex = parts.lastIndexOf('result');
  if (resultIndex > 0) {
    return parts[resultIndex - 1];
  }
  const last = parts.at(-1);
  if (!last) {
    throw new Error(`Cannot parse analysis id from URL: ${page.url()}`);
  }
  return last;
}

/** Log in via the UI login form and wait for the dashboard to load. */
export async function loginAs(page: Page) {
  await page.goto(`${BASE_URL}/login`);
  await page.waitForLoadState('domcontentloaded');
  if (await getAccessToken(page)) {
    await page.waitForURL(url => !url.pathname.includes('login'), { timeout: 5_000 }).catch(() => {});
    return;
  }
  if (!new URL(page.url()).pathname.includes('login')) {
    return;
  }

  const usernameInput = page.locator('input[autocomplete="username"]');
  await usernameInput.waitFor({ state: 'visible', timeout: 10_000 });
  await usernameInput.fill(TEST_USER);

  const passwordInput = page.locator('input[autocomplete="current-password"]');
  await passwordInput.waitFor({ state: 'visible', timeout: 10_000 });
  await passwordInput.click();
  await page.keyboard.press(process.platform === 'darwin' ? 'Meta+A' : 'Control+A');
  await page.keyboard.type(TEST_PASS);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(url => !url.pathname.includes('login'), { timeout: 10_000 });
}

/**
 * Get the raw JWT access token from localStorage.
 * Returns null if the user has not logged in.
 */
export async function getAccessToken(page: Page): Promise<string | null> {
  return page.evaluate(
    () => window.localStorage.getItem('ai_investment_access_token'),
  );
}

/** Delete local auth state (log out) without calling the server. */
export async function clearAuth(page: Page) {
  await page.evaluate(() => {
    localStorage.removeItem('ai_investment_access_token');
  });
}

// ---------------------------------------------------------------------------
// Direct API helpers (bypass UI — used for DB verification)
// ---------------------------------------------------------------------------

/** Call the backend API directly with the browser's auth token. */
export async function apiRequest(
  page: Page,
  method: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE',
  path: string,
  body?: unknown,
): Promise<APIResponse> {
  const token = await getAccessToken(page);
  if (!token) throw new Error('No access token — ensure loginAs() was called first');

  const url = `${API_URL}${path}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
  const fetchOptions: { method: string; headers: Record<string, string>; data?: unknown } = {
    method,
    headers,
  };
  if (body !== undefined) fetchOptions.data = body;

  return page.request.fetch(url, fetchOptions as Parameters<typeof page.request.fetch>[1]);
}

/** GET learning history for the current user. */
export async function fetchLearningHistory(
  page: Page,
  days = 7,
): Promise<{ emotion_history: Array<{ date: string; level: number }>; judgment_history: Array<{ date: string; score: number; label: string }> }> {
  const res = await apiRequest(page, 'GET', `/api/v1/user/profile/learning-history?days=${days}`);
  if (!res.ok()) throw new Error(`learning-history API returned ${res.status()}`);
  return res.json();
}

/** GET the user's full profile (includes behavior_tags). */
export async function fetchUserProfile(page: Page): Promise<{ behavior_tags: string[]; experience_level: string }> {
  const res = await apiRequest(page, 'GET', '/api/v1/user/profile');
  if (!res.ok()) throw new Error(`profile API returned ${res.status()}`);
  return res.json();
}

/** Seed learning history through the DEBUG-only backend endpoint. */
export async function seedLearningHistory(
  page: Page,
  judgmentScores: number[],
  days = 30,
): Promise<void> {
  const res = await apiRequest(page, 'POST', '/api/v1/user/profile/learning-history/debug-seed', {
    days,
    judgment_scores: judgmentScores,
  });
  if (!res.ok()) throw new Error(`debug-seed API returned ${res.status()}: ${await res.text()}`);
}

// ---------------------------------------------------------------------------
// Analysis helpers
// ---------------------------------------------------------------------------

/**
 * Wait for an analysis result to reach a target status by polling.
 *
 * Returns the raw JSON response body.
 * Throws if the analysis reaches 'failed' status before the target.
 */
export async function pollAnalysisResult<T = Record<string, unknown>>(
  page: Page,
  analysisId: string,
  targetStatus: 'ready' | 'partial_ready' | 'processing' = 'ready',
  timeout = 30_000,
): Promise<T> {
  const deadline = Date.now() + timeout;

  while (Date.now() < deadline) {
    const res = await apiRequest(page, 'GET', `/api/v1/analysis/${analysisId}`);
    const json = await res.json() as { status: string };

    if (json.status === 'failed') {
      throw new Error(`Analysis ${analysisId} failed: ${JSON.stringify(json)}`);
    }
    if (json.status === targetStatus) {
      await waitForResultPageSync(page, analysisId, json, targetStatus);
      return json as T;
    }
    // processing / partial_ready — keep polling
    await page.waitForTimeout(2_000);
  }

  throw new Error(`Analysis ${analysisId} did not reach ${targetStatus} within ${timeout}ms`);
}

/**
 * The API can reach ready a few seconds before ResultPage finishes its own
 * polling cycle. Keep UI assertions meaningful by waiting for the page to
 * render the same ready card instead of racing against React state updates.
 */
async function waitForResultPageSync(
  page: Page,
  analysisId: string,
  json: { status: string; decision_card?: { headline_judgement?: string } },
  targetStatus: 'ready' | 'partial_ready' | 'processing',
) {
  if (targetStatus === 'processing') return;

  const { pathname } = new URL(page.url());
  if (!pathname.includes(`/analysis/${analysisId}/result`)) return;

  const headline = json.decision_card?.headline_judgement;
  if (headline) {
    await page.getByText(headline).first().waitFor({ state: 'visible', timeout: 20_000 });
    return;
  }

  await page.getByText(/下一步建议|受限结论/i).first().waitFor({ state: 'visible', timeout: 20_000 });
}

// ---------------------------------------------------------------------------
// Learning feedback card helpers
// ---------------------------------------------------------------------------

/** Wait for the learning feedback card to appear (sheet slides up after 800ms delay). */
export async function waitForFeedbackCard(page: Page, timeout = 20_000) {
  await page.waitForSelector('[role="dialog"]', { timeout });
}

/** Dismiss the feedback card via the "忽略" button. */
export async function dismissFeedbackCard(page: Page) {
  await page.getByRole('button', { name: /忽略/i }).first().click();
  await page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5_000 });
}

/** Click the "确认" button and wait for the API call to resolve. */
export async function confirmFeedbackCard(page: Page) {
  const feedbackReq = page.waitForResponse(
    r => r.url().includes('/api/v1/user/profile/learning-feedback') && r.request().method() === 'POST',
    { timeout: 10_000 },
  );
  await page.getByRole('button', { name: /确认/i }).first().click();
  const res = await feedbackReq;
  if (res.status() !== 200) throw new Error(`learning-feedback returned ${res.status()}`);
  // Card should close
  await page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5_000 });
}
