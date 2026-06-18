<div align="center">
  <br />
    <img src="public/images/logo.png" alt="MusAgent Logo" width="80" />
    <h1>MusAgent</h1>
    <p>基于多模块 NLP 流水线 + RAG 的文学与艺术灵感生成平台</p>
  <br />

  <div>
    <img src="https://img.shields.io/badge/-React-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
    <img src="https://img.shields.io/badge/-GSAP-88CE02?style=for-the-badge&logo=greensock&logoColor=white" />
    <img src="https://img.shields.io/badge/-Tailwind-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" />
    <img src="https://img.shields.io/badge/-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
    <img src="https://img.shields.io/badge/-DeepSeek-4D6BFE?style=for-the-badge&logo=openai&logoColor=white" />
    <img src="https://img.shields.io/badge/-BGE-FF6B35?style=for-the-badge&logo=huggingface&logoColor=white" />
  </div>

  <h3 align="center">9 模块化 NLP 流水线 + 1 Critic Agent · 5320 首诗歌知识库 · DeepSeek LLM 生成</h3>
</div>

---

## 📖 简介

MusAgent 是一个基于 **模块化 NLP 流水线 + RAG** 的文学与艺术灵感生成平台。输入一个主题或情绪，系统依次执行 9 个流水线模块（分词 → 主题扩展 → 关键词 → 摘要 → 混合检索 → 情感分析 → RAG 抽取 → 风格匹配 → 生成），最后由 **Critic Agent** 自我评分并在必要时触发重写，**双通道**呈现算法模板与 DeepSeek LLM 结果。

平台还内置了**灵感菌**对话机器人——一个基于 DeepSeek 的情绪感知助手，可倾听用户心声、引导情绪、激发创作灵感。

**v3.0 重大升级**：
- ✅ 新增 **Critic Agent**（基于 LLM 的 self-critique + 规则化兜底，<7 分自动重写）
- ✅ 引入 BGE-small-zh-v1.5 向量检索 + bge-reranker-base Cross-Encoder 精排
- ✅ 接入 RoBERTa 中文情感模型做双通道融合
- ✅ 知识图谱关系抽取（RE 模型 + BGE 实体识别）
- ✅ 反馈闭环：用户评分 → 关键词权重 + LLM Prompt 调节

---

## 🧠 NLP Pipeline (9 模块 + 1 Critic)

```
用户输入 → 分词 → NER → 主题扩展 → 关键词 → 摘要
        → 混合检索(BM25+BGE+CE) → 情感融合 → 语义解释 → RAG 抽取
        → 风格/音乐匹配 → 算法模板 + LLM 并行生成
        → ★ Critic Agent 自评 → 必要时重写 → 输出
```

| # | 模块 ID | 模块名 | 技术 | 职责 |
|---|---------|--------|------|------|
| 1 | `seg` | 分词 | Jieba + HMM | 中文分词 + 停用词 + 数量词残片过滤 |
| 2 | `ner` | 命名实体 | BERT-NER + Jieba | 抽取人/地/意象/作品/体裁等 8 类实体 |
| 3 | `qe` | 主题扩展 | 同义词词典 | 解决短主题检索不到的问题（`校园爱情` → `校园/爱情/青春/初恋`） |
| 4 | `kw` | 关键词 | TF-IDF | 引入知识库文档频率 + 原始词加权 |
| 5 | `sum` | 摘要 | TextRank | 句子级 PageRank 摘要 |
| 6 | `ret` | 混合检索 | BM25 + **BGE-small-zh-v1.5** + **bge-reranker-base** | 三阶段：BM25 召回 → BGE 稠密召回 → Cross-Encoder 精排 |
| 7 | `emo` | 融合情感 | 文学词典 + **RoBERTa-jd-binary** | 6 维情感 × 双通道打分 |
| 8 | `rag` | RAG 上下文 | 结构化抽取 | 把检索结果提炼为「主题/作者/情绪/可化用片段」注入 LLM Prompt |
| 9 | `gen` | 文本生成 | 规则模板 + **DeepSeek Chat** | 双通道：算法模板降级 + LLM 优先 |
| ★ | `critic` | **Critic Agent** | DeepSeek Chat | **对 LLM 草稿自我评分（0-10），<7 触发重写**（v3.0 新增） |

> **"多 Agent" 的真实含义**：v3.0 起 `critic` 阶段对 `llm` 输出做 self-critique；不达标则重跑 `gen`，最多 1 次。这是 **Generator + Critic 闭环**。

---

## ✨ 功能

- **灵感生成** — 输入主题，选择创作类型、风格、篇幅、押韵、抽象度，一键生成双版本（⚙️ 算法 + 🤖 LLM）
- **Critic 自评 + 自动重写**（v3.0）— 生成后展示 Critic 评分 / 问题 / 改进建议 / 是否触发重写
- **创作润色** — 原文诊断、修改建议、保守润色版与风格化润色版
- **知识库** — 5320 首诗歌（现代诗 5000 + 古典诗词 320），情感/类型筛选、关键词搜索、点击展开全文
- **灵感菌对话** — 情绪感知 AI 助手，NLP 分析每条消息的情感与关键词
- **知识图谱** — 8 类实体（人物/地点/意象/作品/体裁/时间/主题） × 7 类关系的 ForceGraph 可视化
- **算法评测** — 50 主题真实 BM25 / Hybrid 对比 + 误差棒（`/benchmark`）
- **用户系统** — JWT 鉴权、SQLite 持久化、跨设备同步对话与创作记录
- **反馈闭环** — 评分 + 标签 → 关键词权重 + LLM Prompt 调节
- **纯暗色主题** — CSS 变量驱动，无亮色模式

