"""
MusAgent 后端 — FastAPI + DeepSeek LLM
启动: uvicorn main:app --reload --port 8000
"""
import os
import json
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, LLM_MODEL, LLM_TEMPERATURE,
    LLM_MAX_TOKENS, LLM_POLISH_TEMPERATURE, get_runtime_config,
    LENGTH_TOKEN_MAP, LENGTH_CHAR_HINT,
)
from cache import cache_get, cache_set, make_cache_key, get_cache_info
from database import (
    init_db, import_poems_from_json, query_poems, save_feedback, save_qa_feedback,
    get_feedback_stats, get_knowledge_graph, get_db_stats, log_generation,
    create_chat_session, list_chat_sessions, get_chat_session, get_chat_history_for_llm,
    append_chat_message, delete_chat_session,
    create_user, get_user_by_username, bind_client_sessions_to_user,
)
from auth import hash_password, verify_password, create_access_token, require_user, get_optional_user
from feedback_engine import get_feedback_insights, apply_feedback_to_keywords
from quality_engine import assess_pipeline_output, filter_low_quality_items, critic_review
from kg_engine import analyze_topic_graph, build_knowledge_graph_from_poems, export_re_training_samples
from re_model import get_re_model_info, train_relation_model

from nlp_engine import (
    segment, extract_keywords, summarize, analyze_sentiment,
    retrieve_similar, match_art_style, match_music, expand_query,
    get_knowledge_page, extract_entities, correct_text, run_nlp_evaluation,
    explain_retrieval_results, build_generation_citations,
)
from semantic_index import warm_semantic_index, get_index_info, semantic_search
import nlp_engine

app = FastAPI(title="MusAgent API", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== DeepSeek 配置 =====
llm_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

# ===== Pydantic 模型 =====
class PipelineRequest(BaseModel):
    topic: str
    creationType: str = "现代诗"
    emotionTone: str = "孤独"
    artStyle: str = "赛博朋克"
    useLLM: bool = False  # 是否使用 DeepSeek 生成
    lengthPreference: str = "中"  # 短 | 中 | 长 | 超长（散文/短篇支持长文本）
    languageStyle: str = "清新"
    rhymeLevel: str = "自由"
    abstractionLevel: str = "平衡"
    fastMode: bool = False  # 快速模式：BM25 检索、跳过 KG，约快 40%

class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=6, max_length=64)
    email: str = ""
    displayName: str = ""

class LoginRequest(BaseModel):
    username: str
    password: str
    clientId: str = ""  # 登录后绑定匿名对话

class RegenerateRequest(BaseModel):
    input: PipelineRequest
    keywords: list = []
    similarWorks: list = []
    ragResults: list = []
    emotion: dict = {}
    artStyles: list = []
    music: dict = {}

class PolishRequest(BaseModel):
    text: str
    targetStyle: str = "文学化"
    preserveMeaning: bool = True
    useLLM: bool = True

class TextRequest(BaseModel):
    text: str
    top_n: int = 3

class CorrectRequest(BaseModel):
    text: str

class SemanticSearchRequest(BaseModel):
    query: str
    top_n: int = 10
    poemType: str = "all"

class FeedbackRequest(BaseModel):
    sourceType: str  # generation | chat | polish | retrieval
    rating: int
    comment: str = ""
    topic: str = ""
    contentPreview: str = ""
    sourceId: str = ""
    metadata: dict = {}

class QAFeedbackRequest(BaseModel):
    question: str
    answer: str
    rating: int
    helpful: bool = True
    tags: list[str] = []

class QualityRequest(BaseModel):
    content: str
    keywords: list = []
    emotion: str = ""
    similarWorks: list = []

class TrainRERequest(BaseModel):
    epochs: int = 2
    limit: int = 1200
    batchSize: int = 16
    maxTrainSamples: int = 400


@app.on_event("startup")
def startup_warm_index():
    """启动时初始化数据库、缓存、知识库与语义索引。"""
    init_db()
    import_poems_from_json()
    nlp_engine._ensure_kb()
    warm_semantic_index(nlp_engine._kb_docs)
    try:
        build_knowledge_graph_from_poems(nlp_engine.get_poem_list(), max_poems=600)
    except Exception:
        pass


# ===== API 路由 =====
@app.get("/api/health")
def health():
    from ml_models import get_stack_info
    index_info = get_index_info()
    return {
        "status": "ok",
        "service": "MusAgent",
        "version": "3.0",
        "stack": get_stack_info(),
        "semanticIndex": index_info,
        "llmConfigured": bool(DEEPSEEK_API_KEY) and DEEPSEEK_API_KEY != "sk-your-key-here",
        "database": get_db_stats(),
        "cache": get_cache_info(),
        "config": get_runtime_config(),
    }


@app.post("/api/auth/register")
def api_register(req: RegisterRequest):
    if get_user_by_username(req.username):
        return {"success": False, "error": "用户名已被占用"}
    salt, pwd_hash = hash_password(req.password)
    user = create_user(req.username, pwd_hash, salt, req.email, req.displayName or req.username)
    token = create_access_token(user["id"], user["username"])
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "displayName": user["displayName"],
            "email": user["email"],
        },
    }


