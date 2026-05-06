import React, { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AlertTriangle, CheckCircle2, ChevronRight, Search } from 'lucide-react';
import { motion } from 'motion/react';

import { apiPost } from '../api';
import { cn } from '../utils';


type Intent = 'purchase' | 'delay' | 'reduce_budget' | 'review';


const triggers = ['同学都换新机', '限时优惠', '学习需要', '旧设备损坏', '博主种草', '其他'];


export default function PreTradeInput() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const stockId = searchParams.get('stock_id') || 'SZ000200';
  const stockName = searchParams.get('stock_name') || '5999 元手机分期';

  const [intent, setIntent] = useState<Intent | null>('purchase');
  const [trigger, setTrigger] = useState('同学都换新机');
  const [emotion, setEmotion] = useState(5);
  const [monthlyAllowance, setMonthlyAllowance] = useState('2000');
  const [spentThisMonth, setSpentThisMonth] = useState('1500');
  const [itemPrice, setItemPrice] = useState('5999');
  const [installmentMonths, setInstallmentMonths] = useState('12');
  const [answers, setAnswers] = useState<Record<string, boolean>>({});
  const [showSelfCheck, setShowSelfCheck] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isCampusDemoObject = stockName.includes('手机') || stockName.includes('分期');

  const selfCheckQuestions = useMemo(() => {
    const baseQuestions = [
      { id: 'q1', text: '如果不能分期，我是否仍然愿意购买？' },
      { id: 'q2', text: '付完这笔钱后，我是否还能保留至少一个月生活费安全垫？' },
    ];

    if (intent === 'purchase') {
      baseQuestions.push({ id: 'q3', text: '我购买不是因为同伴影响或害怕落后，而是确实满足学习生活刚需吗？' });
    } else if (intent === 'reduce_budget') {
      baseQuestions.push({ id: 'q3', text: '降低预算后的替代方案是否已经能满足核心需求？' });
    }

    if (trigger === '同学都换新机') {
      baseQuestions.push({ id: 'q4', text: '如果身边同学没有换新机，我是否还会现在购买？' });
    } else if (trigger === '限时优惠') {
      baseQuestions.push({ id: 'q4', text: '优惠结束后，我是否仍认为这笔支出值得？' });
    }

    baseQuestions.push({ id: 'q5', text: '我是否已经算清总成本、手续费、每期压力和逾期成本？' });

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
      const data = await apiPost<{ id: string }>('/api/v1/analysis', {
        scenario: 'pre_trade_check',
        stock_id: stockId,
        scenario_payload: {
          intent,
          trigger_reason: trigger,
          emotion_level: emotion,
          monthly_allowance: Number(monthlyAllowance),
          spent_this_month: Number(spentThisMonth),
          item_price: Number(itemPrice),
          installment_months: Number(installmentMonths),
          decision_domain: 'campus_consumption',
          self_check_answers: answers,
          show_self_check: showSelfCheck,
          stock_name: stockName || undefined,
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
    <div className="space-y-7 px-4 py-5 pb-32">
      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">消费决策自检</h2>
        <p className="text-sm leading-relaxed text-stone-500">在大额消费或分期前，先确认这次决定符合预算边界，而不是被情绪推着走。</p>
      </div>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">本次决策对象</label>
        <button
          onClick={() => navigate('/stock/search?callback=/analysis/pre-trade')}
          className="flex w-full items-center justify-between rounded-3xl border border-stone-200 bg-white/80 p-4 transition-colors hover:bg-white"
        >
          {stockId ? (
            <div className="text-left">
              <div className="font-bold text-lg">{stockName}</div>
              <div className="text-xs text-stone-400">
                {isCampusDemoObject ? '校园消费 Demo · 大额分期自检' : stockId}
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-stone-400">
              <Search size={18} />
              <span className="text-sm">选择演示对象或手动输入消费场景</span>
            </div>
          )}
          <ChevronRight size={18} className="text-stone-300" />
        </button>
      </section>

      <section className="space-y-3">
        <label className="text-sm font-bold uppercase tracking-widest text-stone-400">当前意图</label>
        <div className="grid grid-cols-2 gap-2">
          {[
            { value: 'purchase', label: '购买 / 分期', active: 'text-teal-700 border-teal-100 bg-mist' },
            { value: 'delay', label: '暂缓', active: 'text-amber-700 border-amber-100 bg-amber-50' },
            { value: 'reduce_budget', label: '降低预算', active: 'text-teal-700 border-teal-100 bg-mist' },
            { value: 'review', label: '加入复盘', active: 'text-stone-700 border-stone-200 bg-stone-100' },
          ].map((option) => (
            <button
              key={option.value}
              onClick={() => setIntent(option.value as Intent)}
              className={cn(
                'rounded-2xl border py-3 text-sm font-bold transition-all',
                intent === option.value ? option.active : 'border-stone-200 bg-white text-stone-400'
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      </section>

      <section className="grid grid-cols-2 gap-3">
        {[
          { label: '月生活费', value: monthlyAllowance, setter: setMonthlyAllowance, suffix: '元' },
          { label: '本月已消费', value: spentThisMonth, setter: setSpentThisMonth, suffix: '元' },
          { label: '商品价格', value: itemPrice, setter: setItemPrice, suffix: '元' },
          { label: '计划分期', value: installmentMonths, setter: setInstallmentMonths, suffix: '期' },
        ].map((field) => (
          <label key={field.label} className="space-y-2">
            <span className="text-xs font-bold uppercase tracking-widest text-stone-400">{field.label}</span>
            <div className="flex items-center rounded-2xl border border-stone-200 bg-white/80 px-3">
              <input
                inputMode="numeric"
                value={field.value}
                onChange={(event) => field.setter(event.target.value)}
                className="min-w-0 flex-1 bg-transparent py-3 text-sm font-bold outline-none"
              />
              <span className="text-xs text-stone-400">{field.suffix}</span>
            </div>
          </label>
        ))}
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
                trigger === item ? 'border-teal-700 bg-teal-700 text-white' : 'border-stone-200 bg-white text-stone-500'
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
            {emotion}/5 · {emotion <= 2 ? '比较冷静' : emotion === 3 ? '有些波动' : '明显冲动'}
          </span>
        </div>
        <input
          type="range"
          min="1"
          max="5"
          step="1"
          className="w-full accent-teal-700"
          value={emotion}
          onChange={(event) => setEmotion(parseInt(event.target.value, 10))}
        />
        <div className="flex justify-between text-[10px] text-stone-300 font-bold uppercase tracking-tighter">
          <span>冷静</span>
          <span>中性</span>
          <span>冲动</span>
        </div>
        {emotion >= 4 && (
          <p className="rounded-xl bg-amber-50 border border-amber-100 px-3 py-2 text-xs leading-relaxed text-amber-800">
            情绪达到 {emotion}/5 时，系统会先进入消费冷静期：先问清预算、同伴影响和分期真实成本，再生成决策卡。
          </p>
        )}
      </section>

      {(trigger === '同学都换新机' || trigger === '限时优惠') && (
        <div
          className={cn(
            'p-4 rounded-2xl border flex gap-3 items-start',
            trigger === '同学都换新机' ? 'border-amber-100 bg-amber-50' : 'border-teal-100 bg-mist'
          )}
        >
          <AlertTriangle
            size={18}
            className={cn('mt-0.5 shrink-0', trigger === '同学都换新机' ? 'text-amber-600' : 'text-teal-700')}
          />
          <p
            className={cn(
              'text-xs leading-relaxed font-medium',
              trigger === '同学都换新机' ? 'text-amber-900' : 'text-teal-900'
            )}
          >
            {trigger === '同学都换新机'
              ? '系统识别到明显同伴影响，建议先确认这是不是你的真实需求，而不是盲目跟风。'
              : '系统识别到限时优惠压力，建议先计算总成本，再判断是否真的划算。'}
          </p>
        </div>
      )}

      {showSelfCheck && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="soft-card space-y-4 rounded-[28px] p-6"
        >
          <div className="flex items-center gap-2">
            <CheckCircle2 size={20} className="text-teal-700" />
            <h3 className="font-bold text-lg">消费冷静期自检</h3>
          </div>
          <p className="text-xs text-stone-400">
            这一步不是替你做决定，而是把“想立刻买”的情绪拆成预算、必要性、同伴影响和真实成本四件事。
          </p>
          <div className="space-y-4">
            {selfCheckQuestions.map((question, index) => (
              <div key={question.id} className="space-y-2">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-mist text-[10px] font-bold text-teal-700">
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
                        ? 'border border-teal-100 bg-mist text-teal-700'
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
                        ? 'border border-amber-100 bg-amber-50 text-amber-700'
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
        <div className="rounded-2xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <div className="pt-4">
        {!showSelfCheck && emotion > 3 && stockId && intent && trigger ? (
          <div className="space-y-3">
            <div className="bg-amber-50 border border-amber-100 p-4 rounded-2xl flex gap-3 items-start">
              <AlertTriangle size={18} className="text-amber-500 shrink-0 mt-0.5" />
              <p className="text-xs text-amber-800 leading-relaxed">
                当前情绪评分偏高，系统建议先完成消费冷静期自检，再生成六段式校园决策卡。
              </p>
            </div>
            <button
              onClick={() => setShowSelfCheck(true)}
              className="w-full rounded-2xl bg-teal-700 py-4 text-lg font-bold text-white transition-all active:scale-[0.98]"
            >
              进入消费冷静期
            </button>
          </div>
        ) : (
          <button
            disabled={!stockId || !intent || !trigger || (showSelfCheck && !allQuestionsAnswered) || submitting}
            onClick={handleSubmit}
            className="w-full rounded-2xl bg-teal-700 py-4 text-lg font-bold text-white transition-all active:scale-[0.98] disabled:scale-100 disabled:opacity-30"
          >
            {submitting ? '分析中...' : showSelfCheck ? '完成自检并生成决策卡' : '开始消费自检'}
          </button>
        )}
      </div>
    </div>
  );
}
