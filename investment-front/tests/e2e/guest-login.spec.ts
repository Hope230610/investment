import { test, expect } from '@playwright/test';
import { BASE_URL, API_URL } from './helpers';

test.describe('Guest auto-login', () => {
  test('POST /api/v1/user/guest returns valid JWT and user profile', async ({ page }) => {
    const res = await page.request.post(`${API_URL}/api/v1/user/guest`);
    expect(res.ok()).toBeTruthy();

    const body = await res.json() as {
      access_token: string;
      token_type: string;
      user: { id: number; username: string; is_active: boolean; profile?: unknown };
    };

    expect(body.access_token).toBeTruthy();
    expect(body.token_type).toBe('bearer');
    expect(body.user.username).toMatch(/^guest_[a-f0-9]{8}$/);
    expect(body.user.is_active).toBe(true);
    expect(body.user.id).toBeGreaterThan(0);
    expect(body.user.profile).toBeDefined();
  });

  test('each guest call creates a unique user', async ({ page }) => {
    const res1 = await page.request.post(`${API_URL}/api/v1/user/guest`);
    const res2 = await page.request.post(`${API_URL}/api/v1/user/guest`);

    const body1 = await res1.json() as { user: { username: string } };
    const body2 = await res2.json() as { user: { username: string } };

    expect(body1.user.username).not.toBe(body2.user.username);
  });

  test('guest token can access protected endpoints', async ({ page }) => {
    const guestRes = await page.request.post(`${API_URL}/api/v1/user/guest`);
    const { access_token } = await guestRes.json() as { access_token: string };

    const userRes = await page.request.get(`${API_URL}/api/v1/user`, {
      headers: { Authorization: `Bearer ${access_token}` },
    });
    expect(userRes.ok()).toBeTruthy();

    const user = await userRes.json() as { username: string };
    expect(user.username).toMatch(/^guest_/);
  });

  test('bootstrap auto-creates guest and redirects to home', async ({ page }) => {
    // Visit a protected page with empty auth — triggers bootstrap guest login
    await page.goto(BASE_URL);

    // Wait for the guest API call to fire and complete
    const guestRes = await page.waitForResponse(
      r => r.url().includes('/api/v1/user/guest') && r.request().method() === 'POST',
      { timeout: 15_000 },
    );
    expect(guestRes.status()).toBe(200);

    // After bootstrap sets auth state, the app navigates away from /login
    await page.waitForURL(url => !url.pathname.includes('login'), { timeout: 10_000 });
    await page.waitForTimeout(1_000);

    // Verify guest token is in localStorage
    const token = await page.evaluate(() =>
      localStorage.getItem('ai_investment_access_token'),
    );
    expect(token).toBeTruthy();

    // Verify the token is valid by calling the user endpoint
    const userRes = await page.request.get(`${API_URL}/api/v1/user`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(userRes.ok()).toBeTruthy();
    const user = await userRes.json() as { username: string };
    expect(user.username).toMatch(/^guest_/);
  });
});
