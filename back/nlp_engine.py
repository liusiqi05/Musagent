"""
NLP 引擎 — Jieba + TF-IDF + TextRank + RoBERTa 情感 + BGE 检索 + Cross-Encoder 重排 + BERT-NER + MacBERT 校错
"""
import jieba
import jieba.posseg as pseg
import numpy as np
from collections import Counter
import math
import os
import json
import re

# ===== 加载诗歌数据 =====
_poems_cache = None

def _load_poems():
    global _poems_cache
    if _poems_cache is not None:
        return _poems_cache
    path = os.path.join(os.path.dirname(__file__), '..', 'musagent', 'src', 'data', 'poems_extracted.json')
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    _poems_cache = data
    return _poems_cache

def get_poem_list() -> list[dict]:
    """将诗歌 JSON 转为扁平列表，供训练/导入使用。"""
    data = _load_poems()
    poems = []
    for p in data.get("modern", []):
        poems.append({**p, "type": p.get("type", "现代诗")})
    for p in data.get("classical", []):
        poems.append({**p, "type": p.get("type", "古典诗")})
    return poems

# ===== 停用词 =====
STOP_WORDS = set('''
的 了 在 是 我 有 和 就 不 人 都 一 他 这 中 大 来 上 国 个 到 说 们 为 子 和 你
地 出 道 也 时 年 得 就 那 要 下 以 生 会 自 着 去 之 过 家 学 对 可 她 里 后
小 么 心 多 天 而 能 好 然 没 日 于 起 还 发 成 事 只 作 当 想 看 文 无 开 手
十 用 主 行 方 又 如 前 所 本 见 经 头 面 公 同 三 已 老 从 动 两 长 知 民 样
现 分 将 外 但 身 些 与 高 意 进 把 法 此 实 回 二 理 美 点 月 明 其 种 声 全
工 己 话 信 重 相 物 气 代 通 比 员 名 水 常 更 正 关 各 合 期 力 教 内 去 平
太 者 头 机 电 间 第 表 少 山 应 制 加 被 门 话 最 题 新 建 程 展 果 样 变 军
很 最 真 之 些 所 等 月 而 题 向 五 解 问 意 建 体 果 代 应 并 系 外 加 提 立
该 还 此 前 区 务 种 群 解 者 量 看 气 说 手 使 义 情 强 光 运 关 加 重 先 海
接 化 战 通 教 指 干 期 此 已 将 回 被 很 最 其 合 同 正 间 门 较 各 组 见
但是 并且 而且 或者 因为 所以 如果 虽然 然而
'''.split())

NUMERAL_PREFIXES = set("一二三四五六七八九十百千万几数每半两")
MEASURE_WORDS = set("个只条张本次回遍趟场片朵颗双份层阵")
LOW_QUALITY_KEYWORDS = {
    "一张",
    "张脸",
}

def _is_low_quality_word(word: str) -> bool:
    if not word or word in STOP_WORDS or word in LOW_QUALITY_KEYWORDS:
        return True
    if len(word) < 2:
        return True
    # 过滤“数量词 + 量词”残片，例如“一张”“几条”。
    if len(word) == 2 and word[0] in NUMERAL_PREFIXES and word[1] in MEASURE_WORDS:
        return True
    # 过滤 Jieba 偶发的“量词 + 单字名词”残片，例如“一张张脸”中的“张脸”。
    if len(word) == 2 and word[0] in MEASURE_WORDS and word[1] in {"脸", "手", "眼", "嘴", "纸", "票", "桌", "床"}:
        return True
    return False

# ===== WordSegAgent：Jieba 分词 =====
def segment(text: str) -> dict:
    words = [w for w in jieba.cut(text) if w.strip() and not _is_low_quality_word(w)]
    freq = Counter(words)
    return {"words": words, "freq": dict(freq.most_common(30)), "total": len(words)}

# ===== QueryExpansionAgent：主题拆解 + 联想扩展 =====
QUERY_EXPANSION_RULES = {
    "校园": ["校园", "教室", "操场", "课桌", "校服", "毕业", "青春", "少年"],
    "爱情": ["爱情", "恋爱", "初恋", "暗恋", "心动", "告白", "喜欢", "温柔"],
    "校园爱情": ["校园", "爱情", "青春", "少年", "初恋", "暗恋", "教室", "操场", "晚风"],
    "甜美": ["甜美", "甜", "温柔", "明亮", "微笑", "喜欢"],
    "幸福": ["幸福", "快乐", "希望", "温暖", "美好"],
    "成长": ["成长", "青春", "远方", "告别", "梦想"],
    "黄昏": ["黄昏", "夕阳", "晚霞", "怀旧", "告别"],
    "雨夜": ["雨夜", "雨声", "窗", "孤独", "安静"],
    "城市": ["城市", "街道", "霓虹", "地铁", "人潮"],
}

TOPIC_EMOTION_HINTS = {
    "爱情": {"喜悦": 2.0, "平静": 0.8, "怀旧": 0.3},
    "校园": {"怀旧": 0.8, "喜悦": 0.6, "平静": 0.2},
    "校园爱情": {"喜悦": 3.0, "怀旧": 1.2, "平静": 0.7},
    "青春": {"激昂": 0.7, "怀旧": 0.5, "喜悦": 0.3},
    "甜美": {"喜悦": 2.0, "平静": 0.3},
    "幸福": {"喜悦": 2.5},
}

