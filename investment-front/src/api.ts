import { clearAuthSession, getAccessToken } from './auth';
import type { CreateSharePayload, HoldingPayload, ShareSnapshot, TransactionPayload, WatchlistApiItem } from './types';

/** 统一错误响应结构（与后端 ErrorResponse 对应） */
export interface UnifiedError {
  code: string;
  message: string;
  request_id?: string;
  retryable?: boolean;
}

export interface UnifiedErrorResponse {
  error: UnifiedError;
}

/** 旧 detail 风格（向后兼容，短期保留） */
interface LegacyErrorDetail {
  detail: unknown;
}

export class ApiError extends Error {
  status: number;
  code: string;
  request_id?: string;
  retryable: boolean;
  payload: unknown;

  constructor(message: string, status: number, code: string, request_id?: string, retryable = false, payload?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.request_id = request_id;
    this.retryable = retryable;
    this.payload = payload ?? null;
  }
}

interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  auth?: boolean;
  body?: BodyInit | Record<string, unknown> | null;
}

function isBodyInit(value: unknown): value is BodyInit {
  return (
    typeof value === 'string' ||
    value instanceof FormData ||
    value instanceof Blob ||
    value instanceof URLSearchParams ||
    value instanceof ArrayBuffer ||
    ArrayBuffer.isView(value)
  );
}

async function parseResponseBody(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json();
  }

  const text = await response.text();
  return text ? text : null;
}

function parseErrorPayload(
  payload: unknown,
  status: number,
): { message: string; code: string; request_id?: string; retryable: boolean } {
  // 优先解析统一 error 结构
  if (payload && typeof payload === 'object' && 'error' in payload) {
    const err = (payload as UnifiedErrorResponse).error;
    return {
      message: err.message || 'An error occurred',
      code: err.code || `HTTP_${status}`,
      request_id: err.request_id,
      retryable: err.retryable ?? false,
    };
  }

  // 旧 detail 风格（向后兼容，短期保留）
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as LegacyErrorDetail).detail;
    const message = formatLegacyDetail(detail);
    return {
      message,
      code: `HTTP_${status}`,
      retryable: false,
    };
  }

  return {
    message: `Request failed with status ${status}`,
    code: `HTTP_${status}`,
    retryable: false,
  };
}

function formatLegacyDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail;

  if (Array.isArray(detail)) {
    const messages = detail
      .slice(0, 3)
      .map((item) => {
        if (!item || typeof item !== 'object') return null;
        const obj = item as { loc?: unknown; msg?: unknown };
        const loc = Array.isArray(obj.loc)
          ? obj.loc.filter((part) => part !== 'body').join('.')
          : '';
        const msg = typeof obj.msg === 'string' ? obj.msg : '';
        if (!msg) return null;
        return loc ? `${loc}: ${msg}` : msg;
      })
      .filter(Boolean);
    if (messages.length > 0) return `请求参数校验失败：${messages.join('；')}`;
  }

  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message?: unknown }).message || 'An error occurred');
  }

  return 'An error occurred';
}

export async function apiRequest<T>(url: string, options: ApiRequestOptions = {}): Promise<T> {
  const { auth = true, body, headers: rawHeaders, ...rest } = options;
  const headers = new Headers(rawHeaders);

  if (auth) {
    const token = getAccessToken();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
  }

  let requestBody: BodyInit | undefined;
  if (body !== undefined && body !== null) {
    if (isBodyInit(body)) {
      requestBody = body;
    } else {
      headers.set('Content-Type', 'application/json');
      requestBody = JSON.stringify(body);
    }
  }

  const response = await fetch(url, {
    ...rest,
    headers,
    body: requestBody,
  });

  const payload = await parseResponseBody(response);
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      clearAuthSession();
    }
    const { message, code, request_id, retryable } = parseErrorPayload(payload, response.status);
    throw new ApiError(message, response.status, code, request_id, retryable, payload);
  }

  return payload as T;
}

export function apiGet<T>(url: string, options: Omit<ApiRequestOptions, 'method' | 'body'> = {}) {
  return apiRequest<T>(url, { ...options, method: 'GET' });
}

export function apiPost<T>(
  url: string,
  body?: ApiRequestOptions['body'],
  options: Omit<ApiRequestOptions, 'method' | 'body'> = {},
) {
  return apiRequest<T>(url, { ...options, method: 'POST', body });
}

export function apiPut<T>(
  url: string,
  body?: ApiRequestOptions['body'],
  options: Omit<ApiRequestOptions, 'method' | 'body'> = {},
) {
  return apiRequest<T>(url, { ...options, method: 'PUT', body });
}

export function apiDelete<T>(url: string, options: Omit<ApiRequestOptions, 'method' | 'body'> = {}) {
  return apiRequest<T>(url, { ...options, method: 'DELETE' });
}

// ─── Watchlist v2 ───────────────────────────────────────────────────────────────

export interface WatchlistUpsertPayload {
  stock_id: string;
  focus_reason?: string | null;
}

export interface WatchlistUpdatePayload {
  focus_reason?: string | null;
}

/** B1a 冻结的观察列表专用 API；B1b 页面切换时直接复用。 */
export function getWatchlistItems() {
  return apiGet<WatchlistApiItem[]>('/api/v1/watchlist');
}

export function postWatchlistItem(payload: WatchlistUpsertPayload) {
  return apiPost<WatchlistApiItem>(
    '/api/v1/watchlist',
    payload as unknown as Record<string, unknown>,
  );
}

