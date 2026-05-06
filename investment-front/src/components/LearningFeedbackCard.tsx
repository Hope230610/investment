import React, { useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import {
  CheckCircle2,
  Clock,
  Lightbulb,
  Tag,
  BarChart3,
  Activity,
  TrendingUp,
  TrendingDown,
  Minus,
  X,
} from 'lucide-react';

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
  insufficient?: boolean;
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
  /** 本次选择了"难以区分"，判断质量数据不足，不计入历史聚合 */
  isHardToTell?: boolean;
}

// ─── Color System ─────────────────────────────────────────────────────────────

const levelColors: Record<JudgmentQualityLevel, { bg: string; text: string; border: string; dot: string; label: string }> = {
  high: {
    bg: 'bg-mist',
    text: 'text-teal-700',
    border: 'border-teal-100',
    dot: 'bg-teal-600',
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
    bg: 'bg-rose-50',
    text: 'text-rose-700',
    border: 'border-rose-100',
    dot: 'bg-rose-500',
    label: '判断受情绪影响较大，建议减少大额分期和冲动消费频率',
  },
};


// ─── Sparkline ────────────────────────────────────────────────────────────────

export interface EmotionDataPoint {
  date: string;
  level: number; // 1-5
}

interface EmotionSparklineProps {
  data: EmotionDataPoint[];
  currentLevel: number;
  mean: number;
}

export function EmotionSparkline({ data, currentLevel, mean }: EmotionSparklineProps) {
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
  const warnColor = isAboveMean ? 'text-amber-600' : 'text-teal-700';

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
            <stop offset="0%" stopColor="#0f766e" stopOpacity={0.18} />
            <stop offset="100%" stopColor="#0f766e" stopOpacity={0.02} />
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
          stroke="#0f766e"
          strokeWidth={1.5}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {/* Current point */}
        <circle
          cx={lastX}
          cy={lastY}
          r={3.5}
          fill="#0f766e"
          stroke="white"
          strokeWidth={1.5}
        />
        {/* "本次" label */}
        <text
          x={lastX}
          y={lastY - 6}
          textAnchor="middle"
          fontSize={8}
          fill="#0f766e"
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
    up: 'text-teal-700 bg-mist',
    down: 'text-rose-700 bg-rose-50',
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
  add: { bg: 'bg-mist', text: 'text-teal-700', icon: '+' },
  remove: { bg: 'bg-stone-100', text: 'text-stone-500', icon: '−' },
  upgrade: { bg: 'bg-amber-50', text: 'text-amber-700', icon: '↑' },
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
  onLater: () => void;
  onDismiss: () => void;
  loading?: boolean;
  showCount?: number;
}

