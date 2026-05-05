import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import { ApiError, apiGet, apiPost } from './api';
import {
  clearAuthSession,
  readAuthSession,
  saveAuthSession,
  subscribeAuthChange,
} from './auth';
import type { AuthUser, LoginResponse } from './types';

interface AuthContextValue {
  isAuthenticated: boolean;
  isBootstrapping: boolean;
  token: string | null;
  user: AuthUser | null;
  sessionError: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  clearSessionError: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => readAuthSession()?.accessToken ?? null);
  const [user, setUser] = useState<AuthUser | null>(() => readAuthSession()?.user ?? null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [sessionError, setSessionError] = useState<string | null>(null);

  useEffect(() => {
    const syncFromStorage = () => {
      const session = readAuthSession();
      setToken(session?.accessToken ?? null);
      setUser(session?.user ?? null);
    };

    syncFromStorage();
    return subscribeAuthChange(syncFromStorage);
  }, []);

  useEffect(() => {
    let cancelled = false;

    const bootstrap = async () => {
      const session = readAuthSession();
      if (!session?.accessToken) {
        if (!cancelled) {
          setIsBootstrapping(false);
        }
        return;
      }

      const controller = new AbortController();
      const timeoutId = window.setTimeout(() => controller.abort(), 8000);
      try {
        const currentUser = await apiGet<AuthUser>('/api/v1/user', { signal: controller.signal });
        if (cancelled) {
          return;
        }

        saveAuthSession({
          accessToken: session.accessToken,
          user: currentUser,
        });
      } catch (error) {
        if (!cancelled && error instanceof ApiError && error.status === 401) {
          clearAuthSession();
          setSessionError('会话已过期，请重新登录');
        }
      } finally {
        window.clearTimeout(timeoutId);
        if (!cancelled) {
          setIsBootstrapping(false);
        }
      }
    };

    bootstrap();

    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated: Boolean(token),
      isBootstrapping,
      token,
      user,
      sessionError,
      async login(username: string, password: string) {
        const response = await apiPost<LoginResponse>(
          '/api/v1/user/login',
          { username, password },
          { auth: false },
        );

        saveAuthSession({
          accessToken: response.access_token,
          user: response.user,
        });
        setToken(response.access_token);
        setUser(response.user);
        setSessionError(null);
      },
      logout() {
        clearAuthSession();
        setToken(null);
        setUser(null);
        setSessionError(null);
      },
      clearSessionError: () => setSessionError(null),
    }),
    [isBootstrapping, token, user, sessionError],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  const location = useLocation();

  if (auth.isBootstrapping) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-stone-100 text-stone-500">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-stone-200 border-t-ink rounded-full animate-spin" />
          <span className="text-sm">Loading session...</span>
        </div>
      </div>
    );
  }

  if (!auth.isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <>{children}</>;
}