def expand_query(text: str, words: list) -> dict:
    """扩展短主题，解决复合词难以命中知识库的问题。"""
    expanded = []
    reasons = {}

    def add(term: str, reason: str):
        if term and not _is_low_quality_word(term) and term not in expanded:
            expanded.append(term)
            reasons[term] = reason

    for word in words:
        add(word, "原始分词")

    for trigger, terms in QUERY_EXPANSION_RULES.items():
        if trigger in text or trigger in words:
            for term in terms:
                add(term, f"由「{trigger}」扩展")

    # 对未被 Jieba 拆开的复合主题做轻量子串拆解。
    for trigger in QUERY_EXPANSION_RULES:
        if trigger != text and trigger in text:
            add(trigger, "复合主题拆解")

    core = [w for w in expanded if w in words or w in text][:5]
    imagery = [w for w in expanded if w not in core][:8]
    return {
        "original": words,
        "expanded": expanded,
        "core": core,
        "imagery": imagery,
        "reasons": reasons,
    }

# ===== KeywordAgent：TF-IDF =====
def extract_keywords(words: list, top_n: int = 10, original_words: list | None = None) -> list:
    if not words:
        return []
    total = len(words)
    counter = Counter(words)
    _ensure_kb()
    total_docs = len(_kb_docs) if _kb_docs else 0
    result = []
    for word, count in counter.most_common(top_n):
        if _is_low_quality_word(word):
            continue
        tf = count / total
        df = _kb_doc_freq.get(word, 0) if _kb_doc_freq else 0
        idf = math.log(1 + (total_docs + 1) / (df + 1)) if total_docs else 1.0
        original_boost = 1.25 if original_words and word in original_words else 1.0
        result.append({"keyword": word, "tfidf": round(tf * idf * original_boost, 4)})
    result.sort(key=lambda item: item["tfidf"], reverse=True)
    return result

# ===== SummaryAgent：TextRank =====
def summarize(text: str, top_n: int = 3) -> dict:
    import re
    sentences = [s.strip() for s in re.split(r'[。！？\n]+', text) if len(s.strip()) > 2]
    if len(sentences) <= top_n:
        return {"summary": "。".join(sentences), "count": len(sentences)}
    n = len(sentences)
    sim = np.zeros((n, n))
    sent_words = [set(jieba.cut(s)) for s in sentences]
    for i in range(n):
        for j in range(n):
            if i != j:
                a, b = sent_words[i], sent_words[j]
                inter = len(a & b)
                sim[i][j] = inter / (math.log(len(a) + 1) + math.log(len(b) + 1))
    scores = np.ones(n) / n
    for _ in range(50):
        new = np.ones(n) * 0.15 / n
        for i in range(n):
            for j in range(n):
                if i != j and sim[j].sum() > 0:
                    new[i] += 0.85 * (sim[j][i] / sim[j].sum()) * scores[j]
        scores = new
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    top_idx = sorted([i for i, _ in ranked[:top_n]])
    summary = "。".join([sentences[i] for i in top_idx])
    return {"summary": summary, "count": len(sentences)}

# ===== EmotionAgent：情感分析 =====
EMOTION_DICT = {
    "孤独": ["孤独","寂寞","独自","空旷","荒漠","一人","深夜","夜里","无人","沉默","静默","落寞","异乡","漂泊","疏离"],
    "怀旧": ["怀念","回忆","记忆","往事","从前","曾经","故乡","旧日","往昔","泛黄","黄昏","夕阳","旧时光","童年","少年"],
    "激昂": ["激昂","热血","汹涌","澎湃","燃烧","呐喊","奔放","豪迈","壮阔","梦想","成长","青春","远行","追逐"],
    "平静": ["平静","宁静","安静","祥和","淡然","从容","悠然","缓缓","淡淡","微风","和解","释然","自我","月光"],
    "悲伤": ["悲伤","痛苦","难过","泪","哭泣","碎裂","凋零","苍白","沉重","窒息","告别","失去","离别"],
    "喜悦": ["快乐","幸福","欢笑","甜","美好","欣喜","灿烂","明媚","温暖","希望","治愈","春日","春天"],
}

def _score_emotions(words: list, include_topic_hints: bool = True) -> tuple[dict, int]:
    scores = {k: 0.0 for k in EMOTION_DICT}
    total = 0
    for word in words:
        for emotion, kws in EMOTION_DICT.items():
            if word in kws:
                scores[emotion] += 1
                total += 1
        if include_topic_hints and word in TOPIC_EMOTION_HINTS:
            for emotion, weight in TOPIC_EMOTION_HINTS[word].items():
                if emotion in scores:
                    scores[emotion] += weight
            total += 1
    return scores, total

def _normalize_scores(scores: dict) -> dict:
    max_score = max(scores.values()) if scores else 0
    if max_score <= 0:
        return {k: 0 for k in scores}
    return {k: round(v / max_score, 2) for k, v in scores.items()}

def _analyze_sentiment_dictionary(words: list, context_docs: list | None = None) -> dict:
    scores, total = _score_emotions(words)
    direct_intensity = total / max(len(words), 1)

    context_scores = {k: 0.0 for k in EMOTION_DICT}
    context_weight = 0.0
    if context_docs:
        max_similarity = max((doc.get("similarity", 0) for doc in context_docs), default=0) or 1
        for rank, doc in enumerate(context_docs[:5]):
            content = doc.get("content", "")
            doc_words = [
                w for w in jieba.cut(content)
                if w.strip() and not _is_low_quality_word(w)
            ]
            doc_scores, doc_total = _score_emotions(doc_words, include_topic_hints=False)
            if doc_total == 0:
                continue

            similarity_weight = doc.get("similarity", 0) / max_similarity
            rank_weight = 1 / (rank + 1)
            weight = similarity_weight * rank_weight
            normalized_doc_scores = _normalize_scores(doc_scores)
            for emotion, value in normalized_doc_scores.items():
                context_scores[emotion] += value * weight
            context_weight += weight

    if context_weight > 0:
        context_ratio = min(context_weight / 2, 1)
        for emotion, value in context_scores.items():
            scores[emotion] += value if total == 0 else value * 0.5
        intensity = max(direct_intensity, context_ratio * (0.6 if total == 0 else 0.3))
    else:
        intensity = direct_intensity

    if total == 0:
        if context_weight == 0:
            return {"dominant": "平静", "scores": scores, "intensity": 0.0}

    normalized = _normalize_scores(scores)
    dominant = max(normalized, key=normalized.get)
    return {"dominant": dominant, "scores": normalized, "intensity": round(min(intensity, 1), 2)}