@app.post("/api/auth/login")
def api_login(req: LoginRequest):
    user = get_user_by_username(req.username)
    if not user or not verify_password(req.password, user["passwordSalt"], user["passwordHash"]):
        return {"success": False, "error": "用户名或密码错误"}
    bound = 0
    if req.clientId:
        bound = bind_client_sessions_to_user(req.clientId, user["id"])
    token = create_access_token(user["id"], user["username"])
    return {
        "success": True,
        "token": token,
        "boundSessions": bound,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "displayName": user["displayName"],
            "email": user["email"],
        },
    }


@app.get("/api/auth/me")
def api_me(user: dict = Depends(require_user)):
    return {"user": user}


@app.get("/api/config")
def api_config():
    return get_runtime_config()


@app.get("/api/db/stats")
def api_db_stats():
    return get_db_stats()


@app.get("/api/stack")
def api_stack():
    from ml_models import get_stack_info
    return get_stack_info()

@app.post("/api/segment")
def api_segment(req: dict):
    text = req.get("text", "")
    return segment(text)

@app.post("/api/keywords")
def api_keywords(req: dict):
    words = req.get("words", [])
    return {"keywords": extract_keywords(words, 10)}

@app.post("/api/sentiment")
def api_sentiment(req: dict):
    text = req.get("text", "")
    words = req.get("words") or segment(text)["words"]
    return analyze_sentiment(words, full_text=text or "".join(words))

@app.post("/api/entities")
def api_entities(req: TextRequest):
    return extract_entities(req.text)

@app.post("/api/summarize")
def api_summarize(req: TextRequest):
    result = summarize(req.text, top_n=max(1, min(req.top_n, 8)))
    seg = segment(req.text)
    kw = extract_keywords(seg["words"], 6)
    return {**result, "keywords": kw, "sentenceCount": result.get("count", 0)}

@app.post("/api/correct")
def api_correct(req: CorrectRequest):
    base = correct_text(req.text)
    seg = segment(base["corrected"])
    emo = analyze_sentiment(seg["words"], full_text=base["corrected"])
    return {**base, "segmentation": seg, "emotion": emo}

@app.post("/api/semantic-search")
def api_semantic_search(req: SemanticSearchRequest):
    results = semantic_search(req.query, top_n=req.top_n, poem_type=req.poemType)
    return {"query": req.query, "results": results, "index": get_index_info()}

@app.get("/api/evaluate")
def api_evaluate():
    return run_nlp_evaluation()

@app.post("/api/retrieve")
def api_retrieve(req: dict):
    words = req.get("words", [])
    text = req.get("text", "")
    creation_type = req.get("creationType", "all")
    search_mode = req.get("searchMode", "hybrid")
    return {
        "results": retrieve_similar(
            words, creation_type, 5,
            query_text=text or " ".join(words),
            search_mode=search_mode,
        ),
        "searchMode": search_mode,
    }

@app.get("/api/knowledge")
def api_knowledge(
    page: int = 1,
    pageSize: int = 30,
    search: str = "",
    emotion: str = "all",
    poemType: str = "all",
    searchMode: str = "keyword",
):
    cache_key = make_cache_key("knowledge", {
        "page": page, "pageSize": pageSize, "search": search,
        "emotion": emotion, "poemType": poemType, "searchMode": searchMode,
    })
    cached = cache_get(cache_key)
    if cached:
        return {**cached, "cached": True}

    if searchMode == "keyword" and not search:
        result = query_poems(page, pageSize, "", emotion, poemType)
        view = nlp_engine._ensure_knowledge_view()
        result["stats"] = view["stats"]
        result["filteredTotal"] = result["total"]
        result["hasMore"] = page < result["totalPages"]
        result["searchMode"] = searchMode
    else:
        result = get_knowledge_page(page, pageSize, search, emotion, poemType, searchMode)

    cache_set(cache_key, result)
    return {**result, "cached": False}


@app.post("/api/feedback")
def api_feedback(req: FeedbackRequest):
    rating = max(1, min(5, req.rating))
    saved = save_feedback(
        req.sourceType, rating, req.comment, req.topic,
        req.contentPreview, req.sourceId, req.metadata,
    )
    return {**saved, "stats": get_feedback_stats()}


@app.post("/api/feedback/qa")
def api_qa_feedback(req: QAFeedbackRequest):
    rating = max(1, min(5, req.rating))
    saved = save_qa_feedback(req.question, req.answer, rating, req.helpful, req.tags)
    return {**saved, "stats": get_feedback_stats()}


@app.get("/api/feedback/stats")
def api_feedback_stats():
    return get_feedback_stats()


@app.get("/api/feedback/insights")
def api_feedback_insights():
    return get_feedback_insights()


@app.get("/api/knowledge-graph")
def api_knowledge_graph(limit: int = 80, entity: str = "", curated: bool = True):
    cache_key = make_cache_key("kg", {"limit": limit, "entity": entity, "curated": curated})
    cached = cache_get(cache_key)
    if cached:
        return {**cached, "cached": True}
    graph = get_knowledge_graph(limit=limit, entity=entity, curated=curated)
    cache_set(cache_key, graph)
    return {**graph, "cached": False}


@app.post("/api/quality")
def api_quality(req: QualityRequest):
    from quality_engine import score_generation, score_keywords, score_retrieval
    kw_eval = score_keywords(req.keywords)
    retrieval_eval = score_retrieval(req.similarWorks)
    gen_eval = score_generation(req.content, req.keywords, req.emotion)
    overall = round((gen_eval["score"] * 0.5 + kw_eval["score"] * 0.2 + retrieval_eval["score"] * 0.3), 3)
    return {
        "overall": {"score": overall, "label": gen_eval["label"]},
        "keywords": kw_eval,
        "retrieval": retrieval_eval,
        "generation": gen_eval,
    }


