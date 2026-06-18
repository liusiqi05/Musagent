import { Link } from 'react-router-dom';
import { ROUTES } from '../config/routes.js';

const STEPS = [
  {
    num: '01',
    title: '输入主题，生成作品',
    desc: '选择体裁与风格，系统自动分析情感、检索参考诗，生成属于你的文字。',
    path: ROUTES.inspire.path,
    cta: '开始创作',
  },
  {
    num: '02',
    title: '浏览知识库，寻找灵感',
    desc: '5320 首诗词可按情感、关键词或语义检索，为你的创作提供参考与化用素材。',
    path: ROUTES.library.path,
    cta: '探索知识库',
  },
  {
    num: '03',
    title: '润色改写，定稿发布',
    desc: '对已有文本进行文学化改写，保留原意的同时提升表达质感与画面感。',
    path: ROUTES.polish.path,
    cta: '进入润色',
  },
];

const CreatorSteps = () => (
  <section className="creator-steps">
    <div className="container mx-auto max-w-5xl">
      <h2 className="font-cjk text-2xl md:text-3xl text-center mb-3">三步完成创作</h2>
      <p className="text-center text-sm mb-10 max-w-md mx-auto" style={{ color: 'var(--text-muted)' }}>
        从灵感到成稿，MusAgent 为你串联完整的创作路径
      </p>
      <div className="creator-steps-grid">
        {STEPS.map((step) => (
          <Link key={step.num} to={step.path} className="creator-step-card block group">
            <p className="creator-step-num">{step.num}</p>
            <h3 className="creator-step-title group-hover:text-yellow transition-colors">{step.title}</h3>
            <p className="creator-step-desc">{step.desc}</p>
            <span className="inline-block mt-4 text-xs text-yellow opacity-80 group-hover:opacity-100">
              {step.cta} →
            </span>
          </Link>
        ))}
      </div>
    </div>
  </section>
);

export default CreatorSteps;
