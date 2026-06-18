import { Link } from 'react-router-dom'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { useState } from 'react'
import { remotePolish } from '../nlp/api.js'
import PageHeader from '../components/PageHeader.jsx'
import { ROUTES } from '../config/routes.js'

const styleOptions = ['文学化', '克制', '诗性', '叙事', '更有画面感'];

const PolishPage = () => {
  const [inputText, setInputText] = useState(() => {
    const draft = sessionStorage.getItem('musagent:polishDraft');
    if (draft) {
      sessionStorage.removeItem('musagent:polishDraft');
      return draft;
    }
    return '黄昏把影子拉得很长很长。 像极了十八岁那年，我们说过的远方。 后来远山吞没了夕阳，归鸟衔走了最后一声告别。';
  })
  const [targetStyle, setTargetStyle] = useState('文学化')
  const [result, setResult] = useState(null)
  const [isRunning, setIsRunning] = useState(false)

  useGSAP(() => {
    gsap.from('.page-polish h1', { yPercent: 100, duration: 1.2, ease: 'expo.out' });
    gsap.from('.create-panel', { y: 40, duration: 0.8, ease: 'power2.out', stagger: 0.15, delay: 0.3 });
  }, [])

  const handleAnalyze = async () => {
    if (!inputText.trim() || isRunning) return;
    setResult(null)
    setIsRunning(true)
    try {
      const polish = await remotePolish({
        text: inputText,
        targetStyle,
        preserveMeaning: true,
        useLLM: true,
      });
      setResult(polish);
    } catch (err) {
      setResult({
        error: true,
        message: err.message,
        keywords: [],
        emotion: { dominant: '未知', scores: {}, intensity: 0 },
        diagnosis: ['润色失败，请确认后端服务已启动。'],
        suggestions: [err.message],
        conservative: '',
        creative: '',
        method: '错误',
        llmUsed: false,
      });
    }
    setIsRunning(false);
  };

  const copyText = async (text) => {
    if (text) await navigator.clipboard.writeText(text);
  };

  return (
    <section className="page-polish page-manuscript min-h-dvh pt-28 md:pt-32 pb-20">
      <div className="container mx-auto px-5 2xl:px-0">
        <PageHeader
          badge="创作润色"
          title="创作与润色"
          description="针对已有文本进行诊断与文学化改写。若需修正错别字，请使用文本校错。"
        />
        <div className="info-banner max-w-3xl mx-auto mb-8 font-cjk">
          润色 = 保留原意的文学化表达 ·
          <Link to={ROUTES.correct.path} className="text-yellow ml-1">文本校错</Link> = 错别字与标点规范（不改写文风）
        </div>

        <div className="grid xl:grid-cols-3 gap-8 max-w-7xl mx-auto">
          <div className="create-panel space-y-4">
            <div className="p-6 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
              <h2 className="text-lg font-cjk font-medium mb-4">原文输入</h2>
              <textarea value={inputText} onChange={e => setInputText(e.target.value)} rows={12}
                className="w-full px-4 py-3 rounded-xl text-sm focus:outline-none resize-none font-cjk"
                style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)' }} />
              <div className="mt-4">
                <p className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>润色目标</p>
                <div className="flex flex-wrap gap-2">
                  {styleOptions.map(option => (
                    <button key={option} onClick={() => setTargetStyle(option)}
                      className={`px-3 py-1.5 rounded-full text-xs transition-colors font-cjk ${targetStyle === option ? 'bg-yellow text-black' : ''}`}
                      style={targetStyle !== option ? { backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' } : {}}>
                      {option}
                    </button>
                  ))}
                </div>
              </div>
              <button onClick={handleAnalyze} disabled={isRunning || !inputText.trim()} className="w-full mt-4 py-3 rounded-xl bg-yellow text-black font-semibold cursor-pointer disabled:opacity-50 font-cjk">
                {isRunning ? '⏳ 正在润色…' : '✨ 开始分析与润色'}
              </button>
            </div>
          </div>

          <div className="create-panel">
            <div className="p-6 rounded-2xl h-full min-h-[280px] flex flex-col justify-center" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
              {isRunning ? (
                <div className="text-center py-8">
                  <div className="inline-flex gap-1.5 mb-4">
                    <span className="w-2 h-2 rounded-full bg-yellow animate-pulse" />
                    <span className="w-2 h-2 rounded-full bg-yellow animate-pulse" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 rounded-full bg-yellow animate-pulse" style={{ animationDelay: '300ms' }} />
                  </div>
                  <p className="font-cjk text-sm" style={{ color: 'var(--text-secondary)' }}>正在分析文本并生成润色版本…</p>
                  <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>通常需要 10–30 秒</p>
                </div>
              ) : !result ? (
                <div className="text-center py-8" style={{ color: 'var(--text-muted)' }}>
                  <span className="text-4xl block mb-3">✍️</span>
                  <p className="font-cjk text-sm">输入原文后点击润色，诊断与改写结果将在此展示</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-xs font-cjk" style={{ color: 'var(--text-muted)' }}>分析完成</p>
                  <p className="text-sm font-cjk">
                    主导情绪：<span className="text-yellow font-medium">{result.emotion?.dominant || '未知'}</span>
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {(result.keywords || []).slice(0, 5).map(kw => (
                      <span key={kw.keyword} className="px-2 py-0.5 rounded-full text-[10px] bg-yellow text-black">{kw.keyword}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="create-panel space-y-4 xl:col-span-1">
            {result ? (
              <>
                <div className="p-4 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                  <h3 className="text-xs font-medium mb-2 font-cjk" style={{ color: 'var(--text-muted)' }}>原文诊断</h3>
                  <ul className="space-y-1.5">{(result.diagnosis || []).map((s, i) => <li key={i} className="text-xs font-cjk" style={{ color: 'var(--text-secondary)' }}>{s}</li>)}</ul>
                </div>

                <div className="p-4 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                  <h3 className="text-xs font-medium mb-2 font-cjk" style={{ color: 'var(--text-muted)' }}>润色建议</h3>
                  <ul className="space-y-1.5">{(result.suggestions || []).map((s, i) => <li key={i} className="text-xs flex gap-1.5 font-cjk" style={{ color: 'var(--text-secondary)' }}><span className="text-yellow">►</span>{s}</li>)}</ul>
                </div>

                <div className="grid grid-cols-1 gap-3">
                  <div className="p-3 rounded-2xl border border-white/20" style={{ backgroundColor: 'var(--bg-card)' }}>
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-xs font-medium font-cjk" style={{ color: 'var(--text-secondary)' }}>保守润色</h3>
                      <button onClick={() => copyText(result.conservative)} className="text-[10px] text-yellow">复制</button>
                    </div>
                    <pre className="text-xs leading-relaxed font-cjk whitespace-pre-wrap" style={{ color: 'var(--text-primary)' }}>{result.conservative}</pre>
                  </div>
                  <div className="p-3 rounded-2xl border border-yellow/30" style={{ backgroundColor: 'var(--bg-card)' }}>
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-xs font-medium text-yellow font-cjk">风格化润色</h3>
                      <button onClick={() => copyText(result.creative)} className="text-[10px] text-yellow">复制</button>
                    </div>
                    <pre className="text-xs leading-relaxed font-cjk whitespace-pre-wrap" style={{ color: 'var(--text-primary)' }}>{result.creative}</pre>
                  </div>
                </div>
                <p className="text-[10px] text-center font-cjk" style={{ color: 'var(--text-muted)' }}>{result.method} · {result.llmUsed ? 'DeepSeek 已启用' : '规则降级'}</p>
              </>
            ) : (
              <div className="flex-center h-full min-h-[300px] rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                <div className="text-center"><span className="text-4xl block mb-3">📋</span><p className="text-sm font-cjk" style={{ color: 'var(--text-muted)' }}>润色结果将在此展示</p></div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}

export default PolishPage
