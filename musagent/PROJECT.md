# MusAgent — 模块化 NLP 流水线 + RAG 文学灵感平台

> **v3.0 — Transformer-RAG 架构**
> 从基于词典的统计 NLP（v1.0 / v2.0）升级到 **9 个模块化流水线 + 1 个 Critic Agent 自我反思**，并接入 BGE 向量检索、Cross-Encoder 重排、RoBERTa 情感融合与可解释 KG 关系抽取。

---

## 一句话定位

不是「把主题丢给大模型」—— 先跑 NLP 流水线、检索知识库、构建图谱，再让 LLM 在**有依据的上下文**里创作；最后由 **Critic Agent** 自我评分，必要时触发重写。

---

## 9 个模块化流水线 + 1 个 Critic Agent

| # | 模块 ID | 模块名 | 技术 | 职责 |
|---|---------|--------|------|------|
| 1 | `seg` | 分词 | Jieba + HMM | 中文分词 + 停用词 + 数量词残片过滤 |
| 2 | `ner` | 命名实体 | BERT-NER + Jieba | 抽取人/地/意象/作品/体裁等 8 类实体 |
| 3 | `qe` | 主题扩展 | 同义词词典 | 解决短主题检索不到的问题（`校园爱情` → `校园/爱情/青春/初恋`） |
| 4 | `kw` | 关键词 | TF-IDF | 引入知识库文档频率 + 原始词加权 |
| 5 | `sum` | 摘要 | TextRank | 句子级 PageRank 摘要 |
| 6 | `ret` | 混合检索 | BM25 + BGE-small-zh + bge-reranker | 三阶段：BM25 召回 → BGE 稠密召回 → Cross-Encoder 精排 |
| 7 | `emo` | 融合情感 | 文学词典 + RoBERTa-jd-binary | 6 维情感 × 双通道打分，融合给出主导情绪与强度 |
| 8 | `rag` | RAG 上下文 | 结构化抽取 | 把检索结果提炼为「主题/作者/情绪/可化用片段」注入 LLM Prompt |
| 9 | `gen` | 文本生成 | 规则模板 + DeepSeek Chat | 双通道：算法模板降级 + LLM 优先 |
| ★ | `critic` | **Critic Agent** | DeepSeek Chat | **对 LLM 草稿自我评分（0–10），<7 触发重写** |

> **"多 Agent" 的真实含义**：v3.0 起 `critic` 阶段对 `llm` 输出做 self-critique；如不达标则重跑 `gen`，最多 1 次。这是**单一 Critic + Generator 闭环**，不是 9 个 Agent 并行协商。

---

## Pipeline 编排（`orchestrator.py`）

`PipelineContext.run(stage_id, name, model, fn)` 提供：
- 阶段计时（ms）
- 阶段错误捕获
- SSE 实时推送

```python
ctx = PipelineContext(request=req, on_stage=on_stage_cb)
seg = ctx.run("seg",  "分词",   "Jieba",            lambda: segment(topic))
entities = ctx.run("ner", "命名实体", "BERT-NER",    lambda: extract_entities(topic))
...
gen_llm = ctx.run("llm", "LLM 生成", "DeepSeek",   gen_llm_fn)
critic = ctx.run("critic", "Critic Agent", "DeepSeek", lambda: critic_review(gen_llm, rag))
```

每个 stage 都会 push 到 `ctx.stages`，最后 `stages_to_dict()` 转 JSON 给前端。

---

## 技术栈（实际启用）

| 层级 | 技术 | 启用方式 |
|------|------|----------|
| 前端 | React 19 · Vite 6 · Tailwind 4 · GSAP 3 | `npm run dev` |
| 后端 | FastAPI · Uvicorn · Pydantic v2 | `uvicorn main:app --port 8000` |
| 检索 | BM25 (Jieba) · **BGE-small-zh-v1.5** · **bge-reranker-base** | `ml_models.py` 启动时加载 |
| 情感 | **uer/roberta-base-finetuned-jd-binary-chinese** | `ml_models.py` 启动时加载 |
| NER | **ckiplab/bert-base-chinese-ner** | 启动时加载（可选） |
| 校错 | **MacBERT (pycorrector)** | 启动时加载（可选） |
| LLM | **deepseek-chat** | OpenAI SDK + `DEEPSEEK_API_KEY` |
| 数据 | 5320 首诗 JSON（5000 现代 + 320 古典） | `musagent/src/data/poems_extracted.json` |
| 持久化 | SQLite（用户、对话、反馈、生成日志） | `back/data/musagent.db` |
| 鉴权 | JWT (HS256) | `back/auth.py` |
| 流式 | SSE | `/api/pipeline/stream` |

> **BGE / RoBERTa 等 HuggingFace 模型首次启动会从 HF 拉取并缓存到 `back/.cache/`**（10–15 分钟），断点续传。

---

## 用户创作路径 vs 系统技术页

| 路径 | 类型 | 用途 |
|------|------|------|
| `/` | 创作入口 | Hero 视频背景 + 三步创作引导 |
| `/inspire` | 创作 | 灵感生成工作台（**核心页 869 → 已拆分**） |
| `/library` | 创作 | 5320 首诗知识库（分页 / 搜索 / 筛选） |
| `/polish` | 创作 | 创作润色（诊断 + 保守版 + 风格化版） |
| `/summary` | 工具 | TextRank 自动文摘 |
| `/correct` | 工具 | 文本校错 |
| `/login` | 账号 | 跨设备同步 |
| `/knowledge-graph` | 系统 | 关系图谱（ForceGraph 可视化） |
| `/workflow` | 系统 | 流水线架构说明 |
| `/stack` | 系统 | Transformer-RAG 组件清单 |
| `/benchmark` | 系统 | 开发者定量评测（脚注：用户流程请用 `/inspire`） |

---

## 启动

### 本地开发

```bash
# 后端
cd back
pip install -r requirements.txt
export DEEPSEEK_API_KEY="sk-..."  # 不设置则降级为算法模板
uvicorn main:app --reload --port 8000

# 前端
cd musagent
npm install
npm run dev
# → http://localhost:5173
```

### Docker

```bash
docker-compose up
```

### 环境变量（`back/.env`）

```env
DEEPSEEK_API_KEY=sk-...
EMBED_MODEL=BAAI/bge-small-zh-v1.5
RERANK_MODEL=BAAI/bge-reranker-base
SENTIMENT_MODEL=uer/roberta-base-finetuned-jd-binary-chinese
NER_MODEL=ckiplab/bert-base-chinese-ner
```

---

## 测试

```bash
cd back
python -m pytest tests/ -v              # 单元测试
python product_regression_tests.py       # 15 项产品回归断言
```

---

## 答辩用入口

- 架构总览：`docs/figures/fig1_system_architecture.png`
- 流水线时序：`docs/figures/fig2_pipeline_flow.png`
- 混合检索对比：`docs/figures/fig3_hybrid_retrieval.png`
- 情感融合：`docs/figures/fig4_emotion_fusion.png`
- RAG 引用：`docs/figures/fig5_rag_citation.png`
- Critic Agent 评估（v3.0 新增）：`docs/figures/fig10_critic_agent.png`
- LLM vs 模板对比（v3.0 新增）：`docs/figures/fig11_llm_vs_template.png`