---

## 🚀 快速开始

### 环境要求

| 依赖 | 版本 |
|------|------|
| Node.js | ≥ 18 |
| npm | ≥ 9 |
| Python | ≥ 3.10 |

### 本地启动

```bash
# 1. 克隆
git clone https://github.com/liusiqi05/Musagent.git
cd Musagent

# 2. 前端依赖
cd musagent
npm install

# 3. 后端依赖
cd ../back
pip install -r requirements.txt

# 4. 配置 DeepSeek API Key（可选；不设则 LLM 降级为算法模板）
export DEEPSEEK_API_KEY="sk-you...here"
# 可选：BGE / Reranker 模型（不设也能用 BM25 + ngram 跑）
# export EMBED_MODEL=BAAI/bge-small-zh-v1.5
# export RERANK_MODEL=BAAI/bge-reranker-base

# 5. 启动后端
uvicorn main:app --reload --port 8000

# 6. 启动前端（新终端）
cd ../musagent
npm run dev
```

打开 [http://localhost:5173](http://localhost:5173)

### Docker 一键启动

```bash
docker-compose up
# → http://localhost:5173
```

---

## 📁 项目结构

```
Musagent/
├── musagent/                # 前端 (React 19 + Vite 6 + Tailwind 4 + GSAP)
│   ├── src/
│   │   ├── components/      # Hero / Navbar / CreatorSteps / MusAgentVsLLM / ...
│   │   ├── pages/           # Inspire / Library / Polish / KnowledgeGraph / Benchmark / ...
│   │   ├── nlp/             # API 客户端 + Pipeline 调度
│   │   ├── data/            # poems_extracted.json（5320 首）
│   │   └── index.css        # 全局样式（暗色主题 + 响应式）
│   └── public/              # 静态资源
├── back/                    # 后端 (FastAPI)
│   ├── main.py              # API 路由 + DeepSeek 集成 + SSE 流式
│   ├── nlp_engine.py        # 9 模块化 NLP 流水线（分词/TF-IDF/TextRank/混合检索/情感/RAG/生成）
│   ├── quality_engine.py    # ★ v3.0 新增：Critic Agent + 质量评估
│   ├── kg_engine.py         # 知识图谱构建与查询
│   ├── re_model.py          # 关系抽取 RE 模型
│   ├── ml_models.py         # BGE / RoBERTa / NER 模型加载
│   ├── database.py          # SQLite 持久化（用户/对话/反馈/生成日志）
│   ├── auth.py              # JWT 鉴权
│   ├── config.py            # 配置 + 环境变量
│   ├── cache.py             # 检索结果缓存
│   ├── orchestrator.py      # 流水线编排器（计时 + SSE 推送）
│   ├── semantic_index.py    # BGE 向量索引
│   ├── feedback_engine.py   # 反馈权重调节
│   ├── seed_demo_data.py    # 演示数据种子
│   ├── product_regression_tests.py  # 15 项产品回归断言
│   └── tests/               # Pytest 测试套件
├── docs/                    # 论文 / 答辩用图表与文档
│   ├── figures/             # 9 张架构图 + 3 张评测图
│   ├── diagrams/            # 10 张 PNG 架构示意图
│   ├── generate_figures.py  # 架构图自动生成
│   ├── generate_report_docx.py
│   └── regenerate_fig7_10_11.py  # ★ 评测图真实数据再生成
├── scripts/                 # 辅助脚本
│   └── generate_product_doc.py
├── PROJECT.md               # 项目说明（含 9 模块 Pipeline 表）
├── OPTIMIZATION_LOG.md      # 220 行优化日志
├── Dockerfile               # ★ v3.0 新增
├── docker-compose.yml       # ★ v3.0 新增
└── README.md                # 本文件
```

---

## 🔌 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 健康检查（含 BGE / RoBERTa 状态） |
| `POST` | `/api/pipeline` | 完整流水线 `{topic, creationType, emotionTone, artStyle, ...}` |
| `POST` | `/api/pipeline/stream` | SSE 流式（实时阶段进度） |
| `POST` | `/api/regenerate` | 沿用已有分析结果，仅重新生成文本 |
| `POST` | `/api/polish` | 创作润色 `{text, targetStyle, preserveMeaning}` |
| `GET` | `/api/knowledge` | 知识库分页、搜索和筛选 |
| `POST` | `/api/chat` | 灵感对话 `{message, history}` |
| `POST` | `/api/feedback` | 反馈提交 `{sourceType, rating, comment, topic, ...}` |
| `GET` | `/api/feedback/stats` | 反馈统计 |
| `GET` | `/api/knowledge-graph` | 关系图谱 `{limit, entity, curated}` |
| `GET` | `/api/benchmark` | ★ v3.0 新增：开发者定量 benchmark |
| `POST` | `/api/kg/train-re` | 训练 RE 模型（管理员） |
| `POST` | `/api/auth/register` | 用户注册 |
| `POST` | `/api/auth/login` | 用户登录（返回 JWT） |
| `GET` | `/api/auth/me` | 当前用户信息 |
| `POST` | `/api/segment` | 分词 `{text}` |
| `POST` | `/api/keywords` | 关键词 `{words}` |
| `POST` | `/api/sentiment` | 情感分析 `{words}` |
| `POST` | `/api/retrieve` | 相似度检索 `{words, creationType, searchMode}` |
| `POST` | `/api/semantic-search` | BGE 语义检索 `{query, top_n}` |

---

## 🛠 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19 · Vite 6 · Tailwind CSS 4 · GSAP 3 · React Router 7 |
| 后端 | FastAPI · Uvicorn · Pydantic v2 · SSE 流式 |
| NLP | Jieba · NumPy · scikit-learn · TF-IDF · TextRank · 情感词典 |
| 检索 | BM25 (自实现) · **BGE-small-zh-v1.5** (FlagEmbedding) · **bge-reranker-base** |
| 情感 | **uer/roberta-base-finetuned-jd-binary-chinese** |
| NER | **ckiplab/bert-base-chinese-ner** |
| 校错 | **MacBERT (pycorrector)** |
| 关系抽取 | 自训练 RE 模型（`re_model.py`） |
| LLM | **deepseek-chat** · OpenAI SDK |
| 数据 | 5320 首诗歌 JSON（5000 现代 + 320 古典） |
| 持久化 | SQLite + WAL · 4 张表（users / chat_sessions / feedback / generations） |
| 鉴权 | JWT (HS256) · bcrypt 风格哈希 |
| 容器 | Docker · docker-compose |

---

## 🌐 页面路由

| 路径 | 类型 | 功能 |
|------|------|------|
| `/` | 入口 | Hero 视频背景 + 三步创作引导 + 与 LLM 对比 |
| `/inspire` | 创作 | 灵感生成工作台（**9 模块 Pipeline + Critic**） |
| `/library` | 创作 | 5320 首诗知识库（分页 / 搜索 / 筛选） |
| `/polish` | 创作 | 创作润色（诊断 + 保守版 + 风格化版） |
| `/summary` | 工具 | TextRank 自动文摘 |
| `/correct` | 工具 | 文本校错 |
| `/login` | 账号 | 跨设备同步 |
| `/knowledge-graph` | 系统 | 关系图谱（ForceGraph 可视化） |
| `/workflow` | 系统 | 流水线架构说明 |
| `/stack` | 系统 | Transformer-RAG 组件清单 |
| `/benchmark` | 系统 | 开发者定量评测（开发者页） |

> 旧路径 `/cocktails`、`/menu`、`/contact`、`/about`、`/evaluate` 仍可用，会自动重定向到对应新路径。

---

## 📊 论文 / 答辩用图

`docs/figures/` 中已生成 12 张程序化图表：

| 文件 | 内容 |
|------|------|
| `fig1_system_architecture.png` | 5 层系统架构（UI / Gateway / Orchestrator / Engine / Data） |
| `fig2_pipeline_flow.png` | 9 模块流水线时序图 |
| `fig3_hybrid_retrieval.png` | BM25 vs Hybrid 检索原理对比 |
| `fig4_emotion_fusion.png` | 词典 + RoBERTa 双通道情感融合 |
| `fig5_rag_citation.png` | RAG 引用与化用标注 |
| `fig6_explainability.png` | 可解释性样例 |
| `fig7_ablation_chart.png` | ★ 真实数据：50 主题 Top-5 重叠分布 + 误差棒 |
| `fig8_data_model.png` | SQLite 数据模型 |
| `fig9_semantic_kg.png` | 语义知识图谱 |
| `fig10_llm_vs_template.png` | ★ v3.0 新增：LLM vs 模板 4 维指标对比 |
| `fig11_critic_agent.png` | ★ v3.0 新增：Critic 评分分布 + 触发率 |

重新生成命令：

```bash
cd docs
python regenerate_fig7_10_11.py
```

---

## 🧪 测试

```bash
cd back
python -m pytest tests/ -v              # 单元测试
python product_regression_tests.py       # 15 项产品回归断言
```

回归测试覆盖：
- 量词残片过滤（如 `张脸`）
- 短主题扩展（`校园爱情` → `校园/爱情/青春/初恋`）
- 情感识别准确率
- BM25 / Hybrid 检索对比
- LLM 不可用降级
- 知识库分页与标签
- 创作润色结构完整性

---

## 📄 详细文档

- [PROJECT.md](PROJECT.md) — 项目说明（9 模块表 / 技术栈 / 启动 / 部署）
- [OPTIMIZATION_LOG.md](OPTIMIZATION_LOG.md) — 220 行优化记录（开发历程）

---

## 📜 License

MIT © 2026 MusAgent Contributors
