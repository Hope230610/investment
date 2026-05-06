import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight, Info, LogOut, Settings, User } from 'lucide-react';

import { apiGet } from '../api';
import type { UserProfile } from '../types';
import { useAuth } from '../auth-context';
import { cn } from '../utils';


interface UserInfo {
  id: number;
  username: string;
  email: string | null;
  is_active: boolean;
  created_at: string;
}


export default function MePage() {
  const { user, logout } = useAuth();
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const [infoResult, profileResult] = await Promise.allSettled([
          apiGet<UserInfo>('/api/v1/user'),
          apiGet<UserProfile>('/api/v1/user/profile'),
        ]);

        if (!cancelled) {
          if (infoResult.status === 'fulfilled') {
            setUserInfo(infoResult.value);
          }
          if (profileResult.status === 'fulfilled') {
            setProfile(profileResult.value);
          }
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleLogout = () => {
    logout();
  };

  if (loading) {
    return (
      <div className="p-4 space-y-6">
        <div className="h-32 bg-white rounded-2xl animate-pulse" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-white rounded-2xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const riskLabel = profile?.risk_tolerance === 'low' ? '低'
    : profile?.risk_tolerance === 'medium' ? '中'
    : profile?.risk_tolerance === 'high' ? '高' : '未设置';

  const horizonLabel = profile?.holding_horizon === 'short' ? '短期'
    : profile?.holding_horizon === 'medium' ? '中期'
    : profile?.holding_horizon === 'long' ? '长期' : '未设置';

  return (
    <div className="p-4 space-y-6">
      {/* 个人信息卡片 */}
      <div className="bg-white rounded-2xl p-5 border border-stone-100 space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-stone-100 flex items-center justify-center">
            <User size={24} className="text-stone-400" />
          </div>
          <div>
            <div className="font-bold text-lg">
              {userInfo?.username || user?.username || '用户'}
            </div>
            {userInfo?.email && (
              <div className="text-xs text-stone-400">{userInfo.email}</div>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <span className="px-2 py-1 bg-stone-50 rounded-md text-[10px] font-medium uppercase tracking-wider">
            承受能力：{riskLabel}
          </span>
          <span className="px-2 py-1 bg-stone-50 rounded-md text-[10px] font-medium uppercase tracking-wider">
            规划周期：{horizonLabel}
          </span>
          {profile?.behavior_tags?.map((tag) => (
            <span
              key={tag}
              className="px-2 py-1 bg-blue-50 text-blue-600 rounded-md text-[10px] font-medium uppercase tracking-wider"
            >
              {tag === 'chasing_rise' ? '盲目跟风'
                : tag === 'panic_sell' ? '过度焦虑'
                : tag === 'frequent_trading' ? '分期依赖'
                : tag === 'disciplined' ? '预算纪律稳定'
                : tag}
            </span>
          ))}
        </div>
      </div>

      {/* 风险提示 */}
      <div className="bg-amber-50 border border-amber-100 rounded-xl p-3 flex gap-3 items-start">
        <Info size={16} className="text-amber-500 shrink-0 mt-0.5" />
        <p className="text-xs text-amber-800 leading-relaxed">
          系统提供的是校园金融素养教育和结构化辅助判断，不做购买推荐、借贷诱导或投资推荐。
        </p>
      </div>

      {/* 菜单列表 */}
      <div className="bg-white rounded-2xl border border-stone-100 divide-y divide-stone-100 overflow-hidden">
        <Link
          to="/profile"
          className="flex items-center justify-between p-4 hover:bg-stone-50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <Settings size={20} className="text-stone-400" />
            <span className="font-medium text-sm">学生财务画像配置</span>
          </div>
          <ChevronRight size={18} className="text-stone-300" />
        </Link>

        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-between p-4 hover:bg-red-50 transition-colors text-left"
        >
          <div className="flex items-center gap-3">
            <LogOut size={20} className="text-red-400" />
            <span className="font-medium text-sm text-red-500">退出登录</span>
          </div>
        </button>
      </div>

      {/* 版本信息 */}
      <div className="text-center">
        <div className="text-[10px] text-stone-300 uppercase tracking-widest">
          AI 金融素养教练 v1.0.0 · 比赛 Demo
        </div>
      </div>
    </div>
  );
}
