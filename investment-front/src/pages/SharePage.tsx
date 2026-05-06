import { useEffect, useState } from 'react';
import { AlertTriangle, Clock, ShieldCheck } from 'lucide-react';
import { useParams } from 'react-router-dom';

import { getPublicShareSnapshot } from '../api';
import type { ShareSnapshot } from '../types';

function formatDate(value?: string | null) {
  if (!value) return '--';
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function SharePage() {
  const { shareId } = useParams();
  const [snapshot, setSnapshot] = useState<ShareSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!shareId) {
      setError('分享卡片不存在');
      setLoading(false);
      return;
    }
    getPublicShareSnapshot(shareId)
      .then((data) => {
        setSnapshot(data);
        setError(null);
      })
      .catch((err) => setError(err instanceof Error ? err.message : '分享卡片暂时不可访问'))
      .finally(() => setLoading(false));
  }, [shareId]);

  if (loading) {
    return <div className="p-6 text-sm text-stone-500">正在加载分享卡片...</div>;
  }

  if (error || !snapshot) {
    return (
      <div className="p-6 min-h-[60vh] flex items-center justify-center">
        <div className="bg-white border border-stone-100 rounded-2xl p-6 text-center space-y-3">
          <AlertTriangle className="mx-auto text-amber-500" size={28} />
          <div className="font-bold">分享卡片不可访问</div>
          <p className="text-sm text-stone-500">{error || '可能已过期或已撤销'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-5 space-y-4">
      <section className="bg-white border border-stone-100 rounded-2xl p-5 space-y-4">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600">
            <ShieldCheck size={20} />
          </div>
          <div className="space-y-1">
            <h2 className="text-lg font-bold leading-snug">{snapshot.title}</h2>
            <p className="text-xs text-stone-400">校园金融素养成长卡</p>
          </div>
        </div>
        <p className="text-sm text-stone-600 leading-relaxed">{snapshot.summary}</p>
        <div className="flex items-center gap-2 text-xs text-stone-500">
          <Clock size={14} />
          <span>数据时间：{formatDate(snapshot.data_timestamp)}</span>
        </div>
      </section>

      <section className="bg-white border border-stone-100 rounded-2xl p-5 space-y-3">
        <h3 className="text-xs font-bold text-stone-400 uppercase tracking-widest">支撑证据</h3>
        {snapshot.support_evidence.map((item, index) => (
          <p key={index} className="text-sm text-stone-700 leading-relaxed">{item}</p>
        ))}
      </section>

      <section className="bg-white border border-stone-100 rounded-2xl p-5 space-y-3">
        <h3 className="text-xs font-bold text-stone-400 uppercase tracking-widest">反方证据与风险</h3>
        {[...snapshot.counter_evidence, ...snapshot.risks].map((item, index) => (
          <p key={index} className="text-sm text-stone-700 leading-relaxed">{item}</p>
        ))}
      </section>

      <section className="bg-stone-900 text-white rounded-2xl p-5 space-y-3">
        <h3 className="text-xs font-bold text-amber-300 uppercase tracking-widest">复盘条件</h3>
        {snapshot.invalidation_conditions.map((item, index) => (
          <p key={index} className="text-sm text-stone-200 leading-relaxed">{item}</p>
        ))}
      </section>

      <p className="text-xs text-stone-500 leading-relaxed bg-amber-50 border border-amber-100 rounded-2xl p-4">
        {snapshot.disclaimer}
      </p>
    </div>
  );
}
