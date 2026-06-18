import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { useState } from 'react'
import { remoteSummarize } from '../nlp/api.js'
import PageHeader from '../components/PageHeader.jsx'

const SAMPLE_TEXT = `春天来了，校园里的樱花悄悄绽放。少年们在操场上奔跑，笑声像风一样掠过课桌与黑板。
多年以后，当我独自走在城市的地铁里，仍会想起那些说不出口的喜欢，和黄昏里慢慢散开的青春。`;

const SummaryPage = () => {
  const [inputText, setInputText] = useState(SAMPLE_TEXT)
  const [topN, setTopN] = useState(3)
  const [result, setResult] = useState(null)
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState('')

  useGSAP(() => {
    gsap.from('.summary-panel', { y: 40, duration: 0.8, ease: 'power2.out', stagger: 0.12, delay: 0.2 });
  }, []);

  const handleSummarize = async () => {
    if (!inputText.trim() || isRunning) return;
    setIsRunning(true);
    setError('');
    setResult(null);
    try {
      const data = await remoteSummarize(inputText, topN);
      setResult(data);
    } catch (err) {
      setError(err.message || '摘要生成失败');
    }
    setIsRunning(false);
  };

  return (
    <section className="page-summary page-manuscript min-h-dvh pt-28 md:pt-32 pb-20">
      <div className="container mx-auto px-5 2xl:px-0">
        <PageHeader
          badge="TextRank 自动文摘"
          title="自动文摘"
          description="基于 TextRank 对长文本句子重要性排序，提取核心摘要句。"
        />

        <div className="grid xl:grid-cols-2 gap-8 max-w-6xl mx-auto">
          <div className="summary-panel space-y-4">
            <div className="p-6 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
              <h2 className="text-lg font-medium mb-4">📄 原文输入</h2>
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                rows={14}
                className="w-full px-4 py-3 rounded-xl text-sm focus:outline-none resize-none"
                style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)' }}
              />
              <div className="mt-4 flex items-center gap-3">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>摘要句数</span>
                {[2, 3, 5].map((n) => (
                  <button key={n} type="button" onClick={() => setTopN(n)}
                    className={`px-3 py-1.5 rounded-full text-xs ${topN === n ? 'bg-yellow text-black' : ''}`}
                    style={topN !== n ? { backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' } : {}}>
                    {n} 句
                  </button>
                ))}
              </div>
              <button type="button" onClick={handleSummarize} disabled={isRunning || !inputText.trim()}
                className="w-full mt-4 py-3 rounded-xl bg-yellow text-black font-semibold cursor-pointer disabled:opacity-50">
                {isRunning ? '⏳ TextRank 计算中...' : '📋 生成摘要'}
              </button>
              {error && <p className="mt-3 text-xs text-red-400">{error}</p>}
            </div>
          </div>

          <div className="summary-panel space-y-4">
            {result ? (
              <>
                <div className="p-5 rounded-2xl border border-yellow/30" style={{ backgroundColor: 'var(--bg-card)' }}>
                  <h3 className="text-sm font-medium text-yellow mb-3">📋 自动摘要</h3>
                  <p className="text-sm leading-relaxed font-serif" style={{ color: 'var(--text-primary)' }}>{result.summary}</p>
                  <p className="text-[10px] mt-3" style={{ color: 'var(--text-muted)' }}>
                    原文 {result.sentenceCount || result.count || '-'} 句 → 提取 Top {topN}
                  </p>
                </div>
                <div className="p-4 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                  <h3 className="text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>🔑 伴随关键词</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {(result.keywords || []).map((kw) => (
                      <span key={kw.keyword} className="px-2 py-0.5 rounded-full text-[10px] bg-yellow text-black">{kw.keyword}</span>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-center min-h-[360px] rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                <div className="text-center">
                  <span className="text-5xl block mb-4">📋</span>
                  <p style={{ color: 'var(--text-secondary)' }}>粘贴长文后点击生成摘要</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};

export default SummaryPage;
