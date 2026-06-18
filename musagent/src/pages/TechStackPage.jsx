import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../components/PageHeader.jsx';
import { fetchStack, fetchHealth } from '../nlp/api.js';
import { ROUTES } from '../config/routes.js';

const ModelCard = ({ title, model, library, loaded, extra }) => (
  <div
    className="p-5 rounded-2xl"
    style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}
  >
    <div className="flex items-start justify-between gap-3 mb-3">
      <h3 className="text-sm font-medium text-yellow">{title}</h3>
      <span
        className="text-[10px] px-2 py-0.5 rounded-full shrink-0"
        style={{
          backgroundColor: loaded ? 'rgba(34,197,94,0.15)' : 'rgba(148,163,184,0.15)',
          color: loaded ? '#86efac' : 'var(--text-muted)',
        }}
      >
        {loaded ? '已加载' : '按需加载'}
      </span>
    </div>
    <p className="text-xs font-mono mb-1" style={{ color: 'var(--text-primary)' }}>{model || library}</p>
    {model && library && (
      <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{library}</p>
    )}
    {extra && <p className="text-[10px] mt-2" style={{ color: 'var(--text-secondary)' }}>{extra}</p>}
  </div>
);

const TechStackPage = () => {
  const [stack, setStack] = useState(null);
  const [health, setHealth] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [s, h] = await Promise.all([fetchStack(), fetchHealth()]);
        if (!cancelled) {
          setStack(s);
          setHealth(h);
        }
      } catch (e) {
        if (!cancelled) setError(e.message || '无法获取技术栈信息');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <section className="page-stack page-manuscript min-h-dvh pt-28 md:pt-32 pb-20">
      <div className="container mx-auto px-5 2xl:px-0 max-w-5xl">
        <PageHeader
          badge="Transformer-RAG"
          title="技术架构"
          description="预训练模型 + 经典 NLP + 混合检索 + RAG + LLM。答辩可直接展示本页与灵感生成页的 Pipeline 耗时。"
        />

        {loading && (
          <div className="text-center py-20" style={{ color: 'var(--text-muted)' }}>正在读取模型栈...</div>
        )}

        {error && (
          <div className="p-4 rounded-2xl mb-8 text-sm" style={{ backgroundColor: 'rgba(239,68,68,0.12)', color: '#fecaca' }}>
            {error} — 请确认后端已启动（uvicorn main:app --port 8000）。
          </div>
        )}

        {stack && (
          <div className="space-y-8">
            <div className="p-5 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
              <p className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>架构层级</p>
              <p className="text-lg font-bold text-yellow mb-2">{stack.tier}</p>
              <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{stack.architecture}</p>
              {health?.llmConfigured === false && (
                <p className="text-xs mt-3" style={{ color: 'var(--text-muted)' }}>
                  DeepSeek 未配置 API Key，LLM 生成将降级为算法模板。
                </p>
              )}
            </div>

            <div className="p-5 rounded-2xl font-mono text-xs overflow-x-auto" style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
              <pre className="whitespace-pre-wrap">{`用户输入
    ↓
[Jieba 分词] → [BERT-NER + 意象词]
    ↓
[查询扩展] → [TF-IDF 关键词] → [TextRank 摘要]
    ↓
[BM25 稀疏召回] + [BGE-small-zh 稠密召回] → 分数融合
    ↓
[bge-reranker Cross-Encoder 精排 Top-K]
    ↓
[文学词典 + RoBERTa 融合情感]
    ↓
[RAG 结构化上下文] → [DeepSeek / 模板生成]`}</pre>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <ModelCard title="向量嵌入" {...stack.embedding} />
              <ModelCard title="Cross-Encoder 重排" {...stack.reranker} />
              <ModelCard title="情感分析" {...stack.sentiment} />
              <ModelCard title="命名实体" {...stack.ner} />
              <ModelCard
                title="文本校错"
                model={stack.correction?.library}
                library=""
                loaded={stack.correction?.loaded}
              />
              <ModelCard
                title="大语言模型"
                model={stack.llm?.model}
                library={stack.llm?.library}
                loaded={health?.llmConfigured}
                extra="OpenAI 兼容 API，可选启用"
              />
            </div>

            {stack.classicNlp?.length > 0 && (
              <div className="p-5 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                <h2 className="text-sm font-medium mb-3 text-yellow">经典 NLP 组件</h2>
                <div className="flex flex-wrap gap-2">
                  {stack.classicNlp.map((item) => (
                    <span
                      key={item}
                      className="px-3 py-1 rounded-full text-xs"
                      style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {health?.semanticIndex && (
              <div className="p-5 rounded-2xl" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                <h2 className="text-sm font-medium mb-3 text-yellow">语义索引</h2>
                <div className="grid sm:grid-cols-3 gap-4 text-xs" style={{ color: 'var(--text-secondary)' }}>
                  <div>
                    <p style={{ color: 'var(--text-muted)' }}>文档数</p>
                    <p className="text-lg text-yellow">{health.semanticIndex.docCount ?? '-'}</p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-muted)' }}>向量维度</p>
                    <p className="text-lg text-yellow">{health.semanticIndex.dim ?? '-'}</p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-muted)' }}>模型</p>
                    <p className="text-sm">{health.semanticIndex.model ?? stack.embedding?.model}</p>
                  </div>
                </div>
              </div>
            )}

            <div className="info-banner">
              在 <Link to={ROUTES.inspire.path} className="text-yellow">灵感生成</Link> 运行一次 Pipeline 后，
              可查看各阶段耗时与重排分数；在 <Link to={ROUTES.evaluate.path} className="text-yellow">技术评测</Link> 查看定量指标。
            </div>
          </div>
        )}
      </div>
    </section>
  );
};

export default TechStackPage;
