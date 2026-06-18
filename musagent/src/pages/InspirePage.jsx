import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { runPipeline } from '../nlp/pipeline.js'
import { remoteRegenerate } from '../nlp/api.js'
import PageHeader from '../components/PageHeader.jsx'
import PostGenerationReview from '../components/PostGenerationReview.jsx'
import TopicGraphPanel from '../components/TopicGraphPanel.jsx'
import InspirationChatPanel from '../components/InspirationChatPanel.jsx'
import MusAgentVsLLM from '../components/MusAgentVsLLM.jsx'
import GenerationResultCard from '../components/GenerationResultCard.jsx'  // v3.0 拆出
import { ROUTES } from '../config/routes.js'
import { formatAuthor } from '../utils/author.js'

const creationTypes = ['现代诗', '古典诗', '散文', '短篇片段'];
const languageStyleOptions = ['清新', '浪漫', '克制', '朦胧', '叙事'];
const rhymeOptions = ['自由', '轻微押韵', '强押韵'];
const abstractionOptions = ['具象', '平衡', '抽象'];

/** 文字风格 → 后端艺术风格映射（用户不感知视觉艺术术语） */
const STYLE_TO_ART = {
  清新: '极简主义',
  浪漫: '印象派',
  克制: '中国水墨',
  朦胧: '超现实主义',
  叙事: '表现主义',
};

const PIPELINE_STAGE_LABELS = {
  seg: '分词分析',
  ner: '实体识别',
  qe: '主题扩展',
  kw: '关键词提取',
  sum: '主题摘要',
  ret: '知识库检索',
  emo: '情感分析',
  xpl: '参考解读',
  rag: '素材整理',
  art: '风格匹配',
  mus: '音乐映射',
  sty: '风格映射',
  gen: '模板草稿',
  llm: 'AI 创作',
  critic: 'Critic 自评',
  qa: '质量评估',
  kg: '关联图谱',
};

/** Pipeline stage id → Agent 卡片 id */
const STAGE_TO_AGENT = {
  seg: 'wordseg',
  ner: 'ner',
  kw: 'keyword',
  sum: 'summary',
  emo: 'emotion',
  qe: 'intent',
  xpl: 'intent',
  ret: 'retrieval',
  rag: 'rag',
  gen: 'writer',
  llm: 'writer',
  art: 'writer',
  mus: 'writer',
  qa: 'writer',
  kg: 'retrieval',
  critic: 'critic',  // v3.0 新增：Critic Agent
};