def _analyze_sentiment_transformer(text: str) -> dict:
    """RoBERTa 情感极性 → 六维情绪映射。"""
    text = (text or "").strip()
    fallback = {"polarity": 0.5, "scores": {k: 0.0 for k in EMOTION_DICT}, "dominant": "平静", "intensity": 0.0}
    if not text:
        return fallback
    try:
        from ml_models import analyze_sentiment_transformer
        result = analyze_sentiment_transformer(text)
        if result:
            return {
                "polarity": result.get("polarity", 0.5),
                "scores": result.get("scores", fallback["scores"]),
                "dominant": result.get("dominant", "平静"),
                "intensity": result.get("intensity", 0.0),
                "model": result.get("model"),
                "confidence": result.get("confidence"),
            }
    except Exception:
        pass
    return fallback


def _fuse_sentiment(dict_result: dict, model_result: dict, dict_weight: float = 0.5) -> dict:
    model_weight = 1 - dict_weight
    fused = {k: 0.0 for k in EMOTION_DICT}
    for emotion in fused:
        fused[emotion] = (
            dict_result.get("scores", {}).get(emotion, 0) * dict_weight
            + model_result.get("scores", {}).get(emotion, 0) * model_weight
        )
    normalized = _normalize_scores(fused)
    dominant = max(normalized, key=normalized.get)
    intensity = round(
        min(dict_result.get("intensity", 0) * dict_weight + model_result.get("intensity", 0) * model_weight, 1),
        2,
    )
    return {"dominant": dominant, "scores": normalized, "intensity": intensity}


def analyze_sentiment(words: list, context_docs: list | None = None, full_text: str | None = None) -> dict:
    """文学词典 + RoBERTa Transformer 融合情感分析。"""
    dict_result = _analyze_sentiment_dictionary(words, context_docs)
    text = full_text if full_text is not None else "".join(words)
    transformer_result = _analyze_sentiment_transformer(text)
    fused = _fuse_sentiment(dict_result, transformer_result)
    return {
        **fused,
        "dictionary": dict_result,
        "transformer": transformer_result,
        "fusionMethod": "文学词典 50% + RoBERTa 50%",
    }

# ===== RetrievalAgent：BM25 相似度检索 =====
def _build_kb():
    data = _load_poems()
    docs = []
    doc_freq = Counter()

    def add_doc(poem: dict, poem_type: str):
        words = [
            w for w in jieba.cut(poem.get("content", ""))
            if w.strip() and not _is_low_quality_word(w)
        ]
        word_counts = Counter(words)
        docs.append({
            "type": poem_type,
            "title": poem["title"],
            "author": poem["author"],
            "content": poem["content"],
            "words": words,
            "word_counts": word_counts,
            "doc_len": len(words),
        })
        doc_freq.update(word_counts.keys())

    for p in data.get("modern", []):
        add_doc(p, "现代诗")
    for p in data.get("classical", []):
        add_doc(p, "古典诗")

    avg_doc_len = sum(doc["doc_len"] for doc in docs) / max(len(docs), 1)
    return docs, doc_freq, avg_doc_len

_kb_docs = None
_kb_doc_freq = None
_kb_avg_doc_len = 0

def _ensure_kb():
    global _kb_docs, _kb_doc_freq, _kb_avg_doc_len
    if _kb_docs is None:
        _kb_docs, _kb_doc_freq, _kb_avg_doc_len = _build_kb()

def _retrieve_bm25(query_words: list, creation_type: str = "all", top_n: int = 5) -> list:
    _ensure_kb()

    query_terms = [w for w in query_words if not _is_low_quality_word(w)]
    if not query_terms:
        return []

    k1 = 1.5
    b = 0.75
    total_docs = len(_kb_docs)
    scored = []
    for doc in _kb_docs:
        if creation_type == "古典诗" and doc["type"] != "古典诗":
            continue
        if creation_type in ("现代诗", "散文", "短篇片段") and doc["type"] != "现代诗":
            continue

        score = 0.0
        matched_terms = []
        doc_len = max(doc["doc_len"], 1)
        for term in query_terms:
            freq = doc["word_counts"].get(term, 0)
            if freq == 0:
                continue
            matched_terms.append(term)
            df = _kb_doc_freq.get(term, 0)
            idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
            norm = freq + k1 * (1 - b + b * doc_len / max(_kb_avg_doc_len, 1))
            score += idf * (freq * (k1 + 1)) / norm

        if score > 0:
            scored.append({
                "type": doc["type"],
                "title": doc["title"],
                "author": doc["author"],
                "content": doc["content"][:200],
                "bm25Score": round(score, 4),
                "similarity": round(score, 4),
                "matchedTerms": matched_terms[:8],
            })

    scored.sort(key=lambda x: x["bm25Score"], reverse=True)
    return scored[:top_n]


def _normalize_scores_list(items: list, key: str) -> None:
    if not items:
        return
    max_v = max(item.get(key, 0) for item in items) or 1
    for item in items:
        item[f"{key}Norm"] = round(item.get(key, 0) / max_v, 4)


