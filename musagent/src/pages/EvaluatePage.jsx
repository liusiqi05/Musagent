import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../components/PageHeader.jsx';
import { fetchEvaluation } from '../nlp/api.js';
import { ROUTES } from '../config/routes.js';

const EvaluatePage = () => {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const report = await fetchEvaluation();
        if (!cancelled) setData(report);
      } catch (e) {
        if (!cancelled) setError(e.message || '评测接口不可用');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <section className="page-evaluate page-manuscript min-h-dvh pt-28 md:pt-32 pb-20">
      <div className="container mx-auto px-5 2xl:px-0 max-w-5xl">
        <PageHeader
          badge="算法评测"
          title="NLP 技术 Benchmark"
          description="面向开发者与答辩场景的定量评测，使用固定样例集对比检索与情感指标。普通创作者请使用灵感页的评价功能。"
        />

        <div className="info-banner mb-6 text-sm">
          此页面不属于用户创作流程。用户生成后的评分与标签反馈会写入数据库，并回流到检索权重与 LLM 提示。
        </div>

        {loading && (
          <div className="text-center py-20" style={{ color: 'var(--text-muted)' }}>正在运行评测...</div>
        )}

        {error && (
          <div className="p-4 rounded-2xl mb-8 text-sm" style={{ backgroundColor: 'rgba(239,68,68,0.12)', color: '#fecaca' }}>
            {error} — 请确认后端已启动。
          </div>
        )}

        {data && (
          <div className="space-y-6">
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: '情感命中率', value: `${Math.round((data.summary?.emotionAccuracy || 0) * 100)}%` },
                { label: '关键词通过率', value: `${Math.round((data.summary?.keywordPassRate || 0) * 100)}%` },
                { label: '平均检索条数', value: data.summary?.avgRetrievalCount ?? '-' },
                { label: '校错演示修改', value: `${data.summary?.correctionDemoChanges ?? 0} 处` },
              ].map((m) => (
                <div key={m.label} className="p-4 rounded-2xl text-center" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                  <p className="text-2xl font-bold text-yellow">{m.value}</p>
                  <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{m.label}</p>
                </div>
              ))}
            </div>

            {(data.ablation || []).length > 0 && (
              <div className="p-5 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                <h2 className="text-sm font-medium mb-4 text-yellow">检索 Ablation（BM25 vs 混合）</h2>
                <div className="space-y-3">
                  {data.ablation.map((row) => (
                    <div key={row.topic} className="text-xs p-3 rounded-lg" style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
                      <p className="font-medium mb-1" style={{ color: 'var(--text-primary)' }}>{row.topic}</p>
                      <p>BM25 Top1：{row.bm25TopTitle || '—'} · 混合 Top1：{row.hybridTopTitle || '—'}</p>
                      <p className="mt-1" style={{ color: 'var(--text-muted)' }}>
                        重叠 {row.overlapCount}/5 · 混合精排分 {typeof row.semanticGain === 'number' ? row.semanticGain.toFixed(3) : row.semanticGain}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {(data.samples || []).some((s) => s.explanationSample) && (
              <div className="p-5 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                <h2 className="text-sm font-medium mb-3 text-yellow">语义解释样例</h2>
                {(data.samples || []).map((row) => (
                  row.explanationSample ? (
                    <p key={row.topic} className="text-xs mb-2 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                      <span className="text-yellow">{row.topic}</span> → {row.explanationSample}
                    </p>
                  ) : null
                ))}
              </div>
            )}

            <div className="p-5 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
              <h2 className="text-sm font-medium mb-4 text-yellow">样例评测明细</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr style={{ color: 'var(--text-muted)' }}>
                      <th className="pb-2 pr-3">主题</th>
                      <th className="pb-2 pr-3">情感</th>
                      <th className="pb-2 pr-3">命中</th>
                      <th className="pb-2 pr-3">检索</th>
                      <th className="pb-2">Top1</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.samples || []).map((row) => (
                      <tr key={row.topic} style={{ color: 'var(--text-secondary)', borderTop: '1px solid var(--border-color)' }}>
                        <td className="py-2 pr-3 max-w-[140px]">{row.topic}</td>
                        <td className="py-2 pr-3">{row.emotion}</td>
                        <td className="py-2 pr-3">{row.emotionMatch ? '✓' : '—'}</td>
                        <td className="py-2 pr-3">{row.retrievalCount}</td>
                        <td className="py-2">{row.topTitle || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {data.correctionDemo && (
              <div className="p-5 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                <h2 className="text-sm font-medium mb-3 text-yellow">校错演示</h2>
                <p className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>原文</p>
                <p className="text-sm mb-3" style={{ color: 'var(--text-secondary)' }}>{data.correctionDemo.original}</p>
                <p className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>校错后</p>
                <p className="text-sm font-serif" style={{ color: 'var(--text-primary)' }}>{data.correctionDemo.corrected}</p>
              </div>
            )}

            <p className="text-center text-xs" style={{ color: 'var(--text-muted)' }}>
              完整回归测试见后端 <code>product_regression_tests.py</code>（22 项） ·
              <Link to={ROUTES.workflow.path} className="text-yellow ml-1">查看流水线架构</Link>
            </p>
          </div>
        )}
      </div>
    </section>
  );
};

export default EvaluatePage;
