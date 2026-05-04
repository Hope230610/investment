import { afterEach, describe, expect, it, vi } from 'vitest';

import { apiRequest, ApiError } from './api';


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
