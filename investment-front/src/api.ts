import { clearAuthSession, getAccessToken } from './auth';

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
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

async function parseResponseBody(response: Response) {
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

function toErrorMessage(payload: unknown, fallback: string) {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = Reflect.get(payload, 'detail');
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
  }
  return fallback;
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
    if (response.status === 401) {
      clearAuthSession();
    }
    throw new ApiError(
      toErrorMessage(payload, `Request failed with status ${response.status}`),
      response.status,
      payload,
    );
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
