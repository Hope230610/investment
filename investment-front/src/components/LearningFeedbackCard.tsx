import React, { useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { CheckCircle2, TrendingUp, TrendingDown, Minus, Lightbulb, Tag, BarChart3, Activity } from 'lucide-react';

import { cn } from '../utils';


// ─── Types ────────────────────────────────────────────────────────────────────

export type JudgmentQualityLevel = 'high' | 'medium' | 'low';

export interface JudgmentBreakdown {
  mainlyJudgment: number;   // 0-100, "主要来自判断"
  partialJudgment: number;  // 0-100, "部分判断+运气"
  mainlyLuck: number;       // 0-100, "主要来自运气"
  hardToTell: number;       // 0-100, "难以区分"
}

export interface EmotionDataPoint {
  date: string;
  level: number; // 1-5
}

export interface TagUpdate {
  tag: string;
  type: 'add' | 'remove' | 'upgrade';
  source: string;
}

export interface JudgmentTrend {
  direction: 'up' | 'down' | 'stable';
  description: string;
}

export interface LearningFeedbackData {
  tagUpdates: TagUpdate[];
  judgmentQualityPercent: number;
  judgmentQualityDelta: number;
  judgmentLevel: JudgmentQualityLevel;
  judgmentBreakdown: JudgmentBreakdown;
  judgmentTrend: JudgmentTrend;
  suggestion: string;
  emotionHistory: EmotionDataPoint[];
  currentEmotionLevel: number;
}

// ─── Color System ─────────────────────────────────────────────────────────────

const levelColors: Record<JudgmentQualityLevel, { bg: string; text: string; border: string; dot: string; label: string }> = {
  high: {
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
    dot: 'bg-emerald-500',
    label: '判断非常稳健，风险控制良好',
  },
  medium: {
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    border: 'border-amber-200',
    dot: 'bg-amber-500',
    label: '判断基本可靠，存在一定情绪干扰',
  },
  low: {
    bg: 'bg-red-50',
    text: 'text-red-700',
    border: 'border-red-200',
    dot: 'bg-red-500',
    label: '判断受运气影响较大，建议减少交易频率',
  },
};


// ─── Sparkline ────────────────────────────────────────────────────────────────

interface EmotionSparklineProps {
  data: EmotionDataPoint[];
  currentLevel: number;
  mean: number;
}

function EmotionSparkline({ data, currentLevel, mean }: EmotionSparklineProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  if (data.length < 2) {
    return (
      <div className="h-12 flex items-center justify-center text-xs text-stone-400">
        数据不足，无法绘制趋势
      </div>
    );
  }

  const levels = data.map(d => d.level);
  const minLvl = Math.min(...levels, 1);
  const maxLvl = Math.max(...levels, 5);

  const W = 240, H = 44, PAD = 2;
  const xStep = (W - PAD * 2) / Math.max(data.length - 1, 1);

  const toX = (i: number) => PAD + i * xStep;
  const toY = (v: number) => PAD + ((maxLvl - v) / Math.max(maxLvl - minLvl, 1)) * (H - PAD * 2);

  const points = data.map((d, i) => `${toX(i)},${toY(d.level)}`);
  const polyline = points.join(' ');

  const lastX = toX(data.length - 1);
  const lastY = toY(data[data.length - 1].level);
  const currentX = W / 2;
  const currentY = toY(currentLevel);

  // Mean line
  const meanY = toY(mean);

  const isAboveMean = currentLevel > mean;
  const warnIcon = isAboveMean ? '↑' : '↓';
  const warnLabel = isAboveMean ? '略高于均值' : '低于均值';
  const warnColor = isAboveMean ? 'text-amber-600' : 'text-emerald-600';

  return (
    <div className="space-y-2">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-11"
        aria-label="情绪趋势图"
      >
        {/* Mean line */}
        <line
          x1={PAD}
          y1={meanY}
          x2={W - PAD}
          y2={meanY}
          stroke="#d6d3d1"
          strokeWidth={1}
          strokeDasharray="3 3"
        />
        {/* Area fill */}
        <defs>
          <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.2} />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <polygon
          points={`${PAD},${H - PAD} ${polyline} ${W - PAD},${H - PAD}`}
          fill="url(#sparkGrad)"
        />
        {/* Line */}
        <polyline
          points={polyline}
          fill="none"
          stroke="#3b82f6"
          strokeWidth={1.5}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {/* Current point */}
        <circle
          cx={lastX}
          cy={lastY}
          r={3.5}
          fill="#3b82f6"
          stroke="white"
          strokeWidth={1.5}
        />
        {/* "本次" label */}
        <text
          x={lastX}
          y={lastY - 6}
          textAnchor="middle"
          fontSize={8}
          fill="#3b82f6"
          fontWeight="600"
        >
          本次
        </text>
      </svg>
      <div className="flex items-center justify-between text-xs">
        <span className="text-stone-400">
          均值 <span className="font-mono font-semibold text-stone-600">{mean.toFixed(1)}</span>
        </span>
        <span className="text-stone-400">
          本次 <span className="font-mono font-semibold text-stone-800">{currentLevel}</span>
        </span>
        <span className={cn('font-medium', warnColor)}>
          {warnIcon} {warnLabel}
        </span>
      </div>
    </div>
  );
}


