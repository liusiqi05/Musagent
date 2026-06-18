import { Link } from 'react-router-dom'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { useState } from 'react'
import { remoteCorrect } from '../nlp/api.js'
import PageHeader from '../components/PageHeader.jsx'
import { ROUTES } from '../config/routes.js'

const SAMPLE_TEXT = '我迫不急待的想要以经完成的做业，在在重复阅读。黄昏把影子拉的很长很长，像极了十八岁那年我们说过的远方。';

const CorrectPage = () => {
  const [inputText, setInputText] = useState(SAMPLE_TEXT)
  const [result, setResult] = useState(null)
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState('')

  useGSAP(() => {
    gsap.from('.page-correct h1', { yPercent: 100, duration: 1.2, ease: 'expo.out' });
    gsap.from('.correct-panel', { y: 40, duration: 0.8, ease: 'power2.out', stagger: 0.12, delay: 0.3 });
  }, []);

  const handleCorrect = async () => {
    if (!inputText.trim() || isRunning) return;
    setIsRunning(true);
    setError('');
    setResult(null);
    try {
      const data = await remoteCorrect(inputText);
      setResult(data);
    } catch (err) {
      setError(err.message || '校错失败');
    }
    setIsRunning(false);
  };

  const copyText = async (text) => {
    if (text) await navigator.clipboard.writeText(text);
  };

  return (
    <section className="page-correct page-manuscript min-h-dvh pt-28 md:pt-32 pb-20">
      <div className="container mx-auto px-5 2xl:px-0">
        <PageHeader
          badge="CorrectAgent"
          title="文本校错"
          description="MacBERT (pycorrector) 深度校错 + 规则后处理。不改动文学风格。"
        />
        <div className="info-banner max-w-3xl mx-auto mb-8">
          如需文学化改写而非改错，请前往
          <Link to={ROUTES.polish.path} className="text-yellow ml-1">创作润色</Link>
        </div>

        <div className="grid xl:grid-cols-2 gap-8 max-w-6xl mx-auto">
          <div className="correct-panel">
            <div className="p-6 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
              <h2 className="text-lg font-medium mb-4">📝 待校错文本</h2>
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                rows={12}
                className="w-full px-4 py-3 rounded-xl text-sm focus:outline-none resize-none"
                style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)' }}
              />
              <button onClick={handleCorrect} disabled={isRunning || !inputText.trim()}
                className="w-full mt-4 py-3 rounded-xl bg-yellow text-black font-semibold cursor-pointer disabled:opacity-50">
                {isRunning ? '⏳ 校错中...' : '🔧 开始校错'}
              </button>
              {error && <p className="mt-3 text-xs text-red-400">{error}</p>}
            </div>
          </div>

          <div className="correct-panel space-y-4">
            {result ? (
              <>
                <div className="p-5 rounded-2xl border border-yellow/30" style={{ backgroundColor: 'var(--bg-card)' }}>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-medium text-yellow">✅ 校错结果</h3>
                    <button onClick={() => copyText(result.corrected)} className="text-[10px] text-yellow">复制</button>
                  </div>
                  <pre className="text-sm leading-relaxed font-serif whitespace-pre-wrap" style={{ color: 'var(--text-primary)' }}>{result.corrected}</pre>
                  <p className="text-[10px] mt-3" style={{ color: 'var(--text-muted)' }}>
                    {result.method} · 修改 {result.stats?.changeCount || 0} 处
                  </p>
                </div>

                <div className="p-4 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                  <h3 className="text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>📋 修改明细</h3>
                  {(result.corrections || []).length > 0 ? (
                    <ul className="space-y-2">
                      {result.corrections.map((c, i) => (
                        <li key={i} className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                          <span className="text-yellow">[{c.type}]</span> {c.from} → {c.to}
                          <span className="block text-[10px]" style={{ color: 'var(--text-muted)' }}>{c.reason}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>未检测到需修正项</p>
                  )}
                </div>

                {result.emotion && (
                  <div className="p-4 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                    <h3 className="text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>💭 校错后情感（词典+RoBERTa）</h3>
                    <p className="text-sm">主导：<span className="text-yellow font-bold">{result.emotion.dominant}</span></p>
                  </div>
                )}
              </>
            ) : (
              <div className="flex-center min-h-[360px] rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                <div className="text-center">
                  <span className="text-5xl block mb-4">🔧</span>
                  <p style={{ color: 'var(--text-secondary)' }}>输入含错别字的文本开始校错</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};

export default CorrectPage;