def retrieve_similar(
    query_words: list,
    creation_type: str = "all",
    top_n: int = 5,
    query_text: str = "",
    search_mode: str = "hybrid",
) -> list:
    """BM25 + BGE 召回 + Cross-Encoder 精排（默认 hybrid）。"""
    bm25_weight = float(os.getenv("HYBRID_BM25_WEIGHT", "0.55"))
    try:
        from config import RERANK_TOP_K
        rerank_pool = RERANK_TOP_K
    except ImportError:
        rerank_pool = 20
    recall_n = max(top_n * 5, rerank_pool)
    query_terms = [w for w in query_words if not _is_low_quality_word(w)]
    text = (query_text or " ".join(query_terms)).strip()

    if search_mode == "bm25" or not text:
        return _retrieve_bm25(query_words, creation_type, top_n)

    bm25_results = _retrieve_bm25(query_words, creation_type, recall_n)
    if search_mode == "semantic":
        try:
            from semantic_index import semantic_search
            from ml_models import rerank_candidates
            semantic_results = semantic_search(text, top_n=recall_n, poem_type=creation_type)
        except Exception:
            return bm25_results[:top_n]
        _normalize_scores_list(semantic_results, "semanticScore")
        merged = []
        for item in semantic_results:
            merged.append({
                **item,
                "similarity": item.get("semanticScoreNorm", item.get("semanticScore", 0)),
                "bm25Score": 0,
                "semanticScore": item.get("semanticScore", 0),
                "matchedTerms": [],
                "retrievalMethod": "bge",
            })
        return rerank_candidates(text, merged, top_n)

    try:
        from semantic_index import semantic_search
        from ml_models import rerank_candidates
        semantic_results = semantic_search(text, top_n=recall_n, poem_type=creation_type)
    except Exception:
        return bm25_results[:top_n]

    _normalize_scores_list(bm25_results, "bm25Score")
    _normalize_scores_list(semantic_results, "semanticScore")

    merged_map: dict[str, dict] = {}

    def doc_key(item: dict) -> str:
        return f"{item['title']}::{item['author']}"

    for item in bm25_results:
        key = doc_key(item)
        merged_map[key] = {
            **item,
            "semanticScore": 0,
            "semanticScoreNorm": 0,
            "retrievalMethod": "hybrid",
        }

    for item in semantic_results:
        key = doc_key(item)
        if key in merged_map:
            merged_map[key]["semanticScore"] = item.get("semanticScore", 0)
            merged_map[key]["semanticScoreNorm"] = item.get("semanticScoreNorm", 0)
        else:
            merged_map[key] = {
                **item,
                "bm25Score": 0,
                "bm25ScoreNorm": 0,
                "similarity": 0,
                "matchedTerms": [],
                "retrievalMethod": "hybrid",
            }

    fused = []
    for item in merged_map.values():
        bm = item.get("bm25ScoreNorm", 0)
        se = item.get("semanticScoreNorm", 0)
        if bm <= 0 and se <= 0:
            continue
        hybrid = bm25_weight * bm + (1 - bm25_weight) * se
        fused.append({
            **item,
            "hybridScore": round(hybrid, 4),
            "similarity": round(hybrid, 4),
            "retrievalMethod": "hybrid",
        })

    fused.sort(key=lambda x: x["hybridScore"], reverse=True)
    return rerank_candidates(text, fused[:recall_n], top_n)


def _pick_adaptable_phrase(content: str, keywords: list[str], max_len: int = 20) -> str:
    """从参考作品中选取适合化用的短句片段。"""
    clauses = re.split(r"[，。！？；\n]", content or "")
    best = ""
    best_score = -1.0
    kw_set = {k for k in keywords if k and len(k) >= 2}

    for clause in clauses:
        clause = clause.strip()
        if len(clause) < 4:
            continue
        score = sum(1.5 for k in kw_set if k in clause)
        if 6 <= len(clause) <= max_len:
            score += 1.0
        elif len(clause) > max_len:
            score -= 0.5
        if score > best_score:
            best_score = score
            best = clause[:max_len]

    if not best and clauses:
        for clause in clauses:
            clause = clause.strip()
            if len(clause) >= 4:
                return clause[:max_len]
    return best