@app.get("/api/kg/export-re-samples")
def api_export_re_samples(limit: int = 500):
    poems = nlp_engine.get_poem_list()
    out = Path(__file__).resolve().parent / "data" / "re_training_samples.jsonl"
    return export_re_training_samples(poems, str(out), limit=limit)


@app.get("/api/kg/re-model")
def api_re_model_status():
    return get_re_model_info()


@app.post("/api/kg/train-re")
def api_train_re(req: TrainRERequest):
    """触发 BERT 关系抽取微调（后台耗时任务，建议本地 CLI: python train_re.py）。"""
    poems = nlp_engine.get_poem_list()
    out = Path(__file__).resolve().parent / "data" / "re_training_samples.jsonl"
    export_re_training_samples(poems, str(out), limit=req.limit)
    result = train_relation_model(
        samples_path=str(out),
        epochs=max(1, min(req.epochs, 5)),
        batch_size=max(4, min(req.batchSize, 32)),
        max_samples=req.limit,
        max_train_samples=max(100, min(req.maxTrainSamples, 800)),
    )
    return result

@app.post("/api/pipeline")
def run_full_pipeline(req: PipelineRequest):
    """Transformer-RAG 流水线：分词 → NER → 检索(BM25+BGE+重排) → 融合情感 → RAG → 生成"""
    from orchestrator import PipelineContext

    ctx = PipelineContext(request=req)
    return _execute_pipeline(ctx, req)


PIPELINE_STAGE_TOTAL = 14  # v3.0: +1 for Critic Agent (critic)


