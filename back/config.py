"""
MusAgent 统一配置 — 从环境变量读取可调参数。
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = os.getenv("MUSAGENT_DB_PATH", str(DATA_DIR / "musagent.db"))

# LLM
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-your-key-here")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.8"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "500"))
LLM_POLISH_TEMPERATURE = float(os.getenv("LLM_POLISH_TEMPERATURE", "0.65"))

# 篇幅 → LLM max_tokens（长文本生成）
LENGTH_TOKEN_MAP = {
    "短": 500,
    "中": 900,
    "长": 1800,
    "超长": 4096,
}

LENGTH_CHAR_HINT = {
    "短": "80–150 字",
    "中": "150–400 字",
    "长": "400–900 字",
    "超长": "900–2500 字，可分 2–4 节",
}

# 检索融合
HYBRID_BM25_WEIGHT = float(os.getenv("HYBRID_BM25_WEIGHT", "0.55"))
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "20"))
RETRIEVAL_MIN_SCORE = float(os.getenv("RETRIEVAL_MIN_SCORE", "0.15"))
QUALITY_MIN_SCORE = float(os.getenv("QUALITY_MIN_SCORE", "0.45"))

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "auto").lower()
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))

# 垂直领域
VERTICAL_DOMAIN = os.getenv("VERTICAL_DOMAIN", "literature_poetry")

# 模型
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-zh-v1.5")
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-base")
SENTIMENT_MODEL = os.getenv("SENTIMENT_MODEL", "uer/roberta-base-finetuned-jd-binary-chinese")
NER_MODEL = os.getenv("NER_MODEL", "ckiplab/bert-base-chinese-ner")
RE_BASE_MODEL = os.getenv("RE_BASE_MODEL", "hfl/chinese-bert-wwm-ext")


def get_runtime_config() -> dict:
    return {
        "vertical": VERTICAL_DOMAIN,
        "llm": {
            "model": LLM_MODEL,
            "temperature": LLM_TEMPERATURE,
            "maxTokens": LLM_MAX_TOKENS,
            "configured": bool(DEEPSEEK_API_KEY) and DEEPSEEK_API_KEY != "sk-your-key-here",
        },
        "retrieval": {
            "hybridBm25Weight": HYBRID_BM25_WEIGHT,
            "rerankTopK": RERANK_TOP_K,
            "minScore": RETRIEVAL_MIN_SCORE,
        },
        "quality": {"minScore": QUALITY_MIN_SCORE},
        "cache": {
            "redisUrl": REDIS_URL.split("@")[-1] if "@" in REDIS_URL else REDIS_URL,
            "ttlSeconds": CACHE_TTL_SECONDS,
        },
        "models": {
            "embed": EMBED_MODEL,
            "rerank": RERANK_MODEL,
            "sentiment": SENTIMENT_MODEL,
            "ner": NER_MODEL,
            "re": RE_BASE_MODEL,
        },
    }
