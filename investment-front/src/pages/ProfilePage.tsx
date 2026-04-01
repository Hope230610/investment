import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, Info } from 'lucide-react';

import { apiGet, apiPut } from '../api';
import type { UserProfile } from '../types';
import {
  BEHAVIOR_TAGS,
  cn,
  EXPERIENCE_LEVELS,
  HOLDING_HORIZONS,
  RISK_TOLERANCES,
} from '../utils';


const defaultProfile: UserProfile = {
  experience_level: 'intermediate',
  holding_horizon: 'medium',
  risk_tolerance: 'medium',
  behavior_tags: [],
};


export default function ProfilePage() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<UserProfile>(defaultProfile);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const loadProfile = async () => {
      try {
        const data = await apiGet<UserProfile>('/api/v1/user/profile');
        if (!cancelled) {
          setProfile({
            ...defaultProfile,
            ...data,
            behavior_tags: data.behavior_tags || [],
          });
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadProfile().catch(() => {
      if (!cancelled) {
        setLoading(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleSave = async () => {
    await apiPut<UserProfile>('/api/v1/user/profile', profile);
    navigate(-1);
  };

  if (loading) return <div className="p-8 text-center text-stone-400">加载中...</div>;

  return (
    <div className="p-4 space-y-8">
      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">用户画像配置</h2>
        <div className="bg-blue-50 p-3 rounded-xl flex gap-2 items-start">
          <Info size={16} className="text-blue-500 shrink-0 mt-0.5" />
          <p className="text-xs text-blue-700 leading-relaxed">
            用户画像只用于调整解释方式、风险提示和下一步建议，不会改写股票本身的事实判断。
          </p>
        </div>
      </div>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">投资经验</label>
        <div className="grid grid-cols-1 gap-2">
          {EXPERIENCE_LEVELS.map((option) => (
            <button
              key={option.value}
              onClick={() => setProfile({ ...profile, experience_level: option.value as UserProfile['experience_level'] })}
              className={cn(
                'p-4 rounded-2xl border text-left transition-all flex justify-between items-center',
                profile.experience_level === option.value
                  ? 'border-ink bg-ink text-white'
                  : 'border-stone-200 bg-white text-stone-600'
              )}
            >
              <span className="font-medium">{option.label}</span>
              {profile.experience_level === option.value && <Check size={18} />}
            </button>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">持有周期</label>
        <div className="flex bg-stone-100 p-1 rounded-xl">
          {HOLDING_HORIZONS.map((option) => (
            <button
              key={option.value}
              onClick={() => setProfile({ ...profile, holding_horizon: option.value as UserProfile['holding_horizon'] })}
              className={cn(
                'flex-1 py-2 text-xs font-bold rounded-lg transition-all',
                profile.holding_horizon === option.value ? 'bg-white text-ink shadow-sm' : 'text-stone-400'
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">风险承受能力</label>
        <div className="grid grid-cols-3 gap-2">
          {RISK_TOLERANCES.map((option) => (
            <button
              key={option.value}
              onClick={() => setProfile({ ...profile, risk_tolerance: option.value as UserProfile['risk_tolerance'] })}
              className={cn(
                'py-3 rounded-xl border font-bold text-xs transition-all',
                profile.risk_tolerance === option.value
                  ? 'border-ink bg-ink text-white'
                  : 'border-stone-200 bg-white text-stone-400'
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">行为标签</label>
        <div className="flex flex-wrap gap-2">
          {BEHAVIOR_TAGS.map((option) => {
            const isSelected = profile.behavior_tags.includes(option.value as UserProfile['behavior_tags'][number]);
            return (
              <button
                key={option.value}
                onClick={() => {
                  const newTags = isSelected
                    ? profile.behavior_tags.filter((tag) => tag !== option.value)
                    : [...profile.behavior_tags, option.value as UserProfile['behavior_tags'][number]];
                  setProfile({ ...profile, behavior_tags: newTags });
                }}
                className={cn(
                  'px-4 py-2 rounded-full border text-xs font-medium transition-all',
                  isSelected
                    ? 'border-blue-600 bg-blue-600 text-white'
                    : 'border-stone-200 bg-white text-stone-500'
                )}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </section>

      <div className="pt-4">
        <button
          onClick={handleSave}
          className="w-full py-4 bg-ink text-white rounded-2xl font-bold text-lg active:scale-[0.98] transition-transform"
        >
          保存画像
        </button>
      </div>
    </div>
  );
}
