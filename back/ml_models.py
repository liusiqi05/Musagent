"""
深度学习模型层 — BGE 向量 / Cross-Encoder 重排 / RoBERTa 情感 / BERT-NER / MacBERT 校错
懒加载 + 失败降级，避免拖垮整个服务。
"""
from __future__ import annotations

import os
import logging

logger = logging.getLogger("musagent.ml")

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-zh-v1.5")
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-base")
SENTIMENT_MODEL = os.getenv("SENTIMENT_MODEL", "uer/roberta-base-finetuned-jd-binary-chinese")
NER_MODEL = os.getenv("NER_MODEL", "ckiplab/bert-base-chinese-ner")
BGE_QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："

_embed_model = None
_reranker = None
_sentiment_pipe = None
_ner_pipe = None
_pycorrector_ok = None


def _get_re_info() -> dict:
    try:
        from re_model import get_re_model_info
        info = get_re_model_info()
        return {
            "model": info.get("baseModel", "hfl/chinese-bert-wwm-ext"),
            "library": "HuggingFace Transformers (BERT-RE)",
            "loaded": info.get("loaded", False),
            "available": info.get("available", False),
        }
    except Exception:
        return {"model": "hfl/chinese-bert-wwm-ext", "library": "BERT-RE", "loaded": False, "available": False}


def get_stack_info() -> dict:
    return {
        "tier": "Transformer-RAG v3",
        "architecture": "BM25 稀疏召回 → BGE 稠密召回 → Cross-Encoder 精排 → RAG → LLM",
        "embedding": {"model": EMBED_MODEL, "library": "FlagEmbedding (BGE)", "loaded": _embed_model is not None},
        "reranker": {"model": RERANK_MODEL, "library": "FlagEmbedding Cross-Encoder", "loaded": _reranker is not None},
        "sentiment": {"model": SENTIMENT_MODEL, "library": "HuggingFace Transformers (RoBERTa)", "loaded": _sentiment_pipe is not None},
        "ner": {"model": NER_MODEL, "library": "HuggingFace Transformers (BERT-NER)", "loaded": _ner_pipe is not None},
        "relationExtraction": _get_re_info(),
        "correction": {
            "library": "pycorrector (MacBERT)" if _check_pycorrector() else "rule-fallback",
            "loaded": _check_pycorrector(),
        },
        "llm": {"model": "deepseek-chat", "library": "OpenAI SDK compatible"},
        "classicNlp": ["Jieba 分词", "TF-IDF", "TextRank", "BM25", "文学情感词典"],
    }


def _check_pycorrector() -> bool:
    global _pycorrector_ok
    if _pycorrector_ok is not None:
        return _pycorrector_ok
    try:
        import pycorrector  # noqa: F401
        _pycorrector_ok = True
    except Exception:
        _pycorrector_ok = False
    return _pycorrector_ok


def get_embed_model():
    global _embed_model
    if _embed_model is not None:
        return _embed_model
    try:
        from FlagEmbedding import FlagModel
        _embed_model = FlagModel(EMBED_MODEL, query_instruction_for_retrieval=BGE_QUERY_INSTRUCTION)
        logger.info("Loaded embedding model: %s", EMBED_MODEL)
        return _embed_model
    except Exception as exc:
        logger.warning("BGE embed model unavailable: %s", exc)
        try:
            from sentence_transformers import SentenceTransformer
            _embed_model = SentenceTransformer(EMBED_MODEL)
            logger.info("Fallback SentenceTransformer: %s", EMBED_MODEL)
            return _embed_model
        except Exception as exc2:
            logger.warning("SentenceTransformer fallback failed: %s", exc2)
            return None


def encode_queries(texts: list[str]):
    model = get_embed_model()
    if model is None or not texts:
        return None
    if hasattr(model, "encode_queries"):
        return model.encode_queries(texts)
    return model.encode(texts, normalize_embeddings=True)


def encode_corpus(texts: list[str], batch_size: int = 64):
    model = get_embed_model()
    if model is None or not texts:
        return None
    if hasattr(model, "encode_corpus"):
        vectors = []
        for i in range(0, len(texts), batch_size):
            vectors.append(model.encode_corpus(texts[i : i + batch_size]))
        import numpy as np
        return np.vstack(vectors).astype(np.float32)
    import numpy as np
    return np.array(model.encode(texts, normalize_embeddings=True, show_progress_bar=False)).astype(np.float32)


def get_reranker():
    global _reranker
    if _reranker is not None:
        return _reranker
    try:
        from FlagEmbedding import FlagReranker
        _reranker = FlagReranker(RERANK_MODEL, use_fp16=False)
        logger.info("Loaded reranker: %s", RERANK_MODEL)
        return _reranker
    except Exception as exc:
        logger.warning("Reranker unavailable: %s", exc)
        return None