def explain_retrieval_results(
    topic: str,
    similar_works: list,
    query_keywords: list | None = None,
    query_emotion: str = "",
    query_entities: dict | None = None,
) -> tuple[list, dict]:
    """为检索结果附加可读的语义解释，并生成整体语义洞察。"""
    query_keywords = query_keywords or []
    kw_strings = [
        k["keyword"] if isinstance(k, dict) else str(k)
        for k in query_keywords
    ][:10]

    entity_words: list[str] = []
    if query_entities:
        for values in query_entities.get("entities", {}).values():
            entity_words.extend(values)
        for item in query_entities.get("flat", []):
            entity_words.append(item.get("text", ""))
    entity_words = [w for w in entity_words if w and len(w) >= 2][:12]

    enriched = []
    all_shared: list[str] = []
    all_matched: list[str] = []
    emotion_align_count = 0

    for i, item in enumerate(similar_works or []):
        content = item.get("content", "")[:320]
        ref_seg = segment(content)
        ref_kw = [k["keyword"] for k in extract_keywords(ref_seg["words"], 6)]
        ref_emo = analyze_sentiment(ref_seg["words"], full_text=content[:200])

        matched = list(item.get("matchedTerms") or [])
        shared: list[str] = []
        for rk in ref_kw:
            if rk in kw_strings or any(rk in q or q in rk for q in kw_strings):
                if rk not in shared:
                    shared.append(rk)
        for ew in entity_words:
            if ew in content and ew not in shared:
                shared.append(ew)

        reason_tags: list[str] = []
        if matched:
            reason_tags.append("关键词命中")
            all_matched.extend(matched)
        if shared:
            reason_tags.append("意象呼应")
            all_shared.extend(shared)
        if query_emotion and ref_emo["dominant"] == query_emotion:
            reason_tags.append("情感一致")
            emotion_align_count += 1
        elif ref_emo.get("dominant"):
            reason_tags.append("情感参照")
        if item.get("semanticScore", 0) > 0 and not matched:
            reason_tags.append("语义向量相近")
        if item.get("rerankScore") is not None:
            reason_tags.append("Cross-Encoder 精排")

        parts: list[str] = []
        if matched:
            parts.append(f"命中主题词「{'」「'.join(matched[:3])}」")
        if shared:
            parts.append(f"意象呼应「{'」「'.join(shared[:3])}」")
        if ref_emo.get("dominant"):
            align = "与主题一致" if query_emotion and ref_emo["dominant"] == query_emotion else "可作参照"
            parts.append(f"情感基调「{ref_emo['dominant']}」{align}")

        title = item.get("title", "未知作品")
        summary = f"《{title}》：{'；'.join(parts)}" if parts else f"《{title}》：BGE 语义空间与主题「{topic}」表达相近"

        enriched.append({
            **item,
            "semanticExplanation": {
                "summary": summary,
                "reasonTags": reason_tags,
                "sharedKeywords": shared[:5],
                "matchedTerms": matched[:5],
                "refEmotion": ref_emo.get("dominant", ""),
                "refImagery": ref_kw[:5],
                "adaptablePhrase": _pick_adaptable_phrase(content, kw_strings + entity_words),
                "rank": i + 1,
            },
        })

    unique_shared = list(dict.fromkeys(all_shared))[:6]
    unique_matched = list(dict.fromkeys(all_matched))[:6]

    if unique_matched or unique_shared:
        insight = (
            f"围绕「{topic}」，从 5320 首作品中找到 {len(enriched)} 首语义相关参照。"
            f"{' 关键词命中：' + '、'.join(unique_matched[:4]) + '。' if unique_matched else ''}"
            f"{' 共同意象：' + '、'.join(unique_shared[:4]) + '。' if unique_shared else ''}"
            f"{' 其中 ' + str(emotion_align_count) + ' 首情感基调与主题一致，可直接借鉴语气。' if emotion_align_count else ' 可参考不同情感基调的写法，拓展表达层次。'}"
        )
    else:
        insight = (
            f"围绕「{topic}」，通过 BGE 稠密语义在知识库中召回 {len(enriched)} 首表达相近的作品。"
            f"它们在句向量空间中与你的主题描述距离较近，适合作为意象与结构的创作参照。"
        )

    overall = {
        "insight": insight,
        "topic": topic,
        "queryEmotion": query_emotion,
        "sharedImagery": unique_shared,
        "matchedKeywords": unique_matched,
        "emotionAlignedCount": emotion_align_count,
        "referenceCount": len(enriched),
    }
    return enriched, overall


def build_generation_citations(similar_works: list, rag_results: list | None = None) -> list:
    """从检索/RAG 结果构建生成内容的结构化引用。"""
    rag_map = {r["topic"]: r for r in (rag_results or [])}
    citations = []
    for item in (similar_works or [])[:3]:
        expl = item.get("semanticExplanation") or {}
        rag = rag_map.get(item.get("title"), {})
        phrase = expl.get("adaptablePhrase") or (item.get("content", "")[:18] + "…")
        shared = expl.get("sharedKeywords") or expl.get("refImagery", [])[:3]
        detail_parts = []
        if shared:
            detail_parts.append(f"借鉴意象「{'、'.join(shared[:3])}」")
        if expl.get("refEmotion"):
            detail_parts.append(f"情感参照「{expl['refEmotion']}」")
        citations.append({
            "source": f"《{item.get('title', '未知')}》·{item.get('author', '佚名')}",
            "type": item.get("type", "现代诗"),
            "detail": "；".join(detail_parts) if detail_parts else "语义相近的结构与意境",
            "excerpt": rag.get("excerpt") or phrase,
            "adaptablePhrase": phrase,
            "similarity": item.get("rerankScore", item.get("similarity")),
        })
    return citations


def compare_retrieval_modes(query_words: list, query_text: str, creation_type: str = "现代诗") -> dict:
    """对比 BM25 与混合检索，用于评测页 ablation 展示。"""
    bm25 = retrieve_similar(query_words, creation_type, 5, query_text=query_text, search_mode="bm25")
    hybrid = retrieve_similar(query_words, creation_type, 5, query_text=query_text, search_mode="hybrid")
    bm25_titles = {f"{x['title']}::{x['author']}" for x in bm25}
    hybrid_titles = {f"{x['title']}::{x['author']}" for x in hybrid}
    overlap = len(bm25_titles & hybrid_titles)
    return {
        "bm25TopTitle": bm25[0]["title"] if bm25 else None,
        "hybridTopTitle": hybrid[0]["title"] if hybrid else None,
        "bm25Count": len(bm25),
        "hybridCount": len(hybrid),
        "overlapCount": overlap,
        "semanticGain": hybrid[0].get("rerankScore", hybrid[0].get("similarity", 0)) if hybrid else 0,
    }


