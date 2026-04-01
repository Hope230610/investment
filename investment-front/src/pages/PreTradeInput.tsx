import React, { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AlertTriangle, CheckCircle2, ChevronRight, Search } from 'lucide-react';
import { motion } from 'motion/react';

import { apiPost } from '../api';
import { cn } from '../utils';


type Intent = 'buy' | 'sell' | 'add' | 'reduce';


const triggers = ['连续上涨', '热点消息', '快速下跌', '技术面突破', '财报预期', '其他'];


export default function PreTradeInput() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const stockId = searchParams.get('stock_id') || '';
  const stockName = searchParams.get('stock_name') || '';

  const [intent, setIntent] = useState<Intent | null>(null);
  const [trigger, setTrigger] = useState('');
  const [emotion, setEmotion] = useState(3);
  const [answers, setAnswers] = useState<Record<string, boolean>>({});
  const [showSelfCheck, setShowSelfCheck] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selfCheckQuestions = useMemo(() => {
    const baseQuestions = [
      { id: 'q1', text: '我是否写清了这次操作成立的前提？' },
      { id: 'q2', text: '我是否写清了仓位边界和失效条件？' },
    ];

    if (intent === 'buy' || intent === 'add') {
      baseQuestions.push({ id: 'q3', text: '我买入不是因为害怕错过，而是因为有新的事实支撑吗？' });
    } else if (intent === 'sell' || intent === 'reduce') {
      baseQuestions.push({ id: 'q3', text: '我卖出不是因为短期恐慌，而是原有逻辑真的发生变化吗？' });
    }

    if (trigger === '连续上涨') {
      baseQuestions.push({ id: 'q4', text: '如果明天回撤，我还能接受这次决定吗？' });
    } else if (trigger === '快速下跌') {
      baseQuestions.push({ id: 'q4', text: '这次下跌影响的是情绪，还是公司本身？' });
    }

    return baseQuestions;
  }, [intent, trigger]);

  const allQuestionsAnswered = selfCheckQuestions.every((question) => answers[question.id] !== undefined);

  const handleSubmit = async () => {
    if (!stockId || !intent || !trigger || submitting) return;

    if (emotion > 3 && !showSelfCheck) {
      setShowSelfCheck(true);
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const data = await apiPost<{ id: number }>('/api/v1/analysis', {
        scenario: 'pre_trade_check',
        stock_id: stockId,
        scenario_payload: {
          intent,
          trigger_reason: trigger,
          emotion_level: emotion,
          self_check_answers: answers,
          show_self_check: showSelfCheck,
        },
      });
      navigate(`/analysis/${data.id}/result`);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : '创建分析失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-4 space-y-8 pb-32">
      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">交易前自检</h2>
        <p className="text-sm text-stone-400">在采取动作前，先确认这次决定是基于事实，而不是被情绪推着走。</p>
      </div>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">选择股票</label>
        <button
          onClick={() => navigate('/stock/search?callback=/analysis/pre-trade')}
          className="w-full p-4 bg-white border border-stone-200 rounded-2xl flex items-center justify-between"
        >
          {stockId ? (
            <div className="text-left">
              <div className="font-bold text-lg">{stockName}</div>
              <div className="text-xs text-stone-400 font-mono">{stockId}</div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-stone-400">
              <Search size={18} />
              <span className="text-sm">点击搜索 A 股标的</span>
            </div>
          )}
          <ChevronRight size={18} className="text-stone-300" />
        </button>
      </section>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">当前意图</label>
        <div className="grid grid-cols-2 gap-2">
          {[
            { value: 'buy', label: '买入', active: 'text-red-600 border-red-100 bg-red-50' },
            { value: 'add', label: '加仓', active: 'text-red-600 border-red-100 bg-red-50' },
            { value: 'sell', label: '卖出', active: 'text-emerald-600 border-emerald-100 bg-emerald-50' },
            { value: 'reduce', label: '减仓', active: 'text-emerald-600 border-emerald-100 bg-emerald-50' },
          ].map((option) => (
            <button
              key={option.value}
              onClick={() => setIntent(option.value as Intent)}
              className={cn(
                'py-3 rounded-xl border font-bold text-sm transition-all',
                intent === option.value ? option.active : 'border-stone-200 bg-white text-stone-400'
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">触发原因</label>
        <div className="flex flex-wrap gap-2">
          {triggers.map((item) => (
            <button
              key={item}
              onClick={() => setTrigger(item)}
              className={cn(
                'px-4 py-2 rounded-full border text-xs font-medium transition-all',
                trigger === item ? 'border-ink bg-ink text-white' : 'border-stone-200 bg-white text-stone-500'
              )}
            >
              {item}
            </button>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-bold uppercase tracking-widest text-stone-400">当前情绪</label>
          <span className="text-xs font-bold text-stone-600">
            {emotion <= 2 ? '比较冷静' : emotion === 3 ? '有些波动' : '明显冲动'}
          </span>
        </div>
        <input
          type="range"
          min="1"
          max="5"
          step="1"
          className="w-full accent-ink"
          value={emotion}
          onChange={(event) => setEmotion(parseInt(event.target.value, 10))}
        />
        <div className="flex justify-between text-[10px] text-stone-300 font-bold uppercase tracking-tighter">
          <span>冷静</span>
          <span>中性</span>
          <span>冲动</span>
        </div>
      </section>

      {(trigger === '连续上涨' || trigger === '快速下跌') && (
        <div
          className={cn(
            'p-4 rounded-2xl border flex gap-3 items-start',
            trigger === '连续上涨' ? 'bg-red-50 border-red-100' : 'bg-blue-50 border-blue-100'
          )}
        >
          <AlertTriangle
            size={18}
            className={cn('shrink-0 mt-0.5', trigger === '连续上涨' ? 'text-red-500' : 'text-blue-500')}
          />
          <p
            className={cn(
              'text-xs leading-relaxed font-medium',
              trigger === '连续上涨' ? 'text-red-800' : 'text-blue-800'
            )}
          >
            {trigger === '连续上涨'
              ? '系统识别到你可能处在追涨触发下，建议把交易理由补完整，再看是否仍然值得执行。'
              : '系统识别到你可能处在下跌压力触发下，建议先确认逻辑变化，再决定是否动作。'}
          </p>
        </div>
      )}

      {showSelfCheck && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-3xl p-6 border border-stone-100 shadow-sm space-y-4"
        >
          <div className="flex items-center gap-2">
            <CheckCircle2 size={20} className="text-emerald-500" />
            <h3 className="font-bold text-lg">交易前自检</h3>
          </div>
          <p className="text-xs text-stone-400">
            这一步不是为了拖慢你，而是避免把情绪误当成确定性。
          </p>
          <div className="space-y-4">
            {selfCheckQuestions.map((question, index) => (
              <div key={question.id} className="space-y-2">
                <div className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-stone-100 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">
                    {index + 1}
                  </div>
                  <p className="text-sm text-stone-700">{question.text}</p>
                </div>
                <div className="flex gap-3 ml-8">
                  <button
                    onClick={() => setAnswers((prev) => ({ ...prev, [question.id]: true }))}
                    className={cn(
                      'flex-1 py-2 rounded-lg text-xs font-medium transition-all',
                      answers[question.id] === true
                        ? 'bg-emerald-100 text-emerald-700 border border-emerald-200'
                        : 'bg-stone-50 text-stone-600 border border-stone-200 hover:bg-stone-100'
                    )}
                  >
                    是
                  </button>
                  <button
                    onClick={() => setAnswers((prev) => ({ ...prev, [question.id]: false }))}
                    className={cn(
                      'flex-1 py-2 rounded-lg text-xs font-medium transition-all',
                      answers[question.id] === false
                        ? 'bg-red-100 text-red-700 border border-red-200'
                        : 'bg-stone-50 text-stone-600 border border-stone-200 hover:bg-stone-100'
                    )}
                  >
                    否
                  </button>
                </div>
              </div>
            ))}
          </div>
          <div className="text-xs text-stone-400">
            已回答 {Object.keys(answers).length}/{selfCheckQuestions.length} 个问题
          </div>
        </motion.div>
      )}

      {error && (
        <div className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="pt-4">
        {!showSelfCheck && emotion > 3 && stockId && intent && trigger ? (
          <div className="space-y-3">
            <div className="bg-amber-50 border border-amber-100 p-4 rounded-2xl flex gap-3 items-start">
              <AlertTriangle size={18} className="text-amber-500 shrink-0 mt-0.5" />
              <p className="text-xs text-amber-800 leading-relaxed">
                当前情绪评分偏高，建议先完成自检，再进入分析结果页。
              </p>
            </div>
            <button
              onClick={() => setShowSelfCheck(true)}
              className="w-full py-4 bg-amber-600 text-white rounded-2xl font-bold text-lg active:scale-[0.98] transition-all"
            >
              开始自检
            </button>
          </div>
        ) : (
          <button
            disabled={!stockId || !intent || !trigger || (showSelfCheck && !allQuestionsAnswered) || submitting}
            onClick={handleSubmit}
            className="w-full py-4 bg-ink text-white rounded-2xl font-bold text-lg active:scale-[0.98] transition-all disabled:opacity-30 disabled:scale-100"
          >
            {submitting ? '分析中...' : showSelfCheck ? '完成自检并生成分析' : '开始自检分析'}
          </button>
        )}
      </div>
    </div>
  );
}
