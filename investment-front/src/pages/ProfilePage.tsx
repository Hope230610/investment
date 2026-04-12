import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, Info, TrendingUp, TrendingDown, Minus } from 'lucide-react';

import { apiGet, apiPut, getLearningHistory } from '../api';
import type { UserProfile } from '../types';
import { EmotionSparkline } from '../components/LearningFeedbackCard';
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


// ─── Learning History Section ─────────────────────────────────────────────────

const JUDGMENT_LABEL_COLORS: Record<string, string> = {
  '主要来自判断': 'text-emerald-600 bg-emerald-50 border-emerald-200',
  '部分判断 + 部分运气': 'text-amber-600 bg-amber-50 border-amber-200',
  '主要来自运气': 'text-red-600 bg-red-50 border-red-200',
  '难以区分': 'text-stone-500 bg-stone-100 border-stone-200',
};

function JudgmentTrendBar({ score }: { score: number }) {
  const color = score >= 80 ? 'bg-emerald-400' : score >= 60 ? 'bg-amber-400' : 'bg-red-400';
  return (
    <div className="w-full bg-stone-100 rounded-full h-2">
      <div className={cn('h-2 rounded-full transition-all', color)} style={{ width: `${score}%` }} />
    </div>
  );
}

function LearningHistorySection() {
  const [loading, setLoading] = useState(true);
  const [history, setHistory] = useState<{
    emotion_history: { date: string; level: number }[];
    judgment_history: { date: string; score: number; label: string; is_hard_to_tell: boolean }[];
  } | null>(null);

  useEffect(() => {
    getLearningHistory(30)
      .then(setHistory)
      .catch(() => setHistory(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <section className="bg-white rounded-2xl border border-stone-100 p-5 space-y-3">
        <div className="animate-pulse space-y-2">
          <div className="h-4 bg-stone-100 rounded w-32" />
          <div className="h-24 bg-stone-50 rounded-xl" />
        </div>
      </section>
    );
  }

  if (!history) {
    return null;
  }

  const emotionMean = history.emotion_history.length > 0
    ? history.emotion_history.reduce((s, d) => s + d.level, 0) / history.emotion_history.length
    : 0;

  const validJudgmentHistory = history.judgment_history.filter(h => !h.is_hard_to_tell);
  const avgScore = validJudgmentHistory.length > 0
    ? Math.round(validJudgmentHistory.reduce((s, h) => s + h.score, 0) / validJudgmentHistory.length)
    : 0;

  return (
    <section className="bg-white rounded-2xl border border-stone-100 p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <TrendingUp size={16} className="text-blue-500" />
        <h3 className="text-sm font-bold text-stone-700">学习记录</h3>
        {validJudgmentHistory.length > 0 && (
          <span className="ml-auto text-xs text-stone-400">
            共 {validJudgmentHistory.length} 条记录
          </span>
        )}
      </div>

      {/* 情绪趋势 */}
      {history.emotion_history.length > 0 ? (
        <div className="space-y-2">
          <div className="text-[10px] font-bold text-stone-400 uppercase tracking-widest">情绪趋势（最近30天）</div>
          <div className="bg-stone-50 rounded-xl p-3">
            <EmotionSparkline
              data={history.emotion_history}
              currentLevel={history.emotion_history[history.emotion_history.length - 1]?.level ?? 3}
              mean={emotionMean}
            />
          </div>
        </div>
      ) : (
        <div className="text-xs text-stone-400 text-center py-3">暂无情绪数据，开始复盘后将自动积累</div>
      )}

      {/* 判断质量趋势 */}
      {validJudgmentHistory.length > 0 ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-[10px] font-bold text-stone-400 uppercase tracking-widest">判断质量历史</div>
            <div className="text-xs text-stone-500">
              均值 <span className="font-bold font-mono">{avgScore}%</span>
            </div>
          </div>

          {/* 趋势概览条 */}
          <div className="bg-stone-50 rounded-xl p-3 space-y-1">
            <JudgmentTrendBar score={avgScore} />
            <div className="flex justify-between text-[10px] text-stone-400">
              <span>判断质量均值</span>
              <span className={avgScore >= 80 ? 'text-emerald-600' : avgScore >= 60 ? 'text-amber-600' : 'text-red-600'}>
                {avgScore >= 80 ? '稳健' : avgScore >= 60 ? '一般' : '待提升'}
              </span>
            </div>
          </div>

          {/* 逐条记录（最新5条） */}
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {[...validJudgmentHistory].reverse().slice(0, 5).map((entry, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="w-20 shrink-0 text-[10px] text-stone-400 font-mono">
                  {entry.date}
                </div>
                <div className="flex-1 bg-stone-50 rounded-full h-1.5 overflow-hidden">
                  <div
                    className={cn('h-full rounded-full', entry.score >= 80 ? 'bg-emerald-400' : entry.score >= 60 ? 'bg-amber-400' : 'bg-red-400')}
                    style={{ width: `${entry.score}%` }}
                  />
                </div>
                <div className={cn(
                  'px-2 py-0.5 rounded-full text-[9px] font-bold border',
                  JUDGMENT_LABEL_COLORS[entry.label] || JUDGMENT_LABEL_COLORS['难以区分']
                )}>
                  {entry.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="text-xs text-stone-400 text-center py-3">暂无判断质量记录，每次复盘后将自动积累</div>
      )}
    </section>
  );
}


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
    navigate('/me');
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

      {/* ── 学习记录区块 ──────────────────────────────────────── */}
      <LearningHistorySection />

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