def _execute_pipeline(ctx, req: PipelineRequest):
    from orchestrator import stages_to_dict
    from ml_models import get_stack_info

    feedback_insights = get_feedback_insights()
    search_mode = "bm25" if req.fastMode else "hybrid"

    seg = ctx.run("seg", "分词", "Jieba", lambda: segment(req.topic))
    entities = ctx.run("ner", "命名实体", "BERT-NER + Jieba", lambda: extract_entities(req.topic))
    expanded_query = ctx.run("qe", "查询扩展", "同义词词典", lambda: expand_query(req.topic, seg["words"]))
    kw = ctx.run("kw", "关键词", "TF-IDF", lambda: apply_feedback_to_keywords(
        extract_keywords(expanded_query["expanded"], 10, seg["words"]), feedback_insights,
    ))
    summary = ctx.run("sum", "TextRank 摘要", "TextRank", lambda: summarize(req.topic))
    similar = ctx.run(
        "ret", "混合检索" if not req.fastMode else "BM25 检索",
        "BM25 + BGE + Cross-Encoder" if not req.fastMode else "BM25",
        lambda: filter_low_quality_items(retrieve_similar(
            expanded_query["expanded"], req.creationType, 5,
            query_text=req.topic, search_mode=search_mode,
        )),
    )
    emotion = ctx.run(
        "emo", "融合情感", "文学词典 + RoBERTa",
        lambda: analyze_sentiment(expanded_query["expanded"], similar, full_text=req.topic),
    )

    def attach_explanations():
        explained, insight = explain_retrieval_results(
            req.topic, similar, kw, emotion["dominant"], entities,
        )
        return explained, insight

    explain_result = ctx.run("xpl", "语义解释", "可解释检索", attach_explanations)
    similar, semantic_insight = explain_result

    def build_rag():
        from kg_quality import format_author
        rag_results = []
        for s in similar[:3]:
            expl = s.get("semanticExplanation", {})
            matched = (s.get("matchedTerms") or [])[:3]
            rag_results.append({
                "topic": s["title"],
                "type": s["type"],
                "author": format_author(s["author"]),
                "similarity": s.get("rerankScore", s.get("similarity")),
                "retrievalMethod": s.get("retrievalMethod", search_mode),
                "keywords": matched or [k["keyword"] for k in kw[:3]],
                "emotion": emotion["dominant"],
                "excerpt": s["content"][:120],
                "semanticSummary": expl.get("summary", ""),
                "adaptablePhrase": expl.get("adaptablePhrase", ""),
                "sharedKeywords": expl.get("sharedKeywords", []),
            })
        return rag_results

    rag_results = ctx.run("rag", "RAG 上下文", "结构化抽取", build_rag)

    def match_styles():
        with ThreadPoolExecutor(max_workers=2) as pool:
            art_f = pool.submit(match_art_style, seg["words"], emotion["dominant"])
            music_f = pool.submit(match_music, emotion["dominant"])
            return art_f.result(), music_f.result()

    art, music = ctx.run("sty", "风格映射", "文学风格 + 曲风", match_styles)

    gen_template = ctx.run(
        "gen", "模板生成", "规则 + 检索增强 + 化用标注",
        lambda: template_generate(req, kw, similar, emotion["dominant"], art[0], music, rag_results),
    )

    def gen_llm_fn():
        if req.useLLM:
            return llm_generate(
                req, kw, similar, emotion["dominant"], art[0], music, rag_results,
                feedback_hint=feedback_insights.get("generationHint", ""),
            )
        return {
            **gen_template,
            "method": "未启用 LLM，使用算法模板",
            "note": "请求 useLLM=false，已跳过 DeepSeek 调用",
        }

    gen_llm = ctx.run("llm", "LLM 生成", "DeepSeek Chat", gen_llm_fn)

    # ★ Critic Agent — 对 LLM 输出做 self-critique
    # 评分 < 7 时若 useLLM 仍开启，触发 1 次重写（取最后一次）
    def critic_stage_fn():
        content = (gen_llm or {}).get("content", "") or (gen_template or {}).get("content", "")
        if not content.strip():
            return {
                "score": 0, "issues": ["无可评审内容"], "suggestions": [],
                "method": "skip", "model": "n/a", "retryRecommended": False,
                "triggered": False,
            }
        rag_titles = [r.get("topic", "") for r in (rag_results or [])][:3]
        review = critic_review(
            content=content,
            keywords=kw,
            emotion=emotion.get("dominant", "") if isinstance(emotion, dict) else str(emotion),
            rag_titles=rag_titles,
            art_style=(art[0].get("name", "") if art else ""),
            topic=req.topic,
        )
        review["triggered"] = False
        # 仅当 LLM 已启用且 Critic 评分偏低时触发重写（最多 1 次）
        if req.useLLM and review.get("retryRecommended"):
            try:
                retry_fn = gen_llm_fn
                retry = retry_fn()
                if retry and retry.get("content"):
                    gen_llm["content"] = retry["content"]
                    gen_llm["method"] = (retry.get("method", gen_llm.get("method", "")) + " · Critic 重写")
                    # 重评一次
                    re_review = critic_review(
                        content=retry["content"],
                        keywords=kw,
                        emotion=emotion.get("dominant", "") if isinstance(emotion, dict) else str(emotion),
                        rag_titles=rag_titles,
                        art_style=(art[0].get("name", "") if art else ""),
                        topic=req.topic,
                    )
                    re_review["triggered"] = True
                    re_review["originalScore"] = review["score"]
                    return re_review
            except Exception as exc:
                review["retryError"] = str(exc)[:120]
        return review

    critic = ctx.run("critic", "Critic Agent", "DeepSeek Chat (self-critique)", critic_stage_fn)

    quality = ctx.run(
        "qa", "质量评估", "多维打分 + 筛选",
        lambda: assess_pipeline_output(gen_template, gen_llm, kw, similar, emotion),
    )
    topic_graph = {"nodes": [], "edges": [], "skipped": True, "note": "快速模式已跳过图谱构建"}
    if not req.fastMode:
        topic_graph = ctx.run(
            "kg", "知识图谱", "实体关系抽取",
            lambda: analyze_topic_graph(req.topic, entities, similar, emotion.get("dominant", ""), kw),
        )

    total_ms = round(sum(s.durationMs for s in ctx.stages), 1)
    citations = build_generation_citations(similar, rag_results)
    method = (gen_llm or {}).get("method", gen_template.get("method", ""))
    log_generation(
        req.topic, req.creationType,
        quality["overall"]["score"], quality["overall"]["label"],
        method, quality["overall"]["passed"],
        {"recommended": quality["generation"]["recommended"]},
    )

    return {
        "input": req.model_dump(),
        "segmentation": seg,
        "entities": entities,
        "queryExpansion": expanded_query,
        "keywords": kw,
        "summary": summary["summary"],
        "emotion": emotion,
        "intent": classify_intent(req.topic, req.creationType),
        "similarWorks": similar,
        "semanticInsight": semantic_insight,
        "ragResults": rag_results,
        "artStyles": art,
        "music": music,
        "generated": gen_template,
        "generatedLLM": gen_llm,
        "critic": critic,  # v3.0 新增：Critic Agent 自评 + 必要时重写
        "quality": quality,
        "knowledgeGraph": topic_graph,
        "feedbackInsights": feedback_insights,
        "citations": citations,
        "retrievalMethod": "BM25 → BGE 稠密召回 → Cross-Encoder 精排",
        "stack": get_stack_info(),
        "pipeline": {
            "version": "3.0",
            "stages": stages_to_dict(ctx.stages),
            "totalDurationMs": total_ms,
        },
    }