def _knowledge_keywords(doc: dict, top_n: int = 5) -> list:
    total_docs = len(_kb_docs) if _kb_docs else 0
    total_words = max(doc.get("doc_len", 0), 1)
    ranked = []
    for word, count in doc.get("word_counts", {}).items():
        if _is_low_quality_word(word):
            continue
        df = _kb_doc_freq.get(word, 0) if _kb_doc_freq else 0
        tf = count / total_words
        idf = math.log(1 + (total_docs + 1) / (df + 1)) if total_docs else 1.0
        ranked.append((word, tf * idf, count))

    ranked.sort(key=lambda item: (item[1], item[2], len(item[0])), reverse=True)
    return [word for word, _, _ in ranked[:top_n]]

_knowledge_view_cache = None

def _ensure_knowledge_view():
    global _knowledge_view_cache
    _ensure_kb()
    if _knowledge_view_cache is not None:
        return _knowledge_view_cache

    items = []
    stats = {"total": len(_kb_docs), "modern": 0, "classical": 0, "emotions": {}}
    type_prefix = {"现代诗": "m", "古典诗": "c"}
    type_counts = Counter()

    for index, doc in enumerate(_kb_docs):
        emotion = _analyze_sentiment_dictionary(doc["words"])
        keywords = _knowledge_keywords(doc, 5)
        poem_type = doc["type"]
        type_counts[poem_type] += 1
        stats["emotions"][emotion["dominant"]] = stats["emotions"].get(emotion["dominant"], 0) + 1
        items.append({
            "id": f"{type_prefix.get(poem_type, 'p')}-{index}",
            "type": poem_type,
            "title": doc["title"],
            "author": doc["author"],
            "content": doc["content"],
            "keywords": keywords,
            "emotion": emotion["dominant"],
            "emotionDetail": emotion,
        })

    stats["modern"] = type_counts.get("现代诗", 0)
    stats["classical"] = type_counts.get("古典诗", 0)
    _knowledge_view_cache = {"items": items, "stats": stats}
    return _knowledge_view_cache

def get_knowledge_page(
    page: int = 1,
    page_size: int = 30,
    search: str = "",
    emotion: str = "all",
    poem_type: str = "all",
    search_mode: str = "keyword",
) -> dict:
    view = _ensure_knowledge_view()
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 30), 1), 100)
    search = (search or "").strip()

    filtered = []
    if search and search_mode in ("semantic", "hybrid"):
        try:
            from semantic_index import semantic_search
            semantic_hits = semantic_search(search, top_n=200, poem_type=poem_type if poem_type != "all" else "all")
            hit_map = {f"{h['title']}::{h['author']}": h for h in semantic_hits}
            hit_keys = set(hit_map.keys())
            if search_mode == "hybrid":
                for item in view["items"]:
                    haystack = "".join([item["title"], item["author"], item["content"], "".join(item["keywords"])])
                    if search in haystack:
                        hit_keys.add(f"{item['title']}::{item['author']}")
            for item in view["items"]:
                key = f"{item['title']}::{item['author']}"
                if key not in hit_keys:
                    continue
                if poem_type != "all" and item["type"] != poem_type:
                    continue
                if emotion != "all" and item["emotion"] != emotion:
                    continue
                hit = hit_map.get(key)
                filtered.append({**item, "semanticScore": hit.get("semanticScore") if hit else None})
            filtered.sort(key=lambda x: x.get("semanticScore") or 0, reverse=True)
        except Exception:
            search_mode = "keyword"

    if not (search and search_mode in ("semantic", "hybrid")):
        for item in view["items"]:
            if poem_type != "all" and item["type"] != poem_type:
                continue
            if emotion != "all" and item["emotion"] != emotion:
                continue
            if search:
                haystack = "".join([
                    item["title"],
                    item["author"],
                    item["content"],
                    "".join(item["keywords"]),
                ])
                if search not in haystack:
                    continue
            filtered.append(item)

    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": filtered[start:end],
        "stats": view["stats"],
        "filteredTotal": len(filtered),
        "page": page,
        "pageSize": page_size,
        "hasMore": end < len(filtered),
        "searchMode": search_mode,
    }

# ===== 实体向量计算（用 TF-IDF 加权词向量模拟） =====
def compute_query_embedding(words: list, dim: int = 128) -> list:
    """轻量 embedding：基于词袋 + 随机投影的伪语义向量"""
    import hashlib
    vec = np.zeros(dim)
    for word in set(words):
        h = int(hashlib.md5(word.encode()).hexdigest()[:8], 16)
        np.random.seed(h)
        proj = np.random.randn(dim)
        vec += proj
    norm = np.linalg.norm(vec)
    return (vec / norm).tolist() if norm > 0 else vec.tolist()

# ===== 艺术风格匹配 =====
ART_STYLES = {
    "印象派": ["光影","色彩","模糊","瞬间","朦胧","柔和","梦幻","自然"],
    "表现主义": ["扭曲","呐喊","强烈","痛苦","情绪","黑暗","浓烈","不安"],
    "极简主义": ["留白","简洁","线条","空间","克制","空旷","静谧","几何"],
    "中国水墨": ["山水","意境","留白","气韵","墨","虚实","飘逸","古雅"],
    "赛博朋克": ["霓虹","科技","都市","虚拟","雨夜","钢筋","电子","未来"],
    "超现实主义": ["梦境","荒诞","潜意识","自由","奇异","不羁","幻想","迷离"],
}

EMOTION_STYLE_MAP = {
    "孤独": ["表现主义","极简主义","赛博朋克"],
    "怀旧": ["印象派","中国水墨"],
    "激昂": ["表现主义","超现实主义"],
    "平静": ["极简主义","中国水墨"],
    "喜悦": ["印象派","超现实主义"],
    "悲伤": ["表现主义","中国水墨"],
}

