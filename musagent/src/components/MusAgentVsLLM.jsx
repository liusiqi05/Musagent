import { Link } from 'react-router-dom';
import { ROUTES } from '../config/routes.js';

const DIFF_ROWS = [
  { label: '知识来源', llm: '模型训练语料（黑盒）', mus: '5320 首诗词库 + 可解释检索' },
  { label: '创作依据', llm: '纯文本 Prompt', mus: 'RAG 注入 + 化用标注 + 参考诗片段' },
  { label: '情感分析', llm: '对话中隐式推断', mus: '词典 + RoBERTa 融合，可查看分数' },
  { label: '质量保障', llm: '无内置评估', mus: '多维质量打分 + 用户反馈回流' },
  { label: '关系理解', llm: '无结构化图谱', mus: '知识图谱 + 力导向可视化' },
  { label: '长文本', llm: '通用续写', mus: '篇幅档位（含超长）+ 分节散文/短篇' },
  { label: '速度策略', llm: '单次调用', mus: '快速模式 / 完整 Pipeline 可选' },
];

const MusAgentVsLLM = ({ compact = false }) => (
  <section className={`musagent-diff ${compact ? 'is-compact' : ''}`}>
    <div className="musagent-diff-head">
      <h2 className="font-cjk">{compact ? '和普通聊天 AI 有何不同？' : 'MusAgent ≠ 普通 LLM'}</h2>
      <p className="font-cjk">
        不是「把主题丢给大模型」。先跑 NLP 流水线、检索知识库、构建图谱，再让 LLM 在<strong className="text-yellow">有依据</strong>的上下文里创作。
      </p>
    </div>
    <div className="musagent-diff-table">
      <div className="musagent-diff-row musagent-diff-header font-cjk">
        <span>维度</span>
        <span>普通 LLM</span>
        <span>MusAgent</span>
      </div>
      {DIFF_ROWS.map((row) => (
        <div key={row.label} className="musagent-diff-row font-cjk">
          <span className="musagent-diff-label">{row.label}</span>
          <span className="musagent-diff-llm">{row.llm}</span>
          <span className="musagent-diff-mus">{row.mus}</span>
        </div>
      ))}
    </div>
    {!compact && (
      <div className="musagent-diff-cta">
        <Link to={ROUTES.inspire.path} className="px-5 py-2.5 rounded-full bg-yellow text-black text-sm font-cjk font-medium">
          体验完整流水线
        </Link>
        <Link to={ROUTES.knowledgeGraph.path} className="px-5 py-2.5 rounded-full text-sm font-cjk border" style={{ borderColor: 'var(--border-color)', color: 'var(--text-secondary)' }}>
          查看关系图谱
        </Link>
      </div>
    )}
  </section>
);

export default MusAgentVsLLM;