def rerank_candidates(query: str, candidates: list[dict], top_n: int = 5) -> list[dict]:
    """Cross-Encoder 精排；candidates 需含 title/content。"""
    if not candidates or not query.strip():
        return candidates[:top_n]
    reranker = get_reranker()
    if reranker is None:
        return candidates[:top_n]

    pairs = [
        [query, f"{c.get('title', '')} {c.get('author', '')} {(c.get('content') or '')[:240]}"]
        for c in candidates
    ]
    try:
        scores = reranker.compute_score(pairs)
        if not isinstance(scores, list):
            scores = [scores]
        for cand, score in zip(candidates, scores):
            cand["rerankScore"] = round(float(score), 4)
            cand["similarity"] = cand["rerankScore"]
            cand["retrievalMethod"] = "bm25+bge+rerank"
        candidates.sort(key=lambda x: x.get("rerankScore", 0), reverse=True)
        return candidates[:top_n]
    except Exception as exc:
        logger.warning("Rerank failed: %s", exc)
        return candidates[:top_n]


def analyze_sentiment_transformer(text: str) -> dict | None:
    global _sentiment_pipe
    text = (text or "").strip()
    if not text:
        return None
    try:
        if _sentiment_pipe is None:
            from transformers import pipeline
            _sentiment_pipe = pipeline(
                "sentiment-analysis",
                model=SENTIMENT_MODEL,
                tokenizer=SENTIMENT_MODEL,
                truncation=True,
                max_length=512,
            )
        raw = _sentiment_pipe(text[:512])[0]
        label = str(raw.get("label", "")).upper()
        conf = float(raw.get("score", 0.5))
        polarity = conf if "POS" in label or label.endswith("1") else 1 - conf

        scores = {
            "喜悦": max(polarity - 0.4, 0) * 2.0,
            "悲伤": max(0.6 - polarity, 0) * 2.0,
            "平静": 0.4 + (1 - abs(polarity - 0.5) * 2) * 0.35,
            "孤独": 0.2 if any(w in text for w in ["孤独", "独自", "一个人", "深夜"]) else 0.05,
            "怀旧": 0.2 if any(w in text for w in ["回忆", "曾经", "从前", "旧", "青春"]) else 0.05,
            "激昂": 0.2 if any(w in text for w in ["梦想", "燃烧", "呐喊", "激昂"]) else 0.05,
        }
        mx = max(scores.values()) or 1
        normalized = {k: round(v / mx, 2) for k, v in scores.items()}
        dominant = max(normalized, key=normalized.get)
        return {
            "model": SENTIMENT_MODEL,
            "label": label,
            "confidence": round(conf, 3),
            "polarity": round(polarity, 3),
            "scores": normalized,
            "dominant": dominant,
            "intensity": round(min(abs(polarity - 0.5) * 2 + conf * 0.2, 1), 2),
        }
    except Exception as exc:
        logger.warning("Transformer sentiment failed: %s", exc)
        return None


NER_LABEL_MAP = {
    "PER": "person",
    "PERSON": "person",
    "LOC": "location",
    "GPE": "location",
    "ORG": "organization",
    "ORGANIZATION": "organization",
}


def extract_entities_transformer(text: str) -> dict | None:
    global _ner_pipe
    text = (text or "").strip()
    if not text:
        return None
    try:
        if _ner_pipe is None:
            from transformers import pipeline
            _ner_pipe = pipeline(
                "ner",
                model=NER_MODEL,
                tokenizer=NER_MODEL,
                aggregation_strategy="simple",
            )
        spans = _ner_pipe(text[:256])
        entities = {"person": [], "location": [], "organization": [], "time": [], "imagery": []}
        flat = []
        for span in spans:
            word = span.get("word", "").replace("##", "").strip()
            if not word or len(word) < 2:
                continue
            etype = NER_LABEL_MAP.get(span.get("entity_group", "").upper(), "imagery")
            if etype not in entities:
                etype = "imagery"
            if word not in entities[etype]:
                entities[etype].append(word)
                flat.append({"text": word, "type": etype, "score": round(float(span.get("score", 0)), 3)})
        return {"model": NER_MODEL, "entities": entities, "flat": flat[:20]}
    except Exception as exc:
        logger.warning("Transformer NER failed: %s", exc)
        return None


def correct_with_macbert(text: str) -> dict | None:
    if not _check_pycorrector() or not text.strip():
        return None
    try:
        import pycorrector
        corrected_sentences = []
        corrections = []
        for sent in _split_sentences(text):
            new_sent, details = pycorrector.correct(sent)
            corrected_sentences.append(new_sent)
            for item in details or []:
                if len(item) >= 3:
                    corrections.append({
                        "type": "macbert",
                        "from": item[0],
                        "to": item[1],
                        "reason": f"MacBERT 置信度 {item[2]:.2f}" if isinstance(item[2], float) else "MacBERT 校错",
                    })
        corrected = "".join(corrected_sentences)
        return {
            "corrected": corrected,
            "corrections": corrections,
            "method": "pycorrector (MacBERT)",
        }
    except Exception as exc:
        logger.warning("pycorrector failed: %s", exc)
        return None


def _split_sentences(text: str) -> list[str]:
    import re
    parts = re.split(r"([。！？\n])", text)
    if len(parts) <= 1:
        return [text]
    merged = []
    for i in range(0, len(parts) - 1, 2):
        merged.append(parts[i] + (parts[i + 1] if i + 1 < len(parts) else ""))
    if len(parts) % 2 == 1 and parts[-1]:
        merged.append(parts[-1])
    return merged or [text]