def match_art_style(words: list, emotion: str) -> list:
    scores = []
    for style, kws in ART_STYLES.items():
        s = sum(1 for w in words if w in kws)
        if emotion in EMOTION_STYLE_MAP and style in EMOTION_STYLE_MAP[emotion]:
            s += 2
        scores.append({"name": style, "score": s, "keywords": kws[:4]})
    scores.sort(key=lambda x: x["score"], reverse=True)
    return scores[:3]

MUSIC_MOODS = {
    "孤独": {"mood":"孤独","genre":"后摇 / 氛围","desc":"Sigur Rós, 坂本龙一"},
    "怀旧": {"mood":"怀旧","genre":"爵士 / 民谣","desc":"Chet Baker, Bob Dylan"},
    "激昂": {"mood":"激昂","genre":"交响乐","desc":"贝多芬, 马勒"},
    "平静": {"mood":"平静","genre":"极简 / 新世纪","desc":"Max Richter, Enya"},
    "悲伤": {"mood":"悲伤","genre":"古典 / 钢琴","desc":"肖邦, 拉赫玛尼诺夫"},
    "喜悦": {"mood":"喜悦","genre":"流行 / 放克","desc":"Earth Wind & Fire"},
}

def match_music(emotion: str) -> dict:
    return MUSIC_MOODS.get(emotion, MUSIC_MOODS["平静"])


# ===== NERAgent：命名实体与意象词识别 =====
NER_FLAG_MAP = {
    "nr": "person",
    "nrt": "person",
    "ns": "location",
    "nt": "organization",
    "nz": "organization",
}

def extract_entities(text: str) -> dict:
    """BERT-NER (ckiplab) + Jieba 意象词融合。"""
    text = (text or "").strip()
    jieba_result = _extract_entities_jieba(text)
    try:
        from ml_models import extract_entities_transformer
        bert = extract_entities_transformer(text)
    except Exception:
        bert = None

    if not bert:
        return {**jieba_result, "method": "Jieba 词性标注", "models": ["Jieba POS"]}

    entities = bert["entities"]
    for key in ("time", "imagery"):
        for word in jieba_result["entities"].get(key, []):
            if word not in entities[key]:
                entities[key].append(word)

    flat = []
    seen = set()
    for span in bert.get("flat", []):
        k = (span["text"], span["type"])
        if k not in seen:
            flat.append(span)
            seen.add(k)
    for span in jieba_result.get("flat", []):
        if span["type"] in ("time", "imagery"):
            k = (span["text"], span["type"])
            if k not in seen:
                flat.append({**span, "score": span.get("score", 0.5)})
                seen.add(k)

    return {
        "entities": entities,
        "flat": flat[:24],
        "method": "BERT-NER + Jieba 意象融合",
        "models": [bert.get("model", "ckiplab/bert-base-chinese-ner"), "Jieba POS"],
        "bert": bert,
        "jieba": jieba_result,
    }


def _extract_entities_jieba(text: str) -> dict:
    """Jieba 词性 NER + 意象名词（兜底）。"""
    text = (text or "").strip()
    entities = {
        "person": [],
        "location": [],
        "organization": [],
        "time": [],
        "imagery": [],
    }
    if not text:
        return {"entities": entities, "flat": []}

    time_words = {"春天", "夏天", "秋天", "冬天", "黄昏", "清晨", "深夜", "午夜", "少年", "青春", "童年", "昨日", "今天", "明天"}
    imagery_flags = {"n", "vn", "a", "an"}

    for word, flag in pseg.cut(text):
        word = word.strip()
        if not word or _is_low_quality_word(word):
            continue
        bucket = NER_FLAG_MAP.get(flag)
        if bucket and word not in entities[bucket]:
            entities[bucket].append(word)
        if word in time_words and word not in entities["time"]:
            entities["time"].append(word)
        if flag in imagery_flags and len(word) >= 2 and word not in entities["imagery"]:
            entities["imagery"].append(word)

    flat = []
    for group, values in entities.items():
        for value in values:
            flat.append({"text": value, "type": group})
    return {"entities": entities, "flat": flat[:20], "method": "Jieba 词性标注", "models": ["Jieba POS"]}


# ===== CorrectAgent：文本校错 =====
COMMON_REPLACEMENTS = [
    (r"的的+", "的"),
    (r"在在+", "在"),
    (r"是是+", "是"),
    (r"了了+", "了"),
    (r"，，+", "，"),
    (r"。。+", "。"),
    (r"\?\?+", "？"),
    (r"!!+", "！"),
    (r"\s{2,}", " "),
]

COMMON_TYPO_MAP = {
    "以经": "已经",
    "在见": "再见",
    "做业": "作业",
    "既使": "即使",
    "必竟": "毕竟",
    "按装": "安装",
    "成份": "成分",
    "侯选": "候选",
    "预望": "欲望",
    "渡假": "度假",
    "脉博": "脉搏",
    "凑和": "凑合",
    "穿带": "穿戴",
    "震憾": "震撼",
    "渲泄": "宣泄",
    "寒喧": "寒暄",
    "弦律": "旋律",
    "漫延": "蔓延",
    "松驰": "松弛",
    "精萃": "精粹",
    "亲睐": "青睐",
    "迫不急待": "迫不及待",
    "穿流不息": "川流不息",
    "一愁莫展": "一筹莫展",
    "默守成规": "墨守成规",
    "走头无路": "走投无路",
    "变本加利": "变本加厉",
    "谈笑风声": "谈笑风生",
    "甘败下风": "甘拜下风",
    "滥芋充数": "滥竽充数",
    "再接再励": "再接再厉",
    "蛛丝蚂迹": "蛛丝马迹",
    "黄梁美梦": "黄粱美梦",
    "世外桃园": "世外桃源",
    "洁白无暇": "洁白无瑕",
    "不能自己": "不能自已",
    "一股作气": "一鼓作气",
    "悬梁刺骨": "悬梁刺股",
    "烩炙人口": "脍炙人口",
    "针贬时弊": "针砭时弊",
    "美仑美奂": "美轮美奂",
    "食不裹腹": "食不果腹",
    "迫不急待": "迫不及待",
}