@app.post("/api/pipeline/stream")
async def run_pipeline_stream(req: PipelineRequest):
    """SSE 实时推送各 Pipeline 阶段进度，完成后返回完整结果。"""
    from orchestrator import PipelineContext, stages_to_dict

    async def event_stream():
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def on_stage(record, index: int):
            payload = {
                **stages_to_dict([record])[0],
                "index": index,
                "total": PIPELINE_STAGE_TOTAL,
                "progress": min(99, round(index / PIPELINE_STAGE_TOTAL * 100)),
            }
            loop.call_soon_threadsafe(queue.put_nowait, ("stage", payload))

        def worker():
            try:
                ctx = PipelineContext(request=req, on_stage=on_stage)
                result = _execute_pipeline(ctx, req)
                loop.call_soon_threadsafe(queue.put_nowait, ("complete", result))
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, ("error", {"message": str(exc)[:200]}))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        while True:
            event_type, payload = await queue.get()
            if event_type == "stage":
                yield f"event: stage\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            elif event_type == "complete":
                yield f"event: complete\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                break
            elif event_type == "error":
                yield f"event: error\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                break

        thread.join(timeout=1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@app.post("/api/regenerate")
def regenerate_from_context(req: RegenerateRequest):
    """沿用已有分析结果，仅重新执行 WriterAgent。"""
    emotion_name = req.emotion.get("dominant", req.input.emotionTone)
    art = req.artStyles[0] if req.artStyles else {"name": req.input.artStyle, "keywords": []}
    music = req.music or {"mood": emotion_name, "genre": "", "desc": ""}
    gen_template = template_generate(req.input, req.keywords, req.similarWorks, emotion_name, art, music, req.ragResults)
    if req.input.useLLM:
        gen_llm = llm_generate(req.input, req.keywords, req.similarWorks, emotion_name, art, music, req.ragResults)
    else:
        gen_llm = {
            **gen_template,
            "method": "未启用 LLM，使用算法模板",
            "note": "请求 useLLM=false，已跳过 DeepSeek 调用",
        }
    return {"generated": gen_template, "generatedLLM": gen_llm}

@app.post("/api/polish")
def polish_text(req: PolishRequest):
    """创作润色：保留原意，输出诊断、建议、保守润色和风格化润色。"""
    text = req.text.strip()
    if not text:
        return {
            "input": req.model_dump(),
            "segmentation": {"words": [], "freq": {}, "total": 0},
            "keywords": [],
            "summary": "",
            "emotion": {"dominant": "未知", "scores": {}, "intensity": 0},
            "diagnosis": [],
            "suggestions": ["请输入需要润色的文本。"],
            "conservative": "",
            "creative": "",
            "method": "空输入",
            "llmUsed": False,
        }

    seg = segment(text)
    kw = extract_keywords(seg["words"], 8)
    summary = summarize(text)
    emotion = analyze_sentiment(seg["words"], full_text=text)
    diagnosis = build_polish_diagnosis(text, kw, emotion, summary["summary"])
    suggestions = build_polish_suggestions(text, kw, emotion)
    fallback = fallback_polish(text, kw, emotion)
    llm_result = None

    if req.useLLM:
        llm_result = llm_polish(text, req.targetStyle, req.preserveMeaning, kw, emotion, diagnosis, suggestions)

    return {
        "input": req.model_dump(),
        "segmentation": seg,
        "keywords": kw,
        "summary": summary["summary"],
        "emotion": emotion,
        "diagnosis": diagnosis,
        "suggestions": suggestions,
        "conservative": (llm_result or {}).get("conservative") or fallback["conservative"],
        "creative": (llm_result or {}).get("creative") or fallback["creative"],
        "method": (llm_result or {}).get("method") or fallback["method"],
        "llmUsed": bool(llm_result),
        "note": (llm_result or {}).get("note") or fallback["note"],
    }

# ===== 意图分类 =====
def classify_intent(topic: str, creation_type: str) -> dict:
    intent_map = {"现代诗":"诗歌创作","古典诗":"诗歌创作","散文":"散文创作","短篇片段":"小说创作"}
    intent = intent_map.get(creation_type, "诗歌创作")
    return {"intent": intent, "confidence": {"诗歌创作": 0.8}}

def _emotion_strength_label(intensity: float) -> str:
    if intensity >= 0.5:
        return "情绪线索明显"
    if intensity >= 0.2:
        return "情绪线索中等"
    if intensity > 0:
        return "情绪线索较弱"
    return "情绪线索不明显"

def build_polish_diagnosis(text: str, keywords: list, emotion: dict, summary_text: str) -> list:
    top_kw = [k["keyword"] for k in keywords[:5]]
    diagnosis = [
        f"核心意象集中在「{'、'.join(top_kw) if top_kw else '暂无明显关键词'}」。",
        f"主导情绪为「{emotion.get('dominant', '未知')}」，{_emotion_strength_label(emotion.get('intensity', 0))}。",
    ]
    if summary_text and summary_text != text:
        diagnosis.append(f"文本中心句可概括为：{summary_text}")
    if len(text) < 30:
        diagnosis.append("文本较短，适合优先增强画面细节和动词力度。")
    elif len(text) > 220:
        diagnosis.append("文本较长，适合压缩重复表达并强化段落节奏。")
    if "，" not in text and "。" not in text and "\n" not in text:
        diagnosis.append("当前断句较少，可以通过停顿制造节奏层次。")
    return diagnosis

def build_polish_suggestions(text: str, keywords: list, emotion: dict) -> list:
    top_kw = [k["keyword"] for k in keywords[:4]]
    suggestions = []
    if top_kw:
        suggestions.append(f"保留「{'、'.join(top_kw[:3])}」等核心意象，避免润色时换掉文本的识别点。")
    suggestions.append("优先替换泛化形容词，改用具体动作、触感、光线或声音。")
    suggestions.append("检查每个比喻是否服务同一情绪，不要让意象互相抢焦点。")
    if emotion.get("intensity", 0) < 0.2:
        suggestions.append("当前情绪信号偏弱，可以增加一句带有明确态度或感受的收束句。")
    else:
        suggestions.append(f"围绕「{emotion.get('dominant', '情绪')}」强化节奏，避免语气突然转向。")
    return suggestions[:4]

def fallback_polish(text: str, keywords: list, emotion: dict) -> dict:
    top_kw = [k["keyword"] for k in keywords[:3]]
    anchor = "、".join(top_kw) if top_kw else "原有意象"
    conservative = text.replace("很长很长", "拖得更长").strip()
    creative = f"{text.strip()}\n\n{emotion.get('dominant', '某种情绪')}在{anchor}之间缓慢显影，像一束光穿过尚未命名的缝隙。"
    return {
        "method": "算法润色建议",
        "conservative": conservative,
        "creative": creative,
        "note": "DeepSeek 不可用或未启用时返回规则化润色结果。",
    }

def llm_polish(text: str, target_style: str, preserve_meaning: bool, keywords: list, emotion: dict, diagnosis: list, suggestions: list):
    top_kw = [k["keyword"] for k in keywords[:5]]
    prompt = f"""请润色下面这段中文创作文本。

原文：
{text}

目标风格：{target_style}
是否保留原意：{"必须保留原意" if preserve_meaning else "允许较大幅度改写"}
关键词：{'、'.join(top_kw)}
主导情绪：{emotion.get('dominant', '未知')}
诊断：{'；'.join(diagnosis)}
建议：{'；'.join(suggestions)}

请严格按以下格式输出，不要添加额外解释：
[保守润色]
在这里输出，尽量保留原文结构和意思。

[风格化润色]
在这里输出，可以更文学化，但不要偏离原文核心意象。
"""
    try:
        resp = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是一位中文文学编辑，擅长保留原意的文本润色、节奏优化和意象增强。"},
                {"role": "user", "content": prompt},
            ],
            temperature=LLM_POLISH_TEMPERATURE,
            max_tokens=650,
        )
        content = resp.choices[0].message.content.strip()
        conservative = content
        creative = content
        if "[保守润色]" in content and "[风格化润色]" in content:
            conservative = content.split("[保守润色]", 1)[1].split("[风格化润色]", 1)[0].strip()
            creative = content.split("[风格化润色]", 1)[1].strip()
        return {
            "method": "DeepSeek 文学润色",
            "conservative": conservative,
            "creative": creative,
            "note": "模型：deepseek-chat | 任务：保留原意 + 风格化润色",
        }
    except Exception:
        return None