const InspirePage = () => {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('generate')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [topic, setTopic] = useState('城市孤独')
  const [creationType, setCreationType] = useState('现代诗')
  const [lengthPreference, setLengthPreference] = useState('中')
  const [languageStyle, setLanguageStyle] = useState('清新')
  const [rhymeLevel, setRhymeLevel] = useState('自由')
  const [abstractionLevel, setAbstractionLevel] = useState('平衡')
  const [showResult, setShowResult] = useState(false)
  const [pipelineResult, setPipelineResult] = useState(null)
  const [isRunning, setIsRunning] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [copyStatus, setCopyStatus] = useState('')
  const [agentLog, setAgentLog] = useState([])
  const [showAnalysisDetail, setShowAnalysisDetail] = useState(false)
  const [showAgentDetail, setShowAgentDetail] = useState(false)
  const [progress, setProgress] = useState(0)
  const [progressStage, setProgressStage] = useState('')
  const [completedStages, setCompletedStages] = useState([])
  const [reviewDone, setReviewDone] = useState(false)
  const [fastMode, setFastMode] = useState(false)

  const agents = [
    { id: 'wordseg', label: '中文分词', icon: '📝' },
    { id: 'ner', label: '实体识别', icon: '🏷️' },
    { id: 'keyword', label: '关键词提取', icon: '🔑' },
    { id: 'summary', label: '文本摘要', icon: '📋' },
    { id: 'emotion', label: '情感分析', icon: '💭' },
    { id: 'intent', label: '意图理解', icon: '🎯' },
    { id: 'retrieval', label: '混合检索', icon: '🔍' },
    { id: 'rag', label: '知识增强', icon: '📚' },
    { id: 'writer', label: '文本生成', icon: '✍️' },
    { id: 'critic', label: 'Critic Agent', icon: '🧐' },
  ];

  const progressStages = ['分词与实体识别', '情感与关键词', '知识库检索', 'AI 创作生成', 'Critic 自评'];

  const handlePipelineStage = (stage) => {
    const label = PIPELINE_STAGE_LABELS[stage.id] || stage.name || '处理中';
    setProgressStage(`${label} · ${stage.durationMs}ms`);
    setProgress(Math.max(stage.progress || 0, 5));
    setCompletedStages((prev) => [...prev, stage.id]);

    const agentId = STAGE_TO_AGENT[stage.id];
    if (agentId) {
      setAgentLog((prev) => prev.map((a) => (
        a.id === agentId ? { ...a, status: 'done' } : a
      )));
    }
  };

  const mapArtStyle = (style) => STYLE_TO_ART[style] || '极简主义';

  const lengthOptions = creationType === '现代诗' || creationType === '古典诗'
    ? ['短', '中', '长']
    : ['短', '中', '长', '超长'];

  const syncProgressFromPipeline = (result) => {
    const stages = result?.pipeline?.stages;
    if (!stages?.length) return;
    const last = stages[stages.length - 1];
    const label = PIPELINE_STAGE_LABELS[last.id] || last.name || '完成';
    setProgressStage(`${label} · ${last.durationMs}ms`);
    setProgress(100);
  };

  useGSAP(() => {
    gsap.from('.page-inspire h1', { yPercent: 100, duration: 1.2, ease: 'expo.out' });
    gsap.from('.page-inspire .badge', { opacity: 0, y: 30, duration: 0.8, ease: 'power2.out' });
    gsap.from('.input-panel, .result-panel', { y: 50, duration: 0.8, ease: 'power2.out', stagger: 0.15, delay: 0.5 });
  }, []);

  const handleGenerate = async () => {
    setShowResult(false)
    setPipelineResult(null)
    setShowAgentDetail(false)
    setProgress(0)
    setCompletedStages([])
    setAgentLog(agents.map(a => ({ ...a, status: 'running' })))
    setIsRunning(true)

    try {
      const result = await runPipeline({
        topic,
        creationType,
        emotionTone: '自动',
        artStyle: mapArtStyle(languageStyle),
        lengthPreference,
        languageStyle,
        rhymeLevel,
        abstractionLevel,
        fastMode,
      }, { onStage: handlePipelineStage });

      if (!result || !result.generated) {
        throw new Error('Pipeline 返回数据为空');
      }

      setAgentLog(prev => prev.map(a => ({ ...a, status: 'done' })));
      syncProgressFromPipeline(result);
      if (!result?.pipeline?.stages?.length) {
        setProgress(100);
        setProgressStage('创作完成');
      }
      setPipelineResult(result);
      setShowResult(true);
      setReviewDone(false);
      setShowAnalysisDetail(false);
    } catch (err) {
      console.error('[灵感生成] 错误:', err);
      setAgentLog(prev => prev.map(a => ({ ...a, status: 'error' })));
      setPipelineResult({
        error: true,
        message: err.message || '未知错误',
        generated: { method: '错误', content: '生成失败：' + (err.message || '请检查后端是否正常运行'), note: '' },
        generatedLLM: { method: '错误', content: '生成失败：' + (err.message || '请检查后端是否正常运行'), note: '' },
        keywords: [], emotion: { dominant: '未知', scores: {}, intensity: 0 },
        queryExpansion: { core: [], imagery: [], expanded: [] },
        summary: '', similarWorks: [], ragResults: [],
        artStyles: [], music: { mood: '', genre: '' },
        input: { topic, creationType, artStyle: mapArtStyle(languageStyle), lengthPreference, languageStyle, rhymeLevel, abstractionLevel },
      });
      setShowResult(true);
    }
    setIsRunning(false);
  };

  const handleRegenerateOnly = async () => {
    if (!pipelineResult || isRegenerating) return;
    setIsRegenerating(true);
    try {
      const regenerated = await remoteRegenerate({
        input: {
          ...(pipelineResult.input || {}),
          useLLM: true,
          lengthPreference,
          languageStyle,
          rhymeLevel,
          abstractionLevel,
        },
        keywords: pipelineResult.keywords || [],
        similarWorks: pipelineResult.similarWorks || [],
        ragResults: pipelineResult.ragResults || [],
        emotion: pipelineResult.emotion || {},
        artStyles: pipelineResult.artStyles || [],
        music: pipelineResult.music || {},
      });
      setPipelineResult(prev => ({ ...prev, ...regenerated }));
    } catch (err) {
      console.error('[仅重新生成] 错误:', err);
    }
    setIsRegenerating(false);
  };

  const getResultText = () => {
    const llm = pipelineResult?.generatedLLM?.content || '';
    const template = pipelineResult?.generated?.content || '';
    return llm || template;
  };

  const handleCopyResult = async () => {
    const text = getResultText();
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopyStatus('已复制');
    setTimeout(() => setCopyStatus(''), 1500);
  };

  const handleSendToPolish = () => {
    const text = getResultText();
    if (!text) return;
    sessionStorage.setItem('musagent:polishDraft', text);
    navigate(ROUTES.polish.path);
  };

  const getEmotionStrengthText = (value = 0) => {
    if (value >= 0.5) return '情绪线索明显';
    if (value >= 0.2) return '情绪线索中等';
    if (value > 0) return '情绪线索较弱';
    return '情绪线索不明显';
  };

  const getKeywordLevel = (score, maxScore) => {
    if (!maxScore) return '低';
    const ratio = score / maxScore;
    if (ratio >= 0.75) return '高';
    if (ratio >= 0.4) return '中';
    return '低';
  };

  const handleApplyTopicFromChat = (nextTopic) => {
    if (!nextTopic) return;
    setTopic(nextTopic);
    setActiveTab('generate');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  useEffect(() => {
    if (!isRunning || completedStages.length > 0) return undefined;
    // v3.0 修复：移除假的 setInterval，改用真实阶段进度
    // 初始 5% 等待后端响应
    setProgress(5);
    setProgressStage('连接后端…');
    return undefined;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isRunning, completedStages.length]);

  const getWriterStatus = () => {
    const method = pipelineResult?.generatedLLM?.method || '';
    if (pipelineResult?.error) return { text: '请求失败', ok: false };
    if (method.includes('DeepSeek') && !method.includes('失败')) return { text: 'AI 深度创作', ok: true };
    if (method.includes('失败')) return { text: 'AI 暂不可用，已用模板辅助', ok: false };
    if (method.includes('未启用')) return { text: '模板辅助模式', ok: false };
    return { text: method || '等待生成', ok: false };
  };

  return (
    <section className="page-inspire page-manuscript min-h-dvh pt-28 md:pt-32 pb-20">
      <div className="container mx-auto px-5 2xl:px-0">
        <PageHeader
          badge="灵感工作台"
          title="灵感生成"
          description="先跑 NLP 流水线与知识库检索，再让 AI 在有依据的上下文里创作——不是普通聊天式生成。"
        />

        <div className="max-w-3xl mx-auto mb-8">
          <MusAgentVsLLM compact />
        </div>

        <div className="page-tabs max-w-md">
          <button type="button" className={activeTab === 'generate' ? 'is-active' : ''} onClick={() => setActiveTab('generate')}>
            ✨ 生成与分析
          </button>
          <button type="button" className={activeTab === 'chat' ? 'is-active' : ''} onClick={() => setActiveTab('chat')}>
            💬 灵感菌对话
          </button>
        </div>

        {activeTab === 'generate' ? (
        <div className="inspire-workbench">
          {/* 左侧输入面板 */}
          <div className="input-panel inspire-input">
            <div className="p-6 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
              <label className="block text-sm font-medium mb-3" style={{ color: 'var(--text-secondary)' }}>创作主题</label>
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder='例如："城市孤独" "黄昏与成长" "雨夜里的自我和解"'
                className="w-full px-4 py-3 rounded-xl text-base focus:outline-none transition-colors"
                style={{
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                }}
              />
            </div>

            <div className="p-6 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
              <label className="block text-sm font-medium mb-3" style={{ color: 'var(--text-secondary)' }}>创作类型</label>
              <div className="flex flex-wrap gap-2">
                {creationTypes.map((t) => (
                  <button key={t} onClick={() => setCreationType(t)}
                    className={`px-4 py-2 rounded-full text-sm transition-colors cursor-pointer ${
                      creationType === t ? 'bg-yellow text-black' : ''
                    }`}
                    style={creationType !== t ? { backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' } : {}}
                  >{t}</button>
                ))}
              </div>
              {(creationType === '散文' || creationType === '短篇片段') && (
                <p className="mt-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                  💡 知识库仅含现代诗与古典诗，相似度检索将自动引用现代诗作为参考语料
                </p>
              )}
            </div>

            <div className="info-banner font-cjk">
              情感与参考诗由系统自动分析。选择文字风格即可，无需手动指定情绪。
            </div>

            <div className="p-6 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
              <label className="block text-sm font-medium mb-1 font-cjk" style={{ color: 'var(--text-secondary)' }}>文字风格</label>
              <p className="text-[11px] mb-3 font-cjk" style={{ color: 'var(--text-muted)' }}>决定语气、节奏与意象密度</p>
              <div className="flex flex-wrap gap-2">
                {languageStyleOptions.map((option) => (
                  <button key={option} onClick={() => setLanguageStyle(option)}
                    className={`px-4 py-2 rounded-full text-sm transition-colors cursor-pointer font-cjk ${languageStyle === option ? 'bg-yellow text-black' : ''}`}
                    style={languageStyle !== option ? { backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' } : {}}
                  >{option}</button>
                ))}
              </div>
            </div>

            <button
              type="button"
              onClick={() => setShowAdvanced(v => !v)}
              className="w-full py-2 text-xs rounded-xl cursor-pointer"
              style={{ color: 'var(--text-muted)', border: '1px dashed var(--border-color)' }}
            >
              {showAdvanced ? '收起生成偏好 ▲' : '展开生成偏好（篇幅 / 押韵 / 抽象）▼'}
            </button>

            {showAdvanced && (
            <div className="p-6 rounded-2xl space-y-4" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
              <label className="block text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>生成偏好</label>
              <div>
                <p className="text-xs mb-2 font-cjk" style={{ color: 'var(--text-muted)' }}>篇幅</p>
                <div className="flex flex-wrap gap-2">
                  {lengthOptions.map((option) => (
                    <button key={option} onClick={() => setLengthPreference(option)}
                      className={`px-3 py-1.5 rounded-full text-xs transition-colors cursor-pointer ${lengthPreference === option ? 'bg-yellow text-black' : ''}`}
                      style={lengthPreference !== option ? { backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' } : {}}
                    >{option}</button>
                  ))}
                </div>
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <p className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>押韵</p>
                  <div className="flex flex-wrap gap-2">
                    {rhymeOptions.map((option) => (
                      <button key={option} onClick={() => setRhymeLevel(option)}
                        className={`px-3 py-1.5 rounded-full text-xs transition-colors cursor-pointer ${rhymeLevel === option ? 'bg-yellow text-black' : ''}`}
                        style={rhymeLevel !== option ? { backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' } : {}}
                      >{option}</button>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>抽象程度</p>
                  <div className="flex flex-wrap gap-2">
                    {abstractionOptions.map((option) => (
                      <button key={option} onClick={() => setAbstractionLevel(option)}
                        className={`px-3 py-1.5 rounded-full text-xs transition-colors cursor-pointer ${abstractionLevel === option ? 'bg-yellow text-black' : ''}`}
                        style={abstractionLevel !== option ? { backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' } : {}}
                      >{option}</button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
            )}

            <label className="flex items-center gap-2 px-4 py-3 rounded-xl cursor-pointer font-cjk text-xs" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
              <input type="checkbox" checked={fastMode} onChange={(e) => setFastMode(e.target.checked)} className="accent-yellow" />
              快速模式（BM25 检索、跳过图谱，约快 40%）
            </label>

            <button onClick={handleGenerate} disabled={isRunning}
              className="w-full py-4 rounded-xl bg-yellow text-black font-semibold text-lg hover:opacity-80 transition-opacity cursor-pointer disabled:opacity-50 font-cjk">
              {isRunning ? '⏳ 正在创作中…' : '✨ 生成灵感'}
            </button>
          </div>

          {/* 右侧结果面板 */}
          <div className="result-panel inspire-output">
            {/* 生成进度 */}
            {isRunning && (
              <div className="pipeline-progress pipeline-progress-compact">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs font-cjk" style={{ color: 'var(--text-secondary)' }}>
                    {progressStage || '正在处理…'}
                  </p>
                  <p className="text-xs tabular-nums" style={{ color: 'var(--text-muted)' }}>
                    {progress}%
                  </p>
                </div>
                <div className="pipeline-progress-bar">
                  <div className="pipeline-progress-fill" style={{ width: `${progress}%` }} />
                </div>
                {completedStages.length > 0 && (
                  <div className="pipeline-stage-chips mt-2 flex flex-wrap gap-1">
                    {completedStages.map((sid) => (
                      <span key={sid} className="pipeline-stage-chip font-cjk">
                        {PIPELINE_STAGE_LABELS[sid] || sid}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {!isRunning && !showResult && (
              <div className="inspire-empty-state">
                <div className="inspire-empty-inner">
                  <span className="inspire-empty-icon">✨</span>
                  <p className="font-cjk text-base" style={{ color: 'var(--text-secondary)' }}>作品将在这里呈现</p>
                  <p className="font-cjk text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
                    填写左侧主题与风格，点击「生成灵感」
                  </p>
                  <ul className="inspire-empty-steps font-cjk">
                    <li>自动分析情感与关键词</li>
                    <li>检索知识库参考诗</li>
                    <li>AI 生成 + 质量评估</li>
                  </ul>
                </div>
              </div>
            )}

            {showResult && agentLog.length > 0 && !isRunning && (
              <button
                type="button"
                onClick={() => setShowAgentDetail(v => !v)}
                className="w-full px-4 py-2 rounded-xl text-xs font-cjk transition-colors"
                style={{ backgroundColor: 'var(--bg-card)', color: 'var(--text-muted)', border: '1px solid var(--border-color)' }}
              >
                {showAgentDetail ? '收起处理详情 ▲' : '查看处理详情 ▼'}
              </button>
            )}

            {showAgentDetail && showResult && (
              <div className="p-4 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                <div className="grid grid-cols-3 sm:grid-cols-5 gap-1.5">
                  {agentLog.map((a) => (
                    <div key={a.id} className="text-center p-1.5 rounded-lg text-[10px] font-cjk bg-green-500/10 text-green-400">
                      <span className="block text-sm">{a.icon}</span>
                      {a.label}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {showResult && pipelineResult ? (
              <div className="inspire-result-stack">
                {/* ★ v3.0 拆出：你的作品 + Critic Agent 评审 → GenerationResultCard */}
                <GenerationResultCard
                  pipelineResult={pipelineResult}
                  getResultText={getResultText}
                  copyStatus={copyStatus}
                  onCopy={handleCopyResult}
                />

                {/* 创作解释层 — 主题子图 */}
                <TopicGraphPanel graph={pipelineResult.knowledgeGraph} topic={topic} />

                {/* 评价闭环 */}
                {!reviewDone ? (
                  <PostGenerationReview
                    topic={topic}
                    contentPreview={getResultText()}
                    quality={pipelineResult.quality}
                    onPolish={handleSendToPolish}
                    onRegenerate={handleRegenerateOnly}
                    onComplete={() => setReviewDone(true)}
                    onSkip={() => setReviewDone(true)}
                  />
                ) : (
                  <div className="flex flex-wrap justify-center gap-2">
                    <button onClick={handleRegenerateOnly} disabled={isRegenerating}
                      className="px-4 py-2 rounded-full text-xs transition-colors disabled:opacity-50"
                      style={{ backgroundColor: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-color)' }}>
                      {isRegenerating ? '生成中...' : '再生成一版'}
                    </button>
                    <button onClick={handleGenerate} disabled={isRunning}
                      className="px-4 py-2 rounded-full text-xs transition-colors disabled:opacity-50"
                      style={{ backgroundColor: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-color)' }}>
                      重新分析
                    </button>
                    <button onClick={handleSendToPolish}
                      className="px-4 py-2 rounded-full text-xs bg-yellow text-black transition-opacity hover:opacity-80">
                      去润色
                    </button>
                  </div>
                )}

                <button
                  onClick={() => setShowAnalysisDetail(v => !v)}
                  className="w-full px-4 py-2 rounded-full text-xs transition-colors"
                  style={{ backgroundColor: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }}
                >
                  {showAnalysisDetail ? '收起创作分析' : '查看创作分析（关键词 / 情感 / 参考诗）'}
                </button>

                {showAnalysisDetail && (
                <div className="inspire-analysis-panel">
                {/* 用户意图 — 移入分析详情 */}
                <div className="p-4 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                  <h3 className="text-xs font-medium mb-2 font-cjk" style={{ color: 'var(--text-muted)' }}>创作意图</h3>
                  <p className="text-base font-cjk text-yellow">{pipelineResult.intent?.intent || '诗歌创作'}</p>
                </div>

                {/* WriterAgent 状态 — 移入分析详情 */}
                <div className="p-4 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                  <h3 className="text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>生成引擎</h3>
                  {(() => {
                    const st = getWriterStatus();
                    return (
                      <p className="text-sm font-medium" style={{ color: st.ok ? '#86efac' : 'var(--text-secondary)' }}>
                        {st.text}
                      </p>
                    );
                  })()}
                </div>

                {/* 主题理解 */}
                {pipelineResult.queryExpansion && (
                  <div className="p-4 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                    <h3 className="text-xs font-medium mb-3" style={{ color: 'var(--text-muted)' }}>🧭 主题理解</h3>
                    <div className="space-y-3">
                      <div>
                        <p className="text-[10px] mb-1.5" style={{ color: 'var(--text-muted)' }}>核心关键词</p>
                        <div className="flex flex-wrap gap-1.5">
                          {(pipelineResult.queryExpansion.core || []).length > 0 ? (
                            pipelineResult.queryExpansion.core.map((term) => (
                              <span key={term} className="px-2 py-1 rounded-full text-xs bg-yellow text-black">
                                {term}
                              </span>
                            ))
                          ) : (
                            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>未识别到明确核心词</span>
                          )}
                        </div>
                      </div>
                      <div>
                        <p className="text-[10px] mb-1.5" style={{ color: 'var(--text-muted)' }}>联想意象</p>
                        <div className="flex flex-wrap gap-1.5">
                          {(pipelineResult.queryExpansion.imagery || []).length > 0 ? (
                            pipelineResult.queryExpansion.imagery.map((term) => (
                              <span key={term} className="px-2 py-0.5 rounded-full text-[10px]"
                                style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
                                #{term}
                              </span>
                            ))
                          ) : (
                            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>暂无扩展意象</span>
                          )}
                        </div>
                      </div>
                      {pipelineResult.entities?.flat?.length > 0 && (
                        <div>
                          <p className="text-[10px] mb-1.5" style={{ color: 'var(--text-muted)' }}>
                            命名实体 / 意象词
                            {pipelineResult.entities.method && ` · ${pipelineResult.entities.method}`}
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {pipelineResult.entities.flat.slice(0, 10).map((ent) => (
                              <span key={`${ent.type}-${ent.text}`} className="px-2 py-0.5 rounded-full text-[10px]"
                                style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
                                {ent.text} · {ent.type}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* 关键词 */}
                <div className="p-4 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                  <h3 className="text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>🔑 关键词重要度</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {(() => {
                      const keywords = pipelineResult.keywords || [];
                      const maxScore = Math.max(...keywords.map((kw) => kw.tfidf || 0), 0);
                      return keywords.map((kw) => {
                        const level = getKeywordLevel(kw.tfidf || 0, maxScore);
                        return (
                          <span key={kw.keyword} className="px-2 py-1 rounded-full text-xs bg-yellow text-black">
                            {kw.keyword} <span className="opacity-60">{level}</span>
                          </span>
                        );
                      });
                    })()}
                  </div>
                </div>

                {/* 情感 — 词典 + RoBERTa 融合 */}
                <div className="p-4 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                  <h3 className="text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>💭 融合情感分析</h3>
                  <p className="text-sm mb-2">
                    融合主导：<span className="font-bold text-yellow">{pipelineResult.emotion.dominant}</span>
                    <span className="ml-2 text-xs" style={{ color: 'var(--text-muted)' }}>{getEmotionStrengthText(pipelineResult.emotion.intensity)}</span>
                  </p>
                  {pipelineResult.emotion.fusionMethod && (
                    <p className="text-[10px] mb-2" style={{ color: 'var(--text-muted)' }}>{pipelineResult.emotion.fusionMethod}</p>
                  )}
                  <div className="grid sm:grid-cols-2 gap-3 mb-3 text-[10px]">
                    <div className="p-2 rounded-lg" style={{ backgroundColor: 'var(--bg-secondary)' }}>
                      <p style={{ color: 'var(--text-muted)' }}>词典法</p>
                      <p className="text-yellow">{pipelineResult.emotion.dictionary?.dominant || '-'}</p>
                    </div>
                    <div className="p-2 rounded-lg" style={{ backgroundColor: 'var(--bg-secondary)' }}>
                      <p style={{ color: 'var(--text-muted)' }}>RoBERTa</p>
                      <p className="text-yellow">
                        {pipelineResult.emotion.transformer?.dominant || '-'}
                        {pipelineResult.emotion.transformer?.polarity != null && (
                          <span className="ml-1 opacity-70">({pipelineResult.emotion.transformer.polarity})</span>
                        )}
                      </p>
                    </div>
                  </div>
                  <div className="space-y-1">
                    {Object.entries(pipelineResult.emotion.scores).filter(([,v]) => v > 0).map(([k, v]) => (
                      <div key={k} className="flex items-center gap-2">
                        <span className="w-10 text-xs" style={{ color: 'var(--text-muted)' }}>{k}</span>
                        <div className="flex-1 h-1.5 rounded-full" style={{ backgroundColor: 'var(--bg-secondary)' }}>
                          <div className="h-1.5 rounded-full bg-yellow" style={{ width: `${v * 100}%` }}></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 摘要 */}
                <div className="p-4 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                  <h3 className="text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>📋 TextRank 摘要</h3>
                  <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{pipelineResult.summary}</p>
                </div>

                {/* 生成内容 — 双结果对比 + 化用标注 */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* 算法模板 */}
                  <div className="p-3 rounded-2xl border border-white/20" style={{ backgroundColor: 'var(--bg-card)' }}>
                    <p className="text-[10px] mb-2 px-2 py-0.5 rounded-full inline-block"
                      style={{ backgroundColor: 'rgba(255,255,255,0.1)', color: 'var(--text-secondary)' }}>
                      ⚙️ {pipelineResult.generated?.method || '算法模板'}
                    </p>
                    <pre className="text-xs leading-relaxed font-serif whitespace-pre-wrap" style={{ color: 'var(--text-primary)' }}>
                      {pipelineResult.generated?.content || ''}
                    </pre>
                    {(pipelineResult.generated?.citations || []).length > 0 && (
                      <div className="mt-3 pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
                        <p className="text-[10px] mb-1" style={{ color: 'var(--text-muted)' }}>📎 化用来源</p>
                        {pipelineResult.generated.citations.slice(0, 2).map((c) => (
                          <p key={c.source} className="text-[10px] mb-1" style={{ color: 'var(--text-secondary)' }}>
                            <span className="text-yellow">{c.source}</span> — {c.detail}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                  {/* DeepSeek LLM */}
                  <div className="p-3 rounded-2xl border border-yellow/30" style={{ backgroundColor: 'var(--bg-card)' }}>
                    <p className="text-[10px] mb-2 px-2 py-0.5 rounded-full inline-block"
                      style={{ backgroundColor: 'rgba(231,211,147,0.15)', color: 'var(--text-secondary)' }}>
                      🤖 {pipelineResult.generatedLLM?.method || 'LLM 生成'}
                    </p>
                    <pre className="text-xs leading-relaxed font-serif whitespace-pre-wrap" style={{ color: 'var(--text-primary)' }}>
                      {pipelineResult.generatedLLM?.content || '生成中...'}
                    </pre>
                    {(pipelineResult.generatedLLM?.citations || pipelineResult.citations || []).length > 0 && (
                      <div className="mt-3 pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
                        <p className="text-[10px] mb-1" style={{ color: 'var(--text-muted)' }}>📎 化用来源</p>
                        {(pipelineResult.generatedLLM?.citations || pipelineResult.citations).slice(0, 2).map((c) => (
                          <p key={c.source} className="text-[10px] mb-1" style={{ color: 'var(--text-secondary)' }}>
                            <span className="text-yellow">{c.source}</span> — {c.detail}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* 语义洞察 — 为什么推荐这些作品 */}
                {pipelineResult.semanticInsight?.insight && (
                  <div className="p-4 rounded-2xl" style={{ backgroundColor: 'rgba(231,211,147,0.08)', border: '1px solid rgba(231,211,147,0.25)' }}>
                    <h3 className="text-xs font-medium mb-2 text-yellow">💡 语义关联说明</h3>
                    <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                      {pipelineResult.semanticInsight.insight}
                    </p>
                    {(pipelineResult.semanticInsight.sharedImagery?.length > 0 || pipelineResult.semanticInsight.matchedKeywords?.length > 0) && (
                      <div className="flex flex-wrap gap-2 mt-3">
                        {pipelineResult.semanticInsight.matchedKeywords?.map((k) => (
                          <span key={`m-${k}`} className="px-2 py-0.5 rounded-full text-[10px]" style={{ backgroundColor: 'var(--bg-card)', color: 'var(--text-secondary)' }}>
                            命中 {k}
                          </span>
                        ))}
                        {pipelineResult.semanticInsight.sharedImagery?.map((k) => (
                          <span key={`s-${k}`} className="px-2 py-0.5 rounded-full text-[10px]" style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-muted)' }}>
                            意象 {k}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Pipeline 阶段耗时 */}
                {pipelineResult.pipeline?.stages?.length > 0 && (
                  <div className="p-4 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                    <h3 className="text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>
                      ⚡ Pipeline 编排 · v{pipelineResult.pipeline.version || '3.0'}
                      <span className="ml-2 opacity-70">总计 {pipelineResult.pipeline.totalDurationMs}ms</span>
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {pipelineResult.pipeline.stages.map((s) => (
                        <span
                          key={s.id}
                          className="px-2 py-1 rounded-lg text-[10px]"
                          style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}
                          title={s.model}
                        >
                          {s.name} {s.durationMs}ms
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* 混合检索 + Cross-Encoder 精排 */}
                <div className="p-4 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                  <h3 className="text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>
                    🔍 混合检索 — BM25 + BGE + Cross-Encoder
                    {pipelineResult.retrievalMethod && <span className="ml-1 opacity-70">({pipelineResult.retrievalMethod})</span>}
                  </h3>
                  <div className="space-y-2">
                    {(pipelineResult.similarWorks || []).slice(0, 3).map((w, i) => (
                      <div key={i} className="text-xs space-y-1 p-2 rounded-lg" style={{ backgroundColor: 'var(--bg-secondary)' }}>
                        <div className="flex justify-between items-center gap-2">
                          <span style={{ color: 'var(--text-primary)' }}>[{w.type}] {w.title}</span>
                          <span className="text-yellow shrink-0">
                            {w.rerankScore != null ? `重排 ${w.rerankScore.toFixed(3)}` : `混合 ${(w.hybridScore ?? w.similarity ?? 0).toFixed(3)}`}
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-2 text-[10px]" style={{ color: 'var(--text-muted)' }}>
                          <span>BM25 {(w.bm25Score ?? 0).toFixed(3)}</span>
                          <span>BGE {(w.semanticScore ?? 0).toFixed(3)}</span>
                          {w.rerankScore != null && <span>Cross-Encoder {w.rerankScore.toFixed(3)}</span>}
                        </div>
                        {(w.matchedTerms || []).length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            <span style={{ color: 'var(--text-muted)' }}>BM25命中：</span>
                            {w.matchedTerms.slice(0, 5).map((term) => (
                              <span key={term} className="px-1.5 py-0.5 rounded-full text-[10px]" style={{ backgroundColor: 'var(--bg-card)', color: 'var(--text-secondary)' }}>
                                {term}
                              </span>
                            ))}
                          </div>
                        )}
                        {w.semanticExplanation?.summary && (
                          <p className="text-[10px] leading-relaxed pt-1" style={{ color: 'var(--text-secondary)' }}>
                            {w.semanticExplanation.summary}
                          </p>
                        )}
                        {w.semanticExplanation?.adaptablePhrase && (
                          <p className="text-[10px] italic" style={{ color: 'var(--text-muted)' }}>
                            可化用：「{w.semanticExplanation.adaptablePhrase}」
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                  <p className="text-[10px] mt-2" style={{ color: 'var(--text-muted)' }}>
                    先 BM25 + BGE 混合召回，再由 bge-reranker Cross-Encoder 精排；分数为相对排序值，非百分比。
                  </p>
                </div>

                {/* RAG 知识 */}
                <div className="p-4 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                  <h3 className="text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>📚 RAG 知识依据（注入生成）</h3>
                  {(pipelineResult.ragResults || []).map((r, i) => (
                    <div key={i} className="text-xs mb-3 p-2 rounded-lg" style={{ backgroundColor: 'var(--bg-secondary)' }}>
                      <p style={{ color: 'var(--text-primary)' }}>
                        <span className="text-yellow">[{r.topic}]</span> · {formatAuthor(r.author)} · {r.emotion}
                      </p>
                      {r.semanticSummary && (
                        <p className="mt-1 text-[10px]" style={{ color: 'var(--text-muted)' }}>{r.semanticSummary}</p>
                      )}
                      <p className="mt-1" style={{ color: 'var(--text-secondary)' }}>{r.excerpt}...</p>
                      {r.adaptablePhrase && (
                        <p className="mt-1 text-[10px] text-yellow">→ 化用片段：「{r.adaptablePhrase}」</p>
                      )}
                    </div>
                  ))}
                </div>
                </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
        ) : (
        <InspirationChatPanel onApplyTopic={handleApplyTopicFromChat} />
        )}
      </div>
    </section>
  )
}

export default InspirePage
