import { Link } from 'react-router-dom'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { agentSteps } from '../data/mockData.js'
import PageHeader from '../components/PageHeader.jsx'
import { ROUTES } from '../config/routes.js'

const AboutPage = () => {
  useGSAP(() => {
    gsap.from('.page-about h1', { yPercent: 100, duration: 1.2, ease: 'expo.out' });
    gsap.from('.agent-desc', { opacity: 0, y: 40, duration: 1, ease: 'power2.out', delay: 0.3 });
    gsap.from('.agent-card', { y: 40, duration: 0.6, ease: 'power2.out', stagger: 0.1, delay: 0.5 });
  }, [])

  return (
    <section className="page-about page-manuscript min-h-dvh pt-28 md:pt-32 pb-20">
      <div className="container mx-auto px-5 2xl:px-0">
        <PageHeader
          badge="系统架构"
          title="NLP 流水线"
          description="MusAgent 将 NLP 能力拆分为模块化 Agent 展示。后端为顺序执行的 Pipeline，非独立自治 Agent 调度系统。"
        />

        <div className="info-banner max-w-3xl mx-auto mb-12">
          答辩说明：各 Agent 对应后端一个处理步骤（分词 → 检索 → RAG → 生成）。
          可在 <Link to={ROUTES.inspire.path} className="text-yellow">灵感生成</Link> 页查看真实输入输出，
          在 <Link to={ROUTES.stack.path} className="text-yellow">技术架构</Link> 页查看预训练模型栈，
          或在 <Link to={ROUTES.evaluate.path} className="text-yellow">技术评测</Link> 页查看定量指标。
        </div>

        <div className="flex flex-wrap justify-center items-center gap-2 md:gap-3 mb-16 max-w-6xl mx-auto">
          {agentSteps.map((step, i) => (
            <div key={step.id} className="flex items-center gap-2 md:gap-3">
              <div className={`px-3 py-2 md:px-4 md:py-3 rounded-xl text-center transition-all min-w-[80px] md:min-w-[100px] ${
                'ring-1 ring-yellow/20'
              }`}
                style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}
              >
                <span className="text-lg md:text-xl block">{step.icon}</span>
                <span className="text-[10px] md:text-xs font-medium block mt-1" style={{ color: 'var(--text-primary)' }}>
                  {step.label}
                </span>
                <span className="text-[9px] md:text-[10px] block mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  Step {i + 1}
                </span>
              </div>
              {i < agentSteps.length - 1 && (
                <span className="text-yellow text-lg md:text-xl">→</span>
              )}
            </div>
          ))}
        </div>

        {/* 详细 Agent 卡片 */}
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {agentSteps.map((step) => (
            <div
              key={step.id}
              className="agent-card p-6 rounded-2xl transition-colors"
              style={{
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-color)'
              }}
            >
              <div className="flex items-center gap-3 mb-4">
                <span className="text-2xl">{step.icon}</span>
                <div>
                  <h3 className="font-modern-negra text-lg">{step.label}</h3>
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{step.name}</p>
                </div>
              </div>
              <p className="text-sm mb-4" style={{ color: 'var(--text-primary)' }}>{step.description}</p>
              <div className="space-y-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
                <div className="flex justify-between">
                  <span>输入：</span>
                  <span>{step.input}</span>
                </div>
                <div className="flex justify-between">
                  <span>输出：</span>
                  <span className="text-yellow">{step.output}</span>
                </div>
              </div>
              <p className="mt-4 text-xs italic leading-relaxed" style={{ color: 'var(--text-muted)', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
                {step.detail}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default AboutPage
