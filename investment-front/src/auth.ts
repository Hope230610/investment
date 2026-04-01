import type { AuthUser } from './types';

const AUTH_CHANGE_EVENT = 'ai-investment-auth-change';

export const AUTH_STORAGE_KEYS = {
  ACCESS_TOKEN: 'ai_investment_access_token',
  USER: 'ai_investment_user',
} as const;

export interface AuthSession {
  accessToken: string;
  user: AuthUser | null;
}

function emitAuthChange() {
  window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
}

export function readAuthSession(): AuthSession | null {
  const accessToken = localStorage.getItem(AUTH_STORAGE_KEYS.ACCESS_TOKEN);
  if (!accessToken) {
    return null;
  }

  const rawUser = localStorage.getItem(AUTH_STORAGE_KEYS.USER);
  let user: AuthUser | null = null;

  if (rawUser) {
    try {
      user = JSON.parse(rawUser) as AuthUser;
    } catch {
      user = null;
    }
  }

  return { accessToken, user };
}

export function getAccessToken() {
  return localStorage.getItem(AUTH_STORAGE_KEYS.ACCESS_TOKEN);
}

export function saveAuthSession(session: AuthSession) {
  localStorage.setItem(AUTH_STORAGE_KEYS.ACCESS_TOKEN, session.accessToken);
  if (session.user) {
    localStorage.setItem(AUTH_STORAGE_KEYS.USER, JSON.stringify(session.user));
  } else {
    localStorage.removeItem(AUTH_STORAGE_KEYS.USER);
  }
  emitAuthChange();
}

export function clearAuthSession() {
  localStorage.removeItem(AUTH_STORAGE_KEYS.ACCESS_TOKEN);
  localStorage.removeItem(AUTH_STORAGE_KEYS.USER);
  emitAuthChange();
}

export function subscribeAuthChange(listener: () => void) {
  const handleStorage = (event: StorageEvent) => {
    if (
      event.key === AUTH_STORAGE_KEYS.ACCESS_TOKEN ||
      event.key === AUTH_STORAGE_KEYS.USER ||
      event.key === null
    ) {
      listener();
    }
  };

  window.addEventListener(AUTH_CHANGE_EVENT, listener);
  window.addEventListener('storage', handleStorage);

  return () => {
    window.removeEventListener(AUTH_CHANGE_EVENT, listener);
    window.removeEventListener('storage', handleStorage);
  };
}
