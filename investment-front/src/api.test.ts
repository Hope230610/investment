import { afterEach, describe, expect, it, vi } from 'vitest';

import { apiRequest, ApiError, getPortfolioOverview, postHolding, postTransaction } from './api';


function mockJsonResponse(status: number, body: unknown) {
  globalThis.fetch = vi.fn(async () => new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })) as unknown as typeof fetch;
}


describe('api error parsing', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('uses unified error response when backend returns error envelope', async () => {
    mockJsonResponse(502, {
      error: {
        code: 'MARKET_DATA_UNAVAILABLE',
        message: '暂时无法获取行情数据',
        request_id: 'req-1',
        retryable: true,
      },
    });

    await expect(apiRequest('/api/v1/analysis', { auth: false })).rejects.toMatchObject({
      name: 'ApiError',
      status: 502,
      code: 'MARKET_DATA_UNAVAILABLE',
      message: '暂时无法获取行情数据',
      request_id: 'req-1',
      retryable: true,
    } satisfies Partial<ApiError>);
  });

  it('formats legacy validation detail arrays into a stable message', async () => {
    mockJsonResponse(422, {
      detail: [
        { loc: ['body', 'stock_id'], msg: 'Field required' },
        { loc: ['body', 'scenario'], msg: 'Input should be valid' },
      ],
    });

    await expect(apiRequest('/api/v1/analysis', { auth: false })).rejects.toMatchObject({
      status: 422,
      code: 'HTTP_422',
      message: '请求参数校验失败：stock_id: Field required；scenario: Input should be valid',
      retryable: false,
    } satisfies Partial<ApiError>);
  });
});

describe('portfolio api helpers', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('loads portfolio overview from the P2 endpoint', async () => {
    vi.stubGlobal('localStorage', { getItem: () => null, removeItem: vi.fn(), setItem: vi.fn() });
    mockJsonResponse(200, {
      summary: { holding_count: 0, total_market_value: 0, total_cost_value: 0, total_unrealized_pnl: 0, total_unrealized_pnl_rate: 0, max_position_weight: 0, risk_tips: [] },
      holdings: [],
    });

    await expect(getPortfolioOverview()).resolves.toMatchObject({
      summary: { holding_count: 0 },
      holdings: [],
    });
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/v1/portfolio/overview', expect.objectContaining({ method: 'GET' }));
  });

  it('posts holding and transaction payloads as json', async () => {
    vi.stubGlobal('localStorage', { getItem: () => null, removeItem: vi.fn(), setItem: vi.fn() });
    mockJsonResponse(200, { id: 'h1' });
    await postHolding({ stock_id: 'SZ000200', stock_name: '5999元手机分期', market: 'SZ', quantity: 1, cost_price: 5999, current_price: 5999 });
    expect(globalThis.fetch).toHaveBeenLastCalledWith('/api/v1/portfolio/holdings', expect.objectContaining({ method: 'POST' }));

    mockJsonResponse(200, { id: 't1' });
    await postTransaction({ stock_id: 'SZ000200', stock_name: '5999元手机分期', market: 'SZ', side: 'buy', price: 5999, quantity: 1, reason: '校园预算复盘' });
    expect(globalThis.fetch).toHaveBeenLastCalledWith('/api/v1/portfolio/transactions', expect.objectContaining({ method: 'POST' }));
  });
});