export function putWatchlistItem(itemId: string, payload: WatchlistUpdatePayload) {
  return apiPut<WatchlistApiItem>(
    `/api/v1/watchlist/${itemId}`,
    payload as unknown as Record<string, unknown>,
  );
}

export function deleteWatchlistItem(itemId: string) {
  return apiRequest<{ message: string }>(`/api/v1/watchlist/${itemId}`, {
    method: 'DELETE',
    auth: true,
  });
}

// Portfolio

export function getPortfolioOverview() {
  return apiGet<import('./types').PortfolioOverview>('/api/v1/portfolio/overview');
}

export function postHolding(payload: HoldingPayload) {
  return apiPost<import('./types').HoldingItem>(
    '/api/v1/portfolio/holdings',
    payload as unknown as Record<string, unknown>,
  );
}

export function putHolding(holdingId: string, payload: Partial<HoldingPayload>) {
  return apiPut<import('./types').HoldingItem>(
    `/api/v1/portfolio/holdings/${holdingId}`,
    payload as unknown as Record<string, unknown>,
  );
}

export function deleteHolding(holdingId: string) {
  return apiDelete<{ message: string }>(`/api/v1/portfolio/holdings/${holdingId}`);
}

export function getTransactions(stockId?: string) {
  const query = stockId ? `?stock_id=${encodeURIComponent(stockId)}` : '';
  return apiGet<import('./types').TransactionItem[]>(`/api/v1/portfolio/transactions${query}`);
}

export function postTransaction(payload: TransactionPayload) {
  return apiPost<import('./types').TransactionItem>(
    '/api/v1/portfolio/transactions',
    payload as unknown as Record<string, unknown>,
  );
}

export function createShareSnapshot(payload: CreateSharePayload) {
  return apiPost<ShareSnapshot>(
    '/api/v1/p3/shares',
    payload as unknown as Record<string, unknown>,
  );
}

export function getPublicShareSnapshot(shareId: string) {
  return apiGet<ShareSnapshot>(`/api/v1/p3/public/shares/${shareId}`, { auth: false });
}

export function revokeShareSnapshot(shareId: string) {
  return apiDelete<{ message: string }>(`/api/v1/p3/shares/${shareId}`);
}

// ─── Learning Feedback ──────────────────────────────────────────────────────────

/** 行为标签更新项（POST learning-feedback 请求体） */
export interface TagUpdatePayload {
  tag: string;
  type: 'add' | 'remove' | 'upgrade';
  source: string;
}

/** POST /api/v1/user/profile/learning-feedback 请求体 */
export interface LearningFeedbackPayload {
  analysis_task_id?: string;
  tag_updates: TagUpdatePayload[];
  judgment_quality: string;
  emotion_level: number;
  intent?: string;
  trigger_reason?: string;
}

/** POST /api/v1/user/profile/learning-feedback 响应体 */
export interface LearningFeedbackResponse {
  success: boolean;
  tags_updated: number;
  judgment_recorded: boolean;
}

/**
 * 获取画像学习历史：情绪历史 + 判断质量历史
 * GET /api/v1/user/profile/learning-history?days=30
 */
export async function getLearningHistory(days = 30) {
  return apiGet<{
    emotion_history: { date: string; level: number }[];
    judgment_history: { date: string; score: number; label: string; is_hard_to_tell: boolean }[];
  }>(`/api/v1/user/profile/learning-history?days=${days}`);
}

/**
 * 写入学习反馈：行为标签更新 + 情绪历史 + 判断质量历史
 * POST /api/v1/user/profile/learning-feedback
 */
export async function postLearningFeedback(data: LearningFeedbackPayload) {
  return apiPost<LearningFeedbackResponse>(
    '/api/v1/user/profile/learning-feedback',
    data as unknown as Record<string, unknown>,
  );
}

/**
 * 通过整数 review_task_id 更新复盘任务并标记为已完成
 * PATCH /api/v1/reviews/:review_task_id
 */
export async function patchReviewTask(
  reviewTaskId: number,
  reviewResult: Record<string, unknown>,
) {
  return apiRequest<unknown>(
    `/api/v1/reviews/${reviewTaskId}`,
    {
      method: 'PATCH',
      auth: true,
      body: { review_result: reviewResult, mark_completed: true },
    },
  );
}

/**
 * 通过 analysis_task_id 更新复盘任务并标记为已完成
 * PATCH /api/v1/reviews/by-analysis/:analysis_task_id
 */
export async function patchReviewResult(
  analysisTaskId: string,
  reviewResult: Record<string, unknown>,
) {
  return apiRequest<unknown>(
    `/api/v1/reviews/by-analysis/${analysisTaskId}`,
    {
      method: 'PATCH',
      auth: true,
      body: { review_result: reviewResult, mark_completed: true },
    },
  );
}

// ─── 提醒中心 ───────────────────────────────────────────────────────────────────

/**
 * 获取完整提醒列表（聚合：复盘提醒 + 观察池异动 + 分析失效）
 * GET /api/v1/notifications
 */
export function getNotifications() {
  return apiGet<import('./types').NotificationListResponse>('/api/v1/notifications');
}

/**
 * 获取提醒摘要（轻量接口，用于 Tab Badge 数字）
 * GET /api/v1/notifications/summary
 */
export function getNotificationSummary() {
  return apiGet<import('./types').NotificationSummary>('/api/v1/notifications/summary');
}