// ─── Judgment Bar ─────────────────────────────────────────────────────────────

interface JudgmentBarProps {
  label: string;
  value: number;
  maxValue: number;
  color: string;
}

function JudgmentBar({ label, value, maxValue, color }: JudgmentBarProps) {
  const pct = maxValue > 0 ? (value / maxValue) * 100 : 0;
  return (
    <div className="flex items-center gap-3 text-xs">
      <div className="w-24 text-stone-500 shrink-0 text-right pr-1">{label}</div>
      <div className="flex-1 bg-stone-100 rounded-full h-2 overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all', color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="w-8 text-right font-mono font-semibold text-stone-700 shrink-0">{value}%</div>
    </div>
  );
}


// ─── Trend Indicator ───────────────────────────────────────────────────────────

function TrendBadge({ trend }: { trend: JudgmentTrend }) {
  const icons = {
    up: <TrendingUp size={12} />,
    down: <TrendingDown size={12} />,
    stable: <Minus size={12} />,
  };
  const colors = {
    up: 'text-emerald-600 bg-emerald-50',
    down: 'text-red-600 bg-red-50',
    stable: 'text-stone-500 bg-stone-100',
  };
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold', colors[trend.direction])}>
      {icons[trend.direction]} {trend.description}
    </span>
  );
}


// ─── Tag Update Row ────────────────────────────────────────────────────────────

const tagColors: Record<TagUpdate['type'], { bg: string; text: string; icon: string }> = {
  add: { bg: 'bg-emerald-50', text: 'text-emerald-700', icon: '+' },
  remove: { bg: 'bg-stone-100', text: 'text-stone-500', icon: '−' },
  upgrade: { bg: 'bg-blue-50', text: 'text-blue-700', icon: '↑' },
};

function TagUpdateRow({ update, index }: { update: TagUpdate; index: number }) {
  const colors = tagColors[update.type];
  const prefix = update.type === 'add' ? '新增' : update.type === 'remove' ? '移除' : '升级';
  return (
    <div className={cn('flex items-start gap-2 p-3 rounded-xl', colors.bg)}>
      <span className={cn('font-mono font-bold text-base leading-none mt-[-2px]', colors.text)}>
        {colors.icon}
      </span>
      <div className="flex-1">
        <div className="text-xs font-semibold text-stone-800">
          {prefix}「{update.tag}」
        </div>
        <div className="text-[10px] text-stone-400 mt-0.5">{update.source}</div>
      </div>
    </div>
  );
}


// ─── Main Component ────────────────────────────────────────────────────────────

interface LearningFeedbackCardProps {
  visible: boolean;
  data: LearningFeedbackData | null;
  onConfirm: () => void;
  onDismiss: () => void;
  loading?: boolean;
}