# ===== 文本生成 =====
def template_generate(req: PipelineRequest, keywords: list, similar: list, emotion: str, art: dict, music: dict, rag_results: list = None):
    """算法模板生成 — 强制化用检索意象并标注来源"""
    top_kw = [k["keyword"] for k in keywords[:5]]
    citations = build_generation_citations(similar, rag_results)
    ref0 = similar[0] if similar else None
    ref1 = similar[1] if len(similar) > 1 else None
    phrase0 = citations[0]["adaptablePhrase"] if citations else ""
    phrase1 = citations[1]["adaptablePhrase"] if len(citations) > 1 else ""
    imagery = citations[0].get("detail", "").replace("借鉴意象「", "").replace("」", "") if citations else ""
    ref_title = ref0["title"] if ref0 else ""
    ref_author = ref0.get("author", "") if ref0 else ""

    if req.creationType == "古典诗":
        seed = phrase0 or (top_kw[0] if top_kw else "暮色")
        poems = [
            f"{seed[:2] if len(seed) >= 2 else '暮'}色{top_kw[1] if len(top_kw) > 1 else '苍茫'}笼四野\n{top_kw[2] if len(top_kw) > 2 else '孤'}心一片寄天涯\n{emotion}不是无端起\n化意{phrase1[:4] if phrase1 else '浮生'}半盏茶",
            f"{top_kw[0] if top_kw else '长夜'}漫漫独倚栏\n{phrase0[:6] if phrase0 else '月照孤影'}泪未干\n谁解{emotion}无限意\n{top_kw[4] if len(top_kw) > 4 else '秋风'}一叶落长安",
        ]
        content = poems[abs(hash(req.topic)) % len(poems)]
    elif req.creationType == "散文":
        echo = phrase0 or f"{top_kw[1] if len(top_kw) > 1 else '安静'}的时刻"
        content = (
            f"关于{top_kw[0] if top_kw else '时光'}的片段\n\n"
            f"我常常想起{echo}。{top_kw[2] if len(top_kw) > 2 else '风'}轻轻吹过，带走了说不清的东西。\n\n"
            f"就像《{ref_title or '那些诗'}》里写的那样——{phrase0 or '有些美只存在于消逝的瞬间'}。"
        )
    else:
        echo_line = phrase0 or f"{top_kw[2] if len(top_kw) > 2 else '风'}在{top_kw[3] if len(top_kw) > 3 else '窗外'}徘徊"
        poems = [
            f"{top_kw[0] if top_kw else '夜'}沉入{top_kw[1] if len(top_kw) > 1 else '深色'}的海\n{echo_line}\n像那些未说完的话\n在{emotion}里慢慢散开",
            f"把{top_kw[0] if top_kw else '思念'}叠成纸船\n放进{phrase1[:6] if phrase1 else '月光铺就的河'}\n它漂向{top_kw[2] if len(top_kw) > 2 else '远方'}\n那里有{imagery.split('、')[0] if imagery else '春天'}和未拆封的梦",
        ]
        content = poems[abs(hash(req.topic)) % len(poems)]

    citation_lines = [f"—— 化用自 {c['source']}：{c['detail']}" for c in citations[:2]]
    if citation_lines:
        content = content + "\n\n" + "\n".join(citation_lines)

    return {
        "method": "算法模板生成（检索化用）",
        "content": content,
        "citations": citations,
        "note": f"意象：{'、'.join(top_kw)} | 参考：《{ref_title}》·{ref_author} | 风格：{art['name']}",
    }

