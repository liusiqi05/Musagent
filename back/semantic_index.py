"""
语义索引 — BAAI/bge-small-zh-v1.5 (FlagEmbedding) + NumPy 向量检索
"""
from __future__ import annotations

import os
import json
import numpy as np

from ml_models import EMBED_MODEL, encode_corpus, encode_queries

_CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
_CACHE_TAG = EMBED_MODEL.replace("/", "_").replace("-", "_")
_EMB_FILE = os.path.join(_CACHE_DIR, f"embeddings_{_CACHE_TAG}.npy")
_META_FILE = os.path.join(_CACHE_DIR, f"poem_index_meta_{_CACHE_TAG}.json")

_embeddings: np.ndarray | None = None
_meta: list[dict] | None = None
_backend: str = "none"


def _doc_snippet(doc: dict) -> str:
    return f"{doc.get('title', '')} {doc.get('author', '')} {(doc.get('content') or '')[:320]}"


def warm_semantic_index(kb_docs: list[dict]) -> dict:
    global _embeddings, _meta, _backend

    os.makedirs(_CACHE_DIR, exist_ok=True)
    _meta = [
        {
            "index": i,
            "type": doc["type"],
            "title": doc["title"],
            "author": doc["author"],
            "content": doc["content"],
        }
        for i, doc in enumerate(kb_docs)
    ]
    texts = [_doc_snippet(doc) for doc in kb_docs]

    if os.path.exists(_EMB_FILE) and os.path.exists(_META_FILE):
        try:
            with open(_META_FILE, "r", encoding="utf-8") as f:
                cached_meta = json.load(f)
            if len(cached_meta) == len(kb_docs):
                _embeddings = np.load(_EMB_FILE)
                _backend = f"bge:{EMBED_MODEL}"
                return {"backend": _backend, "count": len(kb_docs), "cached": True}
        except Exception:
            pass

    vectors = encode_corpus(texts)
    if vectors is None:
        _backend = "unavailable"
        return {"backend": _backend, "count": len(kb_docs), "cached": False}

    _embeddings = vectors
    np.save(_EMB_FILE, _embeddings)
    with open(_META_FILE, "w", encoding="utf-8") as f:
        json.dump(_meta, f, ensure_ascii=False)
    _backend = f"bge:{EMBED_MODEL}"
    return {"backend": _backend, "count": len(kb_docs), "cached": False}


def _ensure_ready():
    """确保语义索引就绪。如果依赖（KB docs / BGE 模型）缺失，
    设置空占位以让 /api/health 等只读端点能正常返回。
    """
    global _meta, _embeddings, _backend
    if _meta is not None and _embeddings is not None:
        return
    try:
        from nlp_engine import _ensure_kb, _kb_docs
        _ensure_kb()
        if _kb_docs is None or len(_kb_docs) == 0:
            # 知识库为空时占位，避免 health 端点 500
            _meta = []
            _embeddings = np.zeros((0, 1), dtype=np.float32)
            _backend = "unavailable:empty_kb"
            return
        warm_semantic_index(_kb_docs)
    except Exception as exc:
        # 模型加载失败 / 网络不通时降级为占位
        _meta = []
        _embeddings = np.zeros((0, 1), dtype=np.float32)
        _backend = f"unavailable:{type(exc).__name__}"


def semantic_search(query: str, top_n: int = 10, poem_type: str = "all") -> list[dict]:
    _ensure_ready()
    if not query.strip() or _embeddings is None:
        return []

    q_vec = encode_queries([query])
    if q_vec is None:
        return []
    if len(q_vec.shape) == 1:
        q_vec = q_vec.reshape(1, -1)
    scores = (_embeddings @ q_vec[0]).astype(float)

    ranked = np.argsort(-scores)
    results = []
    for idx in ranked:
        doc = _meta[idx]
        if poem_type == "古典诗" and doc["type"] != "古典诗":
            continue
        if poem_type in ("现代诗", "散文", "短篇片段") and doc["type"] != "现代诗":
            continue
        score = float(scores[idx])
        if score <= 0.05:
            continue
        results.append({
            "type": doc["type"],
            "title": doc["title"],
            "author": doc["author"],
            "content": doc["content"][:200],
            "semanticScore": round(score, 4),
            "index": int(idx),
        })
        if len(results) >= top_n:
            break
    return results


def get_index_info() -> dict:
    _ensure_ready()
    return {
        "backend": _backend,
        "model": EMBED_MODEL,
        "documentCount": len(_meta or []),
    }