export default function LearningFeedbackCard({
  visible,
  data,
  onConfirm,
  onLater,
  onDismiss,
  loading = false,
  showCount = 0,
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
            className="safe-bottom fixed bottom-0 left-1/2 z-50 w-full max-w-lg -translate-x-1/2 rounded-t-[28px] bg-white"
            role="dialog"
            aria-modal="true"
            aria-label="学习反馈"
          >
            {/* Drag handle */}
            <div className="flex justify-center pt-3 pb-2" aria-hidden="true">
              <div className="w-9 h-1 bg-stone-200 rounded-full" />
            </div>

            {/* Header */}
            <div className="flex items-start gap-3 border-b border-stone-100 px-6 pb-4">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-teal-700">
                <Activity size={18} className="text-white" />
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-base font-bold leading-snug text-stone-900">本次复盘 · 系统学到了这些</h2>
                  {showCount > 0 && (
                    <span className="px-1.5 py-0.5 bg-amber-50 border border-amber-200 rounded-full text-[10px] font-bold text-amber-600">
                      第{showCount + 1}次展示
                    </span>
                  )}
                </div>
                <p className="text-xs text-stone-400">基于你的复盘内容更新了画像 · 行为标签需确认后才写入</p>
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
                <section className={cn(
                  'rounded-2xl border p-4 space-y-4',
                  data.isHardToTell
                    ? 'bg-stone-50 border-stone-200'
                    : cn(levelConf.bg, levelConf.border)
                )}>
                  <div className="flex items-center gap-2">
                    <BarChart3 size={14} className="text-stone-400" />
                    <h3 className="text-xs font-bold text-stone-400 uppercase tracking-widest">判断质量</h3>
                  </div>

                  {data.isHardToTell ? (
                    /* 难以区分：显示说明文字 + breakdown，不展示百分比 */
                    <>
                      <div className="flex items-start gap-2 py-1">
                        <span className="text-3xl font-bold font-mono text-stone-300">—</span>
                        <div className="space-y-1">
                          <p className="text-sm font-semibold text-stone-500">本次选择了「难以区分」</p>
                          <p className="text-xs text-stone-400 leading-relaxed">
                            本次复盘暂不计入判断质量统计，保持复盘习惯，数据积累后将纳入分析
                          </p>
                        </div>
                      </div>

                      {/* 构成分析 */}
                      <div className="space-y-2.5 pt-1 border-t border-stone-200/60">
                        <div className="text-[10px] font-bold text-stone-400 uppercase tracking-widest">构成分析</div>
                        {(() => {
                          const b = data.judgmentBreakdown;
                          return (
                            <JudgmentBar label="难以区分" value={b.hardToTell} maxValue={100} color="bg-stone-300" />
                          );
                        })()}
                      </div>
                    </>
                  ) : (
                    /* 正常情况：展示百分比 + delta + breakdown */
                    <>
                      {/* 主指标行 */}
                      <div className="flex items-baseline justify-between">
                        <div className="flex items-baseline gap-2">
                          <span className="text-3xl font-bold font-mono text-stone-900">
                            {data.judgmentQualityPercent}%
                          </span>
                          {data.judgmentQualityDelta !== 0 && !data.judgmentTrend.insufficient && (
                            <span className={cn(
                              'text-sm font-semibold',
                              data.judgmentQualityDelta > 0 ? 'text-teal-700' : 'text-rose-700'
                            )}>
                              {data.judgmentQualityDelta > 0 ? '+' : ''}{data.judgmentQualityDelta}%
                            </span>
                          )}
                          {/* Level dot */}
                          <span className={cn('w-2.5 h-2.5 rounded-full inline-block', levelConf.dot)} />
                        </div>
                        {!data.judgmentTrend.insufficient && <TrendBadge trend={data.judgmentTrend} />}
                        {data.judgmentTrend.insufficient && (
                          <span className="text-xs text-stone-400 italic">数据积累中</span>
                        )}
                      </div>

                      {/* 评价文字 */}
                      <div className={cn('text-xs px-3 py-2 rounded-lg', levelConf.bg)}>
                        <span className="font-semibold">{levelConf.label}</span>
                      </div>

                      {/* 构成分析 */}
                      <div className="space-y-2.5 pt-1 border-t border-stone-100/60">
                        <div className="text-[10px] font-bold text-stone-400 uppercase tracking-widest">
                          构成分析{data.judgmentTrend.insufficient ? ' · 初始记录' : ''}
                        </div>
                        {(() => {
                          const b = data.judgmentBreakdown;
                          const max = Math.max(b.mainlyJudgment, b.partialJudgment, b.mainlyLuck, b.hardToTell);
                          return (
                            <>
                              <JudgmentBar label="主要来自判断" value={b.mainlyJudgment} maxValue={max} color="bg-teal-600" />
                              <JudgmentBar label="部分判断+运气" value={b.partialJudgment} maxValue={max} color="bg-amber-400" />
                              <JudgmentBar label="主要来自运气" value={b.mainlyLuck} maxValue={max} color="bg-rose-400" />
                              <JudgmentBar label="难以区分" value={b.hardToTell} maxValue={max} color="bg-stone-300" />
                            </>
                          );
                        })()}
                      </div>
                    </>
                  )}
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
                <section className="rounded-2xl border border-teal-100 bg-mist p-4">
                  <div className="flex items-start gap-2">
                    <Lightbulb size={16} className="mt-0.5 shrink-0 text-teal-700" />
                    <div>
                      <div className="mb-1 text-[10px] font-bold uppercase tracking-widest text-teal-700">建议</div>
                      <p className="text-xs leading-relaxed text-teal-950">{data.suggestion}</p>
                    </div>
                  </div>
                </section>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 pb-6 pt-4 space-y-3 border-t border-stone-100 safe-bottom">
              {/* Three buttons */}
              <div className="flex gap-2">
                {/* Dismiss — 永久跳过，不再出现 */}
                <button
                  onClick={onDismiss}
                  disabled={loading}
                  className="px-3 py-3 bg-stone-100 text-stone-500 rounded-2xl font-bold text-xs hover:bg-stone-200 transition-colors disabled:opacity-40 flex items-center gap-1.5"
                  title="本次跳过，不会再出现"
                >
                  <X size={13} />
                  忽略
                </button>

                {/* Later — 下次复盘再提醒 */}
                <button
                  onClick={onLater}
                  disabled={loading}
                  className="px-3 py-3 bg-amber-50 text-amber-700 rounded-2xl font-bold text-xs hover:bg-amber-100 transition-colors disabled:opacity-40 flex items-center gap-1.5 flex-1 justify-center"
                  title={showCount >= 2 ? '已展示过多次，下次不一定再出现' : '下次复盘时再提醒'}
                >
                  <Clock size={13} />
                  稍后
                  {showCount > 0 && (
                    <span className="text-[10px] text-amber-400 font-mono">({showCount}/3)</span>
                  )}
                </button>

                {/* Confirm — 确认写入 */}
                <button
                  onClick={onConfirm}
                  disabled={loading}
                  className="flex-[2] py-3 bg-teal-700 text-white rounded-2xl font-bold text-sm hover:bg-teal-800 transition-colors disabled:opacity-40 flex items-center justify-center gap-2 active:scale-[0.98]"
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

              {/* Hint text */}
              <p className="text-center text-[10px] text-stone-400 leading-relaxed">
                <span className="font-semibold text-stone-500">忽略</span>
                {' '}跳过本次，不更新画像 ·
                <span className="font-semibold text-amber-600">稍后</span>
                {' '}下次复盘时再提醒（最多3次） ·
                <span className="font-semibold text-stone-700">确认</span>
                {' '}写入画像
              </p>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