def llm_generate(req: PipelineRequest, keywords: list, similar: list, emotion: str, art: dict, music: dict, rag_results: list = None, feedback_hint: str = ""):
    """DeepSeek LLM 生成 — 融入 RAG 提取的参考诗结构信息，并标注化用来源"""
    top_kw = [k["keyword"] for k in keywords[:5]]
    max_tokens = LENGTH_TOKEN_MAP.get(req.lengthPreference, LLM_MAX_TOKENS)
    char_hint = LENGTH_CHAR_HINT.get(req.lengthPreference, "150–400 字")
    long_form = req.lengthPreference == "超长" or req.creationType in ("散文", "短篇片段") and req.lengthPreference in ("长", "超长")
    citations = build_generation_citations(similar, rag_results)
    refs = "\n".join([
        f"- 《{s['title']}》({s['type']})：{s['content'][:80]}"
        for s in similar[:3]
    ])

    rag_context = ""
    if rag_results:
        rag_parts = []
        for r in rag_results:
            rag_parts.append(
                f"■《{r['topic']}》({r['type']}·{r['author']})\n"
                f"  语义关联：{r.get('semanticSummary', '主题相近')}\n"
                f"  情感基调：{r['emotion']} | 核心意象：{'、'.join(r['keywords'])}\n"
                f"  可化用片段：「{r.get('adaptablePhrase', r['excerpt'][:20])}」\n"
                f"  原文片段：「{r['excerpt']}」"
            )
        rag_context = "\n".join(rag_parts)

    cite_instruction = ""
    if citations:
        cite_lines = [f"- {c['source']}：{c['detail']}（片段：{c['adaptablePhrase']}）" for c in citations[:2]]
        cite_instruction = "\n7. 正文结束后另起一行，按格式标注化用来源：\n" + "\n".join(cite_lines)

    user_pref = ""
    if feedback_hint:
        user_pref = f"\n用户历史偏好参考：{feedback_hint}\n"

    prompts = {
        "现代诗": f"""请创作一首现代诗，表达「{req.topic}」的主题。
{user_pref}
用户情感基调：{emotion}
用户输入关键词：{'、'.join(top_kw)}
目标艺术风格：{art['name']}
创作偏好：篇幅{req.lengthPreference}，语言风格{req.languageStyle}，押韵程度{req.rhymeLevel}，抽象程度{req.abstractionLevel}

════════ 知识库 RAG 参考（必须借鉴，不可忽略）════════
以下是通过语义检索从 5320 首诗歌中找到的相似作品，请至少化用其中 1-2 个意象或句式：
{rag_context if rag_context else refs}
════════════════════════════════

要求：
1. 4-8行，语言凝练有力
2. 必须融合上述参考诗歌的核心意象与情感质感，至少化用 1 处「可化用片段」
3. 保留用户关键词"{'、'.join(top_kw[:3])}"但用自己的方式重新演绎
4. 体现{emotion}的情感氛围和{art['name']}的风格
5. 遵守创作偏好，直接输出诗歌正文
6. 不要解释创作过程{cite_instruction}""",

        "古典诗": f"""请创作一首七言绝句/律诗，主题：「{req.topic}」。

情感：{emotion}
参考意象：{'、'.join(top_kw)}
风格：{art['name']}
创作偏好：篇幅{req.lengthPreference}，语言风格{req.languageStyle}，押韵程度{req.rhymeLevel}，抽象程度{req.abstractionLevel}

════════ 知识库 RAG 参考 ════════
{rag_context if rag_context else refs}
════════════════════════════════

要求：
1. 符合格律（平仄、押韵）
2. 借鉴参考诗歌的意境而不抄袭
3. 输出格式为4或8句
4. 直接输出诗句，不加解释""",

        "散文": f"""请写一段散文，主题：「{req.topic}」。

情感：{emotion}
参考意象：{'、'.join(top_kw)}
创作偏好：目标篇幅 {char_hint}，语言风格{req.languageStyle}，抽象程度{req.abstractionLevel}
{'【长文本模式】请分 2–4 个小节，每节有小标题，整体连贯叙事或抒情。' if long_form else ''}

════════ 知识库 RAG 参考 ════════
{rag_context if rag_context else refs}
════════════════════════════════

要求：借鉴参考作品的情感质感与意象，直接输出正文，不加解释{cite_instruction}""",

        "短篇片段": f"""请写一个短篇叙事片段，主题：「{req.topic}」。

情感：{emotion}
意象：{'、'.join(top_kw)}
创作偏好：目标篇幅 {char_hint}，语言风格{req.languageStyle}，抽象程度{req.abstractionLevel}
{'【长文本模式】可有场景、对话与心理描写，分节展开。' if long_form else ''}

参考作品：
{rag_context if rag_context else refs}

要求：融入参考作品的情感氛围，直接输出内容{cite_instruction}""",
    }

    prompt = prompts.get(req.creationType, prompts["现代诗"])

    try:
        resp = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是一位中国文学创作助手，精通诗歌、散文和短篇创作。请仔细分析参考作品中 NLP 提取的意象、情感和结构信息，将其作为创作养分而非简单模仿对象。"},
                {"role": "user", "content": prompt},
            ],
            temperature=LLM_TEMPERATURE,
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content.strip()
        if citations and "化用自" not in content:
            cite_footer = "\n".join([f"—— 化用自 {c['source']}：{c['detail']}" for c in citations[:2]])
            content = content + "\n\n" + cite_footer
        return {
            "method": f"DeepSeek LLM 生成 (RAG + 化用标注 · {req.lengthPreference})",
            "content": content,
            "citations": citations,
            "note": f"模型：{LLM_MODEL} | max_tokens={max_tokens} | 情感：{emotion} | RAG参考：{len(rag_results or [])}首",
        }
    except Exception as e:
        fallback = template_generate(req, keywords, similar, emotion, art, music, rag_results)
        return {
            "method": f"LLM 调用失败，降级为算法模板 ({str(e)[:50]})",
            "content": fallback["content"],
            "citations": fallback.get("citations", citations),
            "note": "DeepSeek API 不可用，已自动切换为检索化用模板",
        }

