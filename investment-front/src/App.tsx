/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import { Home, History, User, ChevronLeft, Star, Bell, PieChart } from 'lucide-react';

import { AuthProvider, RequireAuth } from './auth-context';
import { cn } from './utils';
import { getNotificationSummary } from './api';
import type { NotificationSummary } from './types';

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
import NotificationsPage from './pages/NotificationsPage';
import PortfolioPage from './pages/PortfolioPage';
import SharePage from './pages/SharePage';

function AppShell({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const isResultPage = location.pathname.includes('/result');
  const isInputPage = location.pathname.includes('/analysis/') && !isResultPage;
  const isLoginPage = location.pathname === '/login';

  const [notifSummary, setNotifSummary] = useState<NotificationSummary | null>(null);

  const MAIN_NAV_PATHS = ['/', '/portfolio', '/watchlist', '/notifications', '/records', '/me'];
  const shouldRefreshNotificationBadge = MAIN_NAV_PATHS.some((p) => location.pathname === p);

  const fetchNotifSummary = () => {
    getNotificationSummary()
      .then(setNotifSummary)
      .catch(() => setNotifSummary(null));
  };

  // Refresh when returning to any main nav page
  useEffect(() => {
    if (shouldRefreshNotificationBadge) {
      fetchNotifSummary();
    }
  }, [shouldRefreshNotificationBadge]);

  // Refresh when window regains focus
  useEffect(() => {
    const onFocus = () => {
      if (shouldRefreshNotificationBadge) {
        fetchNotifSummary();
      }
    };
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [shouldRefreshNotificationBadge]);

  const navItems = [
    { path: '/', label: '首页', icon: Home },
    { path: '/portfolio', label: '持仓', icon: PieChart },
    { path: '/watchlist', label: '观察', icon: Star },
    { path: '/notifications', label: '提醒', icon: Bell },
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
        <nav className="safe-bottom fixed bottom-0 left-1/2 z-40 flex h-16 w-full max-w-md -translate-x-1/2 items-center justify-between border-t border-stone-200 bg-white px-4">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            const isNotifications = item.path === '/notifications';
            // 提醒总数（overdue + due_soon）作为 badge
            const unreadCount = isNotifications
              ? (notifSummary?.overdue_count ?? 0) + (notifSummary?.due_soon_count ?? 0)
              : 0;
            const hasUrgent = isNotifications && (notifSummary?.overdue_count ?? 0) > 0;

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
                  {unreadCount > 0 && (
                    <span
                      className={cn(
                        'absolute -top-1.5 -right-2 min-w-[16px] h-4 flex items-center justify-center rounded-full text-[9px] font-bold text-white px-1',
                        hasUrgent ? 'bg-red-500' : 'bg-amber-500',
                      )}
                    >
                      {unreadCount > 99 ? '99+' : unreadCount}
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
            <Route path="/portfolio" element={<RequireAuth><PortfolioPage /></RequireAuth>} />
            <Route path="/stock/search" element={<RequireAuth><StockSearchPage /></RequireAuth>} />
            <Route path="/analysis/single-stock" element={<RequireAuth><SingleStockInput /></RequireAuth>} />
            <Route path="/analysis/pre-trade" element={<RequireAuth><PreTradeInput /></RequireAuth>} />
            <Route path="/analysis/post-trade" element={<RequireAuth><PostTradeInput /></RequireAuth>} />
            <Route path="/analysis/:id/result" element={<RequireAuth><ResultPage /></RequireAuth>} />
            <Route path="/share/:shareId" element={<SharePage />} />
            <Route path="/notifications" element={<RequireAuth><NotificationsPage /></RequireAuth>} />
            <Route path="/reviews" element={<RequireAuth><ReviewsPage /></RequireAuth>} />
            <Route path="/records" element={<RequireAuth><RecordsPage /></RequireAuth>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AppShell>
      </AuthProvider>
    </Router>
  );
}
