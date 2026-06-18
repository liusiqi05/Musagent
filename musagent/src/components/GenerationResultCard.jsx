import { useState } from 'react';

/**
 * GenerationResultCard — 灵感生成结果展示卡
 * v3.0 整合：你的作品 + Critic Agent 评审 + 复制按钮
 *
 * Props:
 *   - pipelineResult: 后端返回的完整 pipeline 结果
 *   - getResultText: () => string — 取 LLM 或模板文本
 *   - copyStatus: string — 复制按钮状态文字
 *   - onCopy: () => void — 复制按钮回调
 *   - onRegenerate: () => void — 仅重新生成按钮回调
 *   - onPolish: () => void — 去润色按钮回调
 */
const GenerationResultCard = ({
  pipelineResult,
  getResultText,
  copyStatus,
  onCopy,
}) => {
  const [showCritic, setShowCritic] = useState(true);
  if (!pipelineResult) return null;

  const quality = pipelineResult.quality?.overall;
  const method = pipelineResult.generatedLLM?.method || pipelineResult.generated?.method || '';
  const isLLM = method.includes('DeepSeek') && !method.includes('失败');

  return (
    <div className="p-4 rounded-2xl border border-yellow/30" style={{ backgroundColor: 'var(--bg-card)' }}>
      {/* 头部：标题 + 质量标签 + 引擎类型 */}
      <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
        <h3 className="text-sm font-medium text-yellow">你的作品</h3>
        <div className="flex items-center gap-2 flex-wrap">
          {quality && (
            <span className={`quality-badge ${quality.passed ? 'is-pass' : 'is-warn'}`}>
              {quality.label}
            </span>
          )}
          <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
            {isLLM ? 'DeepSeek 生成' : '模板生成'}
          </span>
        </div>
      </div>

      {/* 作品正文 */}
      <pre className="text-sm leading-relaxed font-cjk whitespace-pre-wrap" style={{ color: 'var(--text-primary)' }}>
        {getResultText() || '暂无生成内容'}
      </pre>
      <button onClick={onCopy} className="mt-3 text-[10px] text-yellow hover:underline">
        {copyStatus || '复制全文'}
      </button>

      {/* ★ Critic Agent 评审块 — v3.0 新增 */}
      {pipelineResult.critic && (
        <div
          className="mt-4 p-3 rounded-xl"
          style={{
            backgroundColor: pipelineResult.critic.triggered ? 'rgba(134,239,172,0.08)' : 'rgba(231,211,147,0.06)',
            border: `1px solid ${pipelineResult.critic.triggered ? 'rgba(134,239,172,0.3)' : 'rgba(231,211,147,0.25)'}`,
          }}
        >
          <button
            type="button"
            onClick={() => setShowCritic(v => !v)}
            className="w-full flex items-center justify-between gap-2"
          >
            <span className="text-sm font-medium flex items-center gap-2">
              <span>🧐</span>
              <span className="text-yellow">Critic Agent 自评</span>
              {pipelineResult.critic.triggered && (
                <span className="text-[10px] px-2 py-0.5 rounded-full"
                  style={{ backgroundColor: 'rgba(134,239,172,0.2)', color: '#86efac' }}>
                  ✦ 已重写
                </span>
              )}
            </span>
            <span className="flex items-center gap-2 text-[10px]" style={{ color: 'var(--text-muted)' }}>
              <span className="text-lg font-bold text-yellow">
                {pipelineResult.critic.score ?? 0}
              </span>
              <span>/10</span>
              <span className="ml-1 opacity-60">{showCritic ? '▲' : '▼'}</span>
            </span>
          </button>

          {showCritic && (
            <div className="mt-2 space-y-2">
              <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                {pipelineResult.critic.method === 'llm' ? '🤖 LLM 评审' :
                  pipelineResult.critic.method === 'rule' || pipelineResult.critic.method === 'rule-based' ? '📏 规则评审' :
                  pipelineResult.critic.method === 'rule-fallback' ? '🤖→📏 LLM 降级' : '⏭ 已跳过'}
                {pipelineResult.critic.model && ` · ${pipelineResult.critic.model}`}
              </div>

              {pipelineResult.critic.originalScore != null && (
                <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                  重写前 {pipelineResult.critic.originalScore} → 重写后 {pipelineResult.critic.score}
                </p>
              )}

              {(pipelineResult.critic.issues || []).length > 0 && (
                <div>
                  <p className="text-[10px] mb-1" style={{ color: 'var(--text-muted)' }}>问题</p>
                  <ul className="space-y-0.5">
                    {pipelineResult.critic.issues.map((issue, i) => (
                      <li key={i} className="text-xs font-cjk flex gap-1.5" style={{ color: 'var(--text-secondary)' }}>
                        <span style={{ color: '#fca5a5' }}>·</span>{issue}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {(pipelineResult.critic.suggestions || []).length > 0 && (
                <div>
                  <p className="text-[10px] mb-1" style={{ color: 'var(--text-muted)' }}>建议</p>
                  <ul className="space-y-0.5">
                    {pipelineResult.critic.suggestions.map((s, i) => (
                      <li key={i} className="text-xs font-cjk flex gap-1.5" style={{ color: 'var(--text-secondary)' }}>
                        <span className="text-yellow">►</span>{s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {pipelineResult.critic.retryError && (
                <p className="text-[10px] text-red-300">
                  重写异常：{pipelineResult.critic.retryError}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default GenerationResultCard;
