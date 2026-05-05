import { describe, expect, it } from 'vitest';

import { normalizeHoldingContext } from './ResultPage';

describe('normalizeHoldingContext', () => {
  it('renders placeholders for missing or malformed holding context fields', () => {
    const normalized = normalizeHoldingContext({
      stock_name: '',
      weight: '0.5',
      cost_price: null,
      current_price: '100',
      unrealized_pnl: {},
      position_updated_at: 123,
    });

    expect(normalized).toEqual({
      stockName: '--',
      weightPercent: '--',
      costPrice: '--',
      currentPrice: '--',
      unrealizedPnl: '--',
      positionUpdatedAt: null,
    });
  });

  it('keeps valid server-generated numeric holding context fields', () => {
    const normalized = normalizeHoldingContext({
      stock_name: 'Test Stock',
      weight: 0.125,
      cost_price: 10,
      current_price: 12.345,
      unrealized_pnl: 234.5,
      position_updated_at: '2026-05-05T12:00:00Z',
    });

    expect(normalized).toEqual({
      stockName: 'Test Stock',
      weightPercent: '12.5',
      costPrice: '10.00',
      currentPrice: '12.35',
      unrealizedPnl: '234.50',
      positionUpdatedAt: '2026-05-05T12:00:00Z',
    });
  });
});
