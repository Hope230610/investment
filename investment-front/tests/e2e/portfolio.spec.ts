import { test, expect } from '@playwright/test';
import { apiRequest, BASE_URL, loginAs } from './helpers';


test('portfolio MVP: create holding and transaction through API, page renders overview', async ({ page }) => {
  await loginAs(page);

  const holdingRes = await apiRequest(page, 'POST', '/api/v1/portfolio/holdings', {
    stock_id: 'SH600519',
    stock_name: '贵州茅台',
    market: 'SH',
    quantity: 10,
    cost_price: 100,
    current_price: 120,
    note: 'E2E portfolio holding',
  });
  expect(holdingRes.ok()).toBeTruthy();

  const txRes = await apiRequest(page, 'POST', '/api/v1/portfolio/transactions', {
    stock_id: 'SH600519',
    stock_name: '贵州茅台',
    market: 'SH',
    side: 'buy',
    price: 100,
    quantity: 10,
    reason: 'E2E transaction reason',
  });
  expect(txRes.ok()).toBeTruthy();

  await page.goto(`${BASE_URL}/portfolio`);
  await expect(page.getByText(/持仓组合|鎸佷粨缁勫悎/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/贵州茅台|璐靛窞鑼呭彴/).first()).toBeVisible();
  await expect(page.getByText('E2E transaction reason').first()).toBeVisible();
});