export default function LearningFeedbackCard({
  visible,
  data,
  onConfirm,
  onDismiss,
  loading = false,
}: LearningFeedbackCardProps) {
  const levelConf = data ? levelColors[data.judgmentLevel] : levelColors.medium;

  return (
    <AnimatePresence>
      {visible && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onDismiss}
            className="fixed inset-0 bg-black/40 z-50 backdrop-blur-sm"
            aria-hidden="true"
          />

          {/* Sheet */}
          <motion.div
            key="sheet"
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-md bg-white rounded-t-[28px] z-50 safe-bottom"
            role="dialog"
            aria-modal="true"
            aria-label="学习反馈"
          >
            {/* Drag handle */}
            <div className="flex justify-center pt-3 pb-2" aria-hidden="true">
              <div className="w-9 h-1 bg-stone-200 rounded-full" />
            </div>

            {/* Header */}
            <div className="px-6 pb-4 flex items-center gap-3 border-b border-stone-100">
              <div className="w-9 h-9 bg-ink rounded-xl flex items-center justify-center shrink-0">
                <Activity size={18} className="text-white" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-stone-900">本次复盘 · 系统学到了这些</h2>
                <p className="text-xs text-stone-400">基于你的复盘内容更新了画像</p>
              </div>
            </div>

            {/* Content */}
            <div className="px-6 py-5 space-y-5 max-h-[65vh] overflow-y-auto">

              {/* 行为标签 */}
              {data && data.tagUpdates.length > 0 && (
                <section className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Tag size={14} className="text-stone-400" />
                    <h3 className="text-xs font-bold text-stone-400 uppercase tracking-widest">行为标签更新</h3>
                  </div>
                  <div className="space-y-2">
                    {data.tagUpdates.map((update, i) => (
                      <React.Fragment key={i}>
                        <TagUpdateRow update={update} index={i} />
                      </React.Fragment>
                    ))}
                  </div>
                </section>
              )}

              {/* 判断质量 */}
              {data && (
                <section className={cn('rounded-2xl border p-4 space-y-4', levelConf.bg, levelConf.border)}>
                  <div className="flex items-center gap-2">
                    <BarChart3 size={14} className="text-stone-400" />
                    <h3 className="text-xs font-bold text-stone-400 uppercase tracking-widest">判断质量</h3>
                  </div>

                  {/* 主指标行 */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold font-mono text-stone-900">
                        {data.judgmentQualityPercent}%
                      </span>
                      {data.judgmentQualityDelta !== 0 && (
                        <span className={cn(
                          'text-sm font-semibold',
                          data.judgmentQualityDelta > 0 ? 'text-emerald-600' : 'text-red-600'
                        )}>
                          {data.judgmentQualityDelta > 0 ? '+' : ''}{data.judgmentQualityDelta}%
                        </span>
                      )}
                      {/* Level dot */}
                      <span className={cn('w-2.5 h-2.5 rounded-full inline-block', levelConf.dot)} />
                    </div>
                    <TrendBadge trend={data.judgmentTrend} />
                  </div>

                  {/* 评价文字 */}
                  <div className={cn('text-xs px-3 py-2 rounded-lg', levelConf.bg)}>
                    <span className="font-semibold">{levelConf.label}</span>
                  </div>

                  {/* 构成分析 */}
                  <div className="space-y-2.5 pt-1 border-t border-stone-100/60">
                    <div className="text-[10px] font-bold text-stone-400 uppercase tracking-widest">构成分析</div>
                    {(() => {
                      const b = data.judgmentBreakdown;
                      const max = Math.max(b.mainlyJudgment, b.partialJudgment, b.mainlyLuck, b.hardToTell);
                      return (
                        <>
                          <JudgmentBar label="主要来自判断" value={b.mainlyJudgment} maxValue={max} color="bg-blue-500" />
                          <JudgmentBar label="部分判断+运气" value={b.partialJudgment} maxValue={max} color="bg-amber-400" />
                          <JudgmentBar label="主要来自运气" value={b.mainlyLuck} maxValue={max} color="bg-red-400" />
                          <JudgmentBar label="难以区分" value={b.hardToTell} maxValue={max} color="bg-stone-300" />
                        </>
                      );
                    })()}
                  </div>
                </section>
              )}

              {/* 情绪趋势 */}
              {data && data.emotionHistory.length > 0 && (
                <section className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Activity size={14} className="text-stone-400" />
                    <h3 className="text-xs font-bold text-stone-400 uppercase tracking-widest">
                      情绪趋势（最近{data.emotionHistory.length}天）
                    </h3>
                  </div>
                  <div className="rounded-2xl border border-stone-100 p-4 bg-white">
                    <EmotionSparkline
                      data={data.emotionHistory}
                      currentLevel={data.currentEmotionLevel}
                      mean={data.emotionHistory.reduce((s, d) => s + d.level, 0) / data.emotionHistory.length}
                    />
                  </div>
                </section>
              )}

              {/* 建议 */}
              {data && data.suggestion && (
                <section className="bg-blue-50 border border-blue-100 rounded-2xl p-4">
                  <div className="flex items-start gap-2">
                    <Lightbulb size={16} className="text-blue-500 shrink-0 mt-0.5" />
                    <div>
                      <div className="text-[10px] font-bold text-blue-400 uppercase tracking-widest mb-1">建议</div>
                      <p className="text-xs text-blue-800 leading-relaxed">{data.suggestion}</p>
                    </div>
                  </div>
                </section>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 pb-6 pt-4 flex gap-3 border-t border-stone-100 safe-bottom">
              <button
                onClick={onDismiss}
                disabled={loading}
                className="flex-1 py-3.5 bg-stone-100 text-stone-600 rounded-2xl font-bold text-sm hover:bg-stone-200 transition-colors disabled:opacity-40"
              >
                忽略
              </button>
              <button
                onClick={onConfirm}
                disabled={loading}
                className="flex-[2] py-3.5 bg-ink text-white rounded-2xl font-bold text-sm hover:bg-stone-800 transition-colors disabled:opacity-40 flex items-center justify-center gap-2 active:scale-[0.98]"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    保存中...
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={16} />
                    确认
                  </>
                )}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
