import { test, expect } from '@playwright/test';
import { apiRequest, BASE_URL, loginAs } from './helpers';


test('budget MVP: create campus spending item and review transaction through API, page renders overview', async ({ page }) => {
  await loginAs(page);

  const holdingRes = await apiRequest(page, 'POST', '/api/v1/portfolio/holdings', {
    stock_id: 'SZ000200',
    stock_name: '5999元手机分期',
    market: 'SZ',
    quantity: 1,
    cost_price: 5999,
    current_price: 5999,
    note: 'E2E campus installment budget item',
  });
  expect(holdingRes.ok()).toBeTruthy();

  const txRes = await apiRequest(page, 'POST', '/api/v1/portfolio/transactions', {
    stock_id: 'SZ000200',
    stock_name: '5999元手机分期',
    market: 'SZ',
    side: 'buy',
    price: 5999,
    quantity: 1,
    reason: 'E2E campus budget review reason',
  });
  expect(txRes.ok()).toBeTruthy();

  await page.goto(`${BASE_URL}/portfolio`);
  await expect(page.getByText(/预算|持仓组合|鎸佷粨缁勫悎/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/5999元手机分期/).first()).toBeVisible();
  await expect(page.getByText('E2E campus budget review reason').first()).toBeVisible();
});
