import React, { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { LockKeyhole, LogIn, UserRound } from 'lucide-react';

import { useAuth } from '../auth-context';

function getDefaultCredentials() {
  const isLocalhost =
    window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

  if (!isLocalhost) {
    return { username: '', password: '' };
  }

  return {
    username: 'testuser',
    password: 'testpassword123',
  };
}

export default function LoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = location.state?.from?.pathname || '/';
  const defaults = getDefaultCredentials();

  const [username, setUsername] = useState(defaults.username);
  const [password, setPassword] = useState(defaults.password);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!auth.isBootstrapping && auth.isAuthenticated) {
    return <Navigate to={redirectTo} replace />;
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitting) {
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await auth.login(username.trim(), password);
      navigate(redirectTo, { replace: true });
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : '登录失败，请稍后重试');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(245,158,11,0.22),_transparent_42%),linear-gradient(180deg,_#f8fafc_0%,_#f5f5f4_100%)] px-5 py-8">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-md flex-col justify-center">
        <div className="rounded-[28px] border border-white/70 bg-white/90 p-7 shadow-[0_24px_80px_rgba(15,23,42,0.12)] backdrop-blur">
          <div className="mb-8 space-y-3">
            <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-ink text-white">
              <LogIn size={22} />
            </div>
            <div className="space-y-2">
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-stone-400">
                AI Financial Literacy Coach
              </p>
              <h1 className="text-3xl font-bold tracking-tight text-stone-900">AI 金融素养教练</h1>
              <p className="text-sm leading-relaxed text-stone-500">
                面向大学生的校园消费自检 Demo：登录后可体验小林分期买 5999 元手机、冷静期问题、决策卡和月底复盘；系统不会替你选择金融产品或安排借贷。
              </p>
            </div>
          </div>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <label className="block space-y-2">
              <span className="text-xs font-bold uppercase tracking-widest text-stone-400">
                用户名
              </span>
              <div className="flex items-center gap-3 rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3">
                <UserRound size={18} className="text-stone-400" />
                <input
                  type="text"
                  autoComplete="username"
                  className="w-full bg-transparent text-sm text-stone-800 outline-none"
                  placeholder="请输入用户名"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                />
              </div>
            </label>

            <label className="block space-y-2">
              <span className="text-xs font-bold uppercase tracking-widest text-stone-400">
                密码
              </span>
              <div className="flex items-center gap-3 rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3">
                <LockKeyhole size={18} className="text-stone-400" />
                <input
                  type="password"
                  autoComplete="current-password"
                  className="w-full bg-transparent text-sm text-stone-800 outline-none"
                  placeholder="请输入密码"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </div>
            </label>

            {error && (
              <div className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            {defaults.username && defaults.password && (
              <div className="rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3 text-xs leading-relaxed text-amber-800">
                当前本地开发环境已预填测试账号，可直接登录验证完整主路径；Demo 使用模拟数据，未真实调用外部 PCG API。
              </div>
            )}

            <button
              type="submit"
              disabled={!username.trim() || !password || submitting}
              className="w-full rounded-2xl bg-ink py-4 text-sm font-bold text-white transition-all disabled:cursor-not-allowed disabled:opacity-40"
            >
              {submitting ? '登录中...' : '进入系统'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