# ===== 对话模型 =====
class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    sessionId: str = ""
    clientId: str = ""

# ===== 灵感对话接口 =====
INSPIRATION_SYSTEM_PROMPT = """你是一个名叫「灵感菌」的情绪感知与创作灵感小助手。

你的核心任务：
1. **共情倾听**：首先感知用户的情绪状态，用温暖的理解回应
2. **情绪引导**：帮助用户梳理情绪，让情绪成为创作的燃料
3. **灵感激发**：根据用户表达的情绪和话题，给予创意启发（诗歌意象、画面联想、艺术风格建议等）
4. **知识引用**：适时引用古诗词或文学片段来呼应或升华用户的情感

风格要求：
- 语气温暖、真诚，像深夜电台里的知心朋友
- 回复简洁（100字左右），不要长篇大论
- 适当使用 emoji 增加亲和力
- 当用户表达创作意图时，主动提供意象建议和风格参考
- 永远保持正向、包容、不评判的态度"""

class ChatSessionCreate(BaseModel):
    clientId: str
    title: str = "新对话"


@app.get("/api/chat/sessions")
def api_list_chat_sessions(clientId: str, limit: int = 40, user: dict | None = Depends(get_optional_user)):
    if not clientId and not user:
        return {"sessions": []}
    return {"sessions": list_chat_sessions(clientId or "", limit=limit, user_id=user["id"] if user else None)}


@app.post("/api/chat/sessions")
def api_create_chat_session(req: ChatSessionCreate, user: dict | None = Depends(get_optional_user)):
    return create_chat_session(req.clientId, req.title, user_id=user["id"] if user else None)


@app.get("/api/chat/sessions/{session_id}")
def api_get_chat_session(session_id: str, clientId: str):
    session = get_chat_session(session_id, clientId)
    if not session:
        return {"error": "session not found"}
    return session


@app.delete("/api/chat/sessions/{session_id}")
def api_delete_chat_session(session_id: str, clientId: str):
    ok = delete_chat_session(session_id, clientId)
    return {"deleted": ok}


@app.post("/api/chat")
def chat(req: ChatRequest, user: dict | None = Depends(get_optional_user)):
    """灵感对话：NLP 情绪分析 + DeepSeek 灵感助手 + 历史持久化"""
    session_id = req.sessionId
    if req.clientId and not session_id:
        session_id = create_chat_session(req.clientId, user_id=user["id"] if user else None)["id"]

    seg = segment(req.message)
    kw = extract_keywords(seg["words"], 5)
    entities = extract_entities(req.message)
    emotion = analyze_sentiment(seg["words"], full_text=req.message)
    nlp_payload = {
        "segmentation": seg,
        "keywords": kw,
        "emotion": emotion,
        "entities": entities,
    }

    if session_id:
        history = get_chat_history_for_llm(session_id, limit=20)
    else:
        history = req.history

    messages = [{"role": "system", "content": INSPIRATION_SYSTEM_PROMPT}]
    for h in history[-10:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": req.message})

    try:
        resp = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.9,
            max_tokens=400,
        )
        reply = resp.choices[0].message.content.strip()
        llm_used = True
    except Exception:
        top_kw = [k["keyword"] for k in kw[:3]]
        templates = [
            f"我感受到了你内心的{emotion['dominant']}。{'、'.join(top_kw) if top_kw else '你的话语'}让我想起一句诗：「此情可待成追忆，只是当时已惘然。」愿意和我聊聊更多吗？🌙",
            f"你的情绪里有一种{emotion['dominant']}的质感。也许可以试试把这些感受写下来——文字是最好的容器。需要一些意象灵感吗？✨",
            f"听你说话，我仿佛看到了{'、'.join(top_kw[:2]) if len(top_kw)>=2 else '某个画面'}。创作就在这些细微的感知里。想不想一起探索？🎨",
        ]
        import random
        reply = random.choice(templates)
        llm_used = False

    if session_id:
        append_chat_message(session_id, "user", req.message)
        append_chat_message(session_id, "assistant", reply, nlp=nlp_payload, llm_used=llm_used)
        session = get_chat_session(session_id, req.clientId) if req.clientId else None
        title = session["title"] if session else "新对话"
    else:
        title = None

    return {
        "reply": reply,
        "sessionId": session_id,
        "sessionTitle": title,
        "llmUsed": llm_used,
        "nlp": nlp_payload,
    }

# ===== 启动入口 =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
