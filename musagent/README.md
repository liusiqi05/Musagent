# MusAgent — 前端

> 本目录是 MusAgent 项目的 **前端代码**（React 19 + Vite 6 + Tailwind 4 + GSAP）。
>
> 完整项目说明、API、技术栈、启动方法见仓库根目录的 [`README.md`](../README.md) 与 [`PROJECT.md`](../PROJECT.md)。

## 本地开发

```bash
# 假设后端已启动在 :8000
npm install
npm run dev
# → http://localhost:5173
```

## 路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | `Home.jsx` | Hero + 与 LLM 对比 + 三步创作引导 |
| `/inspire` | `InspirePage.jsx` | 灵感生成（9 模块 Pipeline + Critic） |
| `/library` | `LibraryPage.jsx` | 5320 首诗知识库 |
| `/polish` | `PolishPage.jsx` | 创作润色 |
| `/summary` | `SummaryPage.jsx` | TextRank 自动文摘 |
| `/correct` | `CorrectPage.jsx` | 文本校错 |
| `/knowledge-graph` | `KnowledgeGraphPage.jsx` | 关系图谱 |
| `/login` | `LoginPage.jsx` | 用户登录 / 注册 |
| `/workflow` | `AboutPage.jsx` | 流水线架构说明 |
| `/stack` | `TechStackPage.jsx` | 模型技术栈 |
| `/benchmark` | `EvaluatePage.jsx` | 开发者定量评测 |

## 关键模块

```
src/
├── pages/                # 路由页面
├── components/           # 复用组件
│   ├── Hero.jsx
│   ├── Navbar.jsx
│   ├── CreatorSteps.jsx
│   ├── MusAgentVsLLM.jsx
│   ├── PostGenerationReview.jsx
│   ├── TopicGraphPanel.jsx
│   ├── InspirationChatPanel.jsx
│   ├── ForceGraphView.jsx
│   └── library/          # 知识库专用子组件
│       ├── LibraryHero.jsx
│       ├── PoemScrollCard.jsx
│       └── EmotionSpectrum.jsx
├── nlp/                  # 后端 API 客户端
│   ├── api.js            # fetch 封装
│   ├── pipeline.js       # Pipeline 调度
│   └── retriever.js      # （旧版前端混合检索，可忽略）
├── context/              # React Context
│   ├── AuthContext.jsx
│   └── ThemeContext.jsx
├── config/
│   └── routes.js         # 路由表 + 导航分组
├── constants/
│   └── labels.js         # 全站中文标签
├── utils/
│   ├── auth.js           # JWT 存储
│   ├── pipelineStream.js # SSE 解析
│   └── chatClient.js
└── data/
    └── poems_extracted.json  # 5320 首诗（前端兜底检索）
```

## 设计原则

- **暗色主题统一** — 通过 CSS 变量（`var(--bg-card)`、`var(--text-muted)` 等）
- **不引入新的状态管理库** — 用 React 原生 `useState` + Context
- **错误降级** — 后端不可用时所有 NLP 仍能跑（前端有兜底 retriever）
- **响应式** — 3 个断点（手机 ≤767 / 平板 768-1023 / 桌面 ≥1024）