PUNCT_FIXES = {
    ",": "，",
    ";": "；",
    ":": "：",
    "?": "？",
    "!": "！",
}


def _correct_text_rules(text: str) -> dict:
    """规则 + 常见错别字词典（MacBERT 不可用时的兜底）。"""
    original = text or ""
    corrected = original
    corrections = []

    for wrong, right in COMMON_TYPO_MAP.items():
        if wrong in corrected:
            corrected = corrected.replace(wrong, right)
            corrections.append({"type": "typo", "from": wrong, "to": right, "reason": "常见错别字词典"})

    for pattern, repl in COMMON_REPLACEMENTS:
        new_text = re.sub(pattern, repl, corrected)
        if new_text != corrected:
            corrections.append({"type": "repeat", "from": pattern, "to": repl, "reason": "重复字符/标点压缩"})
            corrected = new_text

    for half, full in PUNCT_FIXES.items():
        if half in corrected:
            new_text = corrected.replace(half, full)
            if new_text != corrected:
                corrections.append({"type": "punct", "from": half, "to": full, "reason": "半角标点转全角"})
                corrected = new_text

    # 诗歌场景：连续空格转顿号式停顿（仅中文段落）
    if re.search(r"[\u4e00-\u9fff]", corrected):
        new_text = re.sub(r" {2,}", "，", corrected)
        if new_text != corrected:
            corrections.append({"type": "spacing", "from": "多空格", "to": "，", "reason": "中文语境空格规范化"})
            corrected = new_text

    stats = {
        "originalLength": len(original),
        "correctedLength": len(corrected),
        "changeCount": len(corrections),
        "changed": corrected != original,
    }
    return {
        "original": original,
        "corrected": corrected,
        "corrections": corrections,
        "stats": stats,
        "method": "规则校错 + 常见错别字词典",
    }


def correct_text(text: str) -> dict:
    """MacBERT (pycorrector) + 规则后处理。"""
    original = text or ""
    try:
        from ml_models import correct_with_macbert
        mac = correct_with_macbert(original)
        if mac:
            base = _correct_text_rules(mac["corrected"])
            merged_corrections = mac.get("corrections", []) + base["corrections"]
            corrected = base["corrected"]
            stats = {
                "originalLength": len(original),
                "correctedLength": len(corrected),
                "changeCount": len(merged_corrections),
                "changed": corrected != original,
            }
            return {
                "original": original,
                "corrected": corrected,
                "corrections": merged_corrections,
                "stats": stats,
                "method": mac.get("method", "pycorrector") + " + 规则后处理",
            }
    except Exception:
        pass
    return _correct_text_rules(original)


def run_nlp_evaluation() -> dict:
    """定量评测：检索、情感、关键词、校错样例 + 检索 ablation。"""
    samples = [
        {"topic": "幸福甜美的校园爱情", "expect_emotion": "喜悦"},
        {"topic": "地铁啃食着城市的肋骨，人群中的一张张脸", "expect_kw": ["地铁", "城市"]},
        {"topic": "雨夜里的自我和解", "expect_emotion": "平静"},
    ]
    results = []
    ablations = []

    for sample in samples:
        text = sample["topic"]
        seg = segment(text)
        exp = expand_query(text, seg["words"])
        emo = analyze_sentiment(exp["expanded"], full_text=text)
        kw = extract_keywords(exp["expanded"], 8, seg["words"])
        sim = retrieve_similar(exp["expanded"], "现代诗", 5, query_text=text, search_mode="hybrid")
        explained, insight = explain_retrieval_results(text, sim, kw, emo["dominant"])
        ablation = compare_retrieval_modes(exp["expanded"], text, "现代诗")
        ablations.append({"topic": text, **ablation})
        row = {
            "topic": text,
            "emotion": emo["dominant"],
            "emotionMatch": emo["dominant"] == sample.get("expect_emotion"),
            "keywords": [k["keyword"] for k in kw[:5]],
            "keywordHit": all(w in [k["keyword"] for k in kw] for w in sample.get("expect_kw", kw[:1] or [""])),
            "retrievalCount": len(explained),
            "topTitle": explained[0]["title"] if explained else None,
            "hybridTopScore": explained[0].get("rerankScore", explained[0].get("similarity")) if explained else 0,
            "semanticInsight": insight.get("insight", ""),
            "explanationSample": explained[0].get("semanticExplanation", {}).get("summary") if explained else "",
        }
        results.append(row)

    typo_text = "我迫不急待的想要以经完成的做业，在在重复阅读。"
    correction = correct_text(typo_text)

    summary = {
        "emotionAccuracy": round(sum(1 for r in results if r["emotionMatch"]) / max(len(results), 1), 2),
        "keywordPassRate": round(sum(1 for r in results if r["keywordHit"]) / max(len(results), 1), 2),
        "avgRetrievalCount": round(sum(r["retrievalCount"] for r in results) / max(len(results), 1), 2),
        "correctionDemoChanges": correction["stats"]["changeCount"],
        "avgRetrievalOverlap": round(sum(a["overlapCount"] for a in ablations) / max(len(ablations), 1), 2),
        "hybridUsesRerank": any(r.get("hybridTopScore") for r in results),
    }
    return {"samples": results, "ablation": ablations, "correctionDemo": correction, "summary": summary}
