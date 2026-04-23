/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import { Home, LayoutGrid, History, User, ChevronLeft, Star } from 'lucide-react';

import { AuthProvider, RequireAuth } from './auth-context';
import { cn, computeUnfinishedReviews } from './utils';
import { apiGet } from './api';
import type { ReviewTask } from './types';

import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import MePage from './pages/MePage';
import ProfilePage from './pages/ProfilePage';
import StockSearchPage from './pages/StockSearchPage';
import SingleStockInput from './pages/SingleStockInput';
import PreTradeInput from './pages/PreTradeInput';
import PostTradeInput from './pages/PostTradeInput';
import ResultPage from './pages/ResultPage';
import ReviewsPage from './pages/ReviewsPage';
import RecordsPage from './pages/RecordsPage';
import WatchlistPage from './pages/WatchlistPage';

function AppShell({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const isResultPage = location.pathname.includes('/result');
  const isInputPage = location.pathname.includes('/analysis/') && !isResultPage;
  const isLoginPage = location.pathname === '/login';

  const [unfinishedReviews, setUnfinishedReviews] = useState<ReviewTask[]>([]);

  const MAIN_NAV_PATHS = ['/', '/watchlist', '/reviews', '/records', '/me'];

  const fetchUnfinishedReviews = () => {
    apiGet<ReviewTask[]>('/api/v1/reviews')
      .then((data) => setUnfinishedReviews(computeUnfinishedReviews(data)))
      .catch(() => setUnfinishedReviews([]));
  };

  // Refresh when returning to any main nav page (e.g. after completing a review)
  useEffect(() => {
    if (MAIN_NAV_PATHS.some((p) => location.pathname === p)) {
      fetchUnfinishedReviews();
    }
  }, [location.pathname]);

  // Refresh when window regains focus (covers tab-switch scenario)
  useEffect(() => {
    const onFocus = () => fetchUnfinishedReviews();
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, []);

  const navItems = [
    { path: '/', label: '首页', icon: Home },
    { path: '/watchlist', label: '观察', icon: Star },
    { path: '/reviews', label: '复盘', icon: LayoutGrid },
    { path: '/records', label: '记录', icon: History },
    { path: '/me', label: '我的', icon: User },
  ];

  if (isLoginPage) {
    return <div className="min-h-screen bg-stone-100">{children}</div>;
  }

  return (
    <div className="flex min-h-screen max-w-md flex-col bg-stone-50 shadow-xl relative mx-auto">
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-stone-200 bg-white/80 px-4 backdrop-blur-md">
        <div className="flex items-center gap-2">
          {location.pathname !== '/' && (
            <Link to={-1 as never} className="rounded-full p-1 -ml-1 transition-colors hover:bg-stone-100">
              <ChevronLeft size={20} />
            </Link>
          )}
          <h1 className="text-lg font-semibold tracking-tight">AI 投资助手</h1>
        </div>
        <div className="text-[10px] font-bold uppercase tracking-widest opacity-30">REAL DATA</div>
      </header>

      <main className="flex-1 pb-24">{children}</main>

      {!isInputPage && !isResultPage && (
        <nav className="safe-bottom fixed bottom-0 left-1/2 z-40 flex h-16 w-full max-w-md -translate-x-1/2 items-center justify-between border-t border-stone-200 bg-white px-6">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            const isReviews = item.path === '/reviews';
            const count = isReviews ? unfinishedReviews.length : 0;
            const hasExpired = isReviews && unfinishedReviews.some((t) => t.status === 'expired');

            return (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  'relative flex flex-col items-center gap-1 transition-colors',
                  isActive ? 'text-ink' : 'text-stone-400 hover:text-stone-600',
                )}
              >
                <div className="relative">
                  <Icon size={20} strokeWidth={isActive ? 2.5 : 2} />
                  {count > 0 && (
                    <span
                      className={cn(
                        'absolute -top-1.5 -right-2 min-w-[16px] h-4 flex items-center justify-center rounded-full text-[9px] font-bold text-white px-1',
                        hasExpired ? 'bg-red-500' : 'bg-amber-500',
                      )}
                    >
                      {count > 99 ? '99+' : count}
                    </span>
                  )}
                </div>
                <span className="text-[10px] font-medium">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      )}
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <AuthProvider>
        <AppShell>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<RequireAuth><HomePage /></RequireAuth>} />
            <Route path="/me" element={<RequireAuth><MePage /></RequireAuth>} />
            <Route path="/profile" element={<RequireAuth><ProfilePage /></RequireAuth>} />
            <Route path="/watchlist" element={<RequireAuth><WatchlistPage /></RequireAuth>} />
            <Route path="/stock/search" element={<RequireAuth><StockSearchPage /></RequireAuth>} />
            <Route path="/analysis/single-stock" element={<RequireAuth><SingleStockInput /></RequireAuth>} />
            <Route path="/analysis/pre-trade" element={<RequireAuth><PreTradeInput /></RequireAuth>} />
            <Route path="/analysis/post-trade" element={<RequireAuth><PostTradeInput /></RequireAuth>} />
            <Route path="/analysis/:id/result" element={<RequireAuth><ResultPage /></RequireAuth>} />
            <Route path="/reviews" element={<RequireAuth><ReviewsPage /></RequireAuth>} />
            <Route path="/records" element={<RequireAuth><RecordsPage /></RequireAuth>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AppShell>
      </AuthProvider>
    </Router>
  );
}
