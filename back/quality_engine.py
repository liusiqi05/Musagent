"""
质量评估与筛选 — 对生成结果、检索结果、关键词做多维打分。
v3.0 新增：Critic Agent（基于 LLM 的 self-critique + 规则化兜底）。
"""
from __future__ import annotations

import json
import re
from typing import Any

from config import QUALITY_MIN_SCORE, RETRIEVAL_MIN_SCORE, DEEPSEEK_API_KEY, LLM_MODEL, LLM_TEMPERATURE
from openai import OpenAI

# 复用一个轻量客户端给 Critic 用（与 main.py 共享环境变量）
_critic_client = None
def _get_critic_client():
    global _critic_client
    if _critic_client is not None:
        return _critic_client
    from config import DEEPSEEK_BASE_URL
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "***":
        return None
    _critic_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    return _critic_client

GENERIC_WORDS = {
    "东西", "事情", "感觉", "时候", "地方", "世界", "人生", "生活", "一切", "某种",
    "某种情绪", "未知", "某种感觉",
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def score_keywords(keywords: list[dict]) -> dict:
    if not keywords:
        return {"score": 0.0, "label": "无关键词", "issues": ["未提取到有效关键词"]}
    issues = []
    good = 0
    for item in keywords[:10]:
        word = item.get("keyword", "")
        if len(word) < 2:
            issues.append(f"过短词：{word}")
            continue
        if word in GENERIC_WORDS:
            issues.append(f"泛化词：{word}")
            continue
        good += 1
    score = _clamp(good / max(len(keywords[:10]), 1))
    label = "优秀" if score >= 0.75 else "良好" if score >= 0.5 else "待优化"
    return {"score": round(score, 3), "label": label, "issues": issues[:5]}


def score_retrieval(results: list[dict], min_score: float | None = None) -> dict:
    min_score = RETRIEVAL_MIN_SCORE if min_score is None else min_score
    if not results:
        return {"score": 0.0, "label": "无检索", "filtered": [], "issues": ["检索结果为空"]}

    filtered = []
    scores = []
    for item in results:
        raw = item.get("rerankScore", item.get("similarity", item.get("bm25Score", 0)))
        try:
            val = float(raw or 0)
        except (TypeError, ValueError):
            val = 0.0
        if val >= min_score:
            filtered.append(item)
            scores.append(val)

    avg = sum(scores) / len(scores) if scores else 0.0
    coverage = len(filtered) / max(len(results), 1)
    score = _clamp(avg * 0.7 + coverage * 0.3)
    label = "高相关" if score >= 0.7 else "中等相关" if score >= 0.45 else "弱相关"
    issues = []
    if len(filtered) < 2:
        issues.append("高质量命中不足，建议扩展主题词")
    return {
        "score": round(score, 3),
        "label": label,
        "filtered": filtered,
        "issues": issues,
        "minScore": min_score,
    }


def score_generation(
    content: str,
    keywords: list[dict],
    emotion: str,
    citations: list | None = None,
) -> dict:
    text = (content or "").strip()
    issues = []
    if not text:
        return {"score": 0.0, "label": "空输出", "issues": ["生成内容为空"], "passed": False}

    kw_strings = [k.get("keyword", "") for k in keywords[:8] if k.get("keyword")]
    hit_kw = sum(1 for w in kw_strings if w and w in text)
    kw_ratio = hit_kw / max(len(kw_strings), 1)

    lines = [ln.strip() for ln in re.split(r"[\n]+", text) if ln.strip()]
    line_score = _clamp(len(lines) / 6)

    unique_chars = len(set(re.sub(r"\s+", "", text)))
    diversity = _clamp(unique_chars / max(len(text), 1) * 2)

    cite_bonus = 0.08 if citations else 0.0
    emotion_bonus = 0.05 if emotion and emotion in text else 0.0

    repetition_penalty = 0.0
    if len(text) > 20:
        chunks = [text[i : i + 4] for i in range(0, len(text) - 3, 2)]
        if chunks:
            dup = 1 - len(set(chunks)) / len(chunks)
            if dup > 0.35:
                repetition_penalty = 0.15
                issues.append("重复片段偏多")

    if kw_ratio < 0.2 and kw_strings:
        issues.append("核心关键词覆盖不足")
    if len(text) < 24:
        issues.append("篇幅偏短")

    score = _clamp(kw_ratio * 0.35 + line_score * 0.25 + diversity * 0.2 + cite_bonus + emotion_bonus - repetition_penalty)
    label = "优秀" if score >= 0.75 else "可用" if score >= QUALITY_MIN_SCORE else "待优化"
    return {
        "score": round(score, 3),
        "label": label,
        "passed": score >= QUALITY_MIN_SCORE,
        "issues": issues,
        "metrics": {
            "keywordCoverage": round(kw_ratio, 3),
            "lineCount": len(lines),
            "diversity": round(diversity, 3),
        },
    }


def assess_pipeline_output(
    generated: dict,
    generated_llm: dict | None,
    keywords: list[dict],
    similar_works: list[dict],
    emotion: dict | None = None,
) -> dict:
    emotion_name = (emotion or {}).get("dominant", "")
    kw_eval = score_keywords(keywords)
    retrieval_eval = score_retrieval(similar_works)

    template_eval = score_generation(
        generated.get("content", ""),
        keywords,
        emotion_name,
        generated.get("citations"),
    )
    llm_eval = None
    if generated_llm and generated_llm.get("content"):
        llm_eval = score_generation(
            generated_llm.get("content", ""),
            keywords,
            emotion_name,
            generated_llm.get("citations"),
        )

    primary = llm_eval or template_eval
    overall = round((primary["score"] * 0.5 + kw_eval["score"] * 0.2 + retrieval_eval["score"] * 0.3), 3)
    return {
        "overall": {
            "score": overall,
            "label": "优秀" if overall >= 0.75 else "合格" if overall >= QUALITY_MIN_SCORE else "待优化",
            "passed": overall >= QUALITY_MIN_SCORE,
            "minScore": QUALITY_MIN_SCORE,
        },
        "keywords": kw_eval,
        "retrieval": retrieval_eval,
        "generation": {
            "template": template_eval,
            "llm": llm_eval,
            "recommended": "llm" if llm_eval and (not template_eval or llm_eval["score"] >= template_eval["score"]) else "template",
        },
        "filteredSimilarWorks": retrieval_eval["filtered"] or similar_works[:3],
    }


def filter_low_quality_items(items: list[dict], score_key: str = "rerankScore", min_score: float | None = None) -> list[dict]:
    min_score = RETRIEVAL_MIN_SCORE if min_score is None else min_score
    kept = []
    for item in items:
        try:
            val = float(item.get(score_key, item.get("similarity", 0)) or 0)
        except (TypeError, ValueError):
            val = 0.0
        if val >= min_score:
            kept.append(item)
    return kept or items[:1]


# ============================================================
# Critic Agent — v3.0 新增
# 对 LLM 生成结果做 self-critique：评分 + 改进建议 + 必要时触发重写
# 复用 score_generation 规则化打分作为 LLM 不可用时的兜底
# ============================================================
CRITIC_THRESHOLD = 7.0  # < 7 分触发重写（最多 1 次）
CRITIC_MAX_RETRIES = 1  # 防止无限循环


def _build_critic_prompt(topic: str, content: str, keywords: list, emotion: str,
                          rag_titles: list[str], art_style: str) -> str:
    kw_str = "、".join([k.get("keyword", "") for k in keywords[:6] if k.get("keyword")])
    rag_str = "、".join(rag_titles[:3]) if rag_titles else "（无）"
    return f"""你是一位严格的文学评论家（Critic Agent），对以下生成结果打分（0-10 整数）并给出最多 3 条具体改进建议。

【主题】{topic}
【目标情感】{emotion}
【核心关键词】{kw_str}
【目标风格】{art_style}
【RAG 参考作品】{rag_str}

【待评生成内容】
{content[:800]}

【评分维度】（总分 0-10）
- 主题契合（0-3）：是否紧扣主题，关键词是否被有机融入
- 情感表达（0-3）：情绪氛围是否到位，与目标 emotion 是否一致
- 文学质量（0-2）：语言凝练度、意象密度、是否有重复/空洞
- RAG 化用（0-2）：是否借鉴了参考作品的核心意象/句式

【严格输出 JSON】（不要任何解释或 Markdown 标记）：
{{"score": <int 0-10>, "issues": ["问题1", "问题2", "问题3"], "suggestions": ["建议1", "建议2"]}}
"""


def _parse_critic_response(raw: str) -> dict:
    """解析 Critic LLM 输出。容忍 JSON 前后多余字符与 markdown 围栏。"""
    if not raw:
        return {"score": 0, "issues": ["Critic 返回为空"], "suggestions": [], "raw": ""}
    text = raw.strip()
    # 去掉 markdown ```json ... ``` 围栏
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # 尝试抓取第一个 { ... } 块
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {"score": 5, "issues": ["Critic 输出无法解析"], "suggestions": [], "raw": raw[:200]}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"score": 5, "issues": ["Critic JSON 解析失败"], "suggestions": [], "raw": raw[:200]}
    score = data.get("score", 0)
    try:
        score = max(0, min(10, int(round(float(score)))))
    except (TypeError, ValueError):
        score = 5
    return {
        "score": score,
        "issues": list(data.get("issues", []))[:3],
        "suggestions": list(data.get("suggestions", []))[:3],
        "raw": raw[:200],
    }


def _rule_based_critic(content: str, keywords: list, emotion: str) -> dict:
    """LLM 不可用时的兜底：基于规则的多维打分。"""
    if not content or not content.strip():
        return {"score": 0, "issues": ["生成内容为空"], "suggestions": ["检查后端 LLM 状态"], "method": "rule"}
    text = content.strip()
    issues = []
    suggestions = []

    # 关键词覆盖率
    kw_strings = [k.get("keyword", "") for k in keywords[:8] if k.get("keyword")]
    hit = sum(1 for w in kw_strings if w in text)
    coverage = hit / max(len(kw_strings), 1)

    # 行数
    lines = [ln for ln in re.split(r"[\n]+", text) if ln.strip()]
    if len(lines) < 3:
        issues.append("行数偏少")
        suggestions.append("增加 2-3 行以丰富画面")
    if len(text) < 30:
        issues.append("篇幅过短")
        suggestions.append("扩写到 100 字以上")
    if coverage < 0.3:
        issues.append("关键词未充分体现")
        suggestions.append(f"至少自然融入 1-2 个关键词：{', '.join(kw_strings[:3])}")
    if emotion and emotion not in text and any(e in text for e in ["悲", "喜", "静", "远", "暖"]):
        issues.append(f"目标情绪 {emotion} 不够鲜明")
        suggestions.append(f"强化 {emotion} 情绪词或意象")

    # 重复
    if len(text) > 20:
        chunks = [text[i:i + 4] for i in range(0, len(text) - 3, 2)]
        dup = 1 - len(set(chunks)) / len(chunks) if chunks else 0
        if dup > 0.4:
            issues.append("片段重复较多")
            suggestions.append("换掉重复 2-gram，引入新意象")

    # 简版综合分
    base = 5
    base += min(2, int(coverage * 4))  # 关键词加成
    base += 1 if 4 <= len(lines) <= 12 else 0
    base += 1 if 50 <= len(text) <= 600 else 0
    base -= 1 if issues else 0
    base -= 1 if any("重复" in i or "过短" in i or "空" in i for i in issues) else 0
    score = max(0, min(10, base))

    return {
        "score": score,
        "issues": issues[:3],
        "suggestions": suggestions[:3],
        "method": "rule",
    }


def critic_review(
    content: str,
    keywords: list,
    emotion: str,
    rag_titles: list[str] | None = None,
    art_style: str = "",
    topic: str = "",
) -> dict:
    """
    Critic Agent 主入口。
    优先用 LLM 打分；API 不可用 / 异常时回退到规则打分。
    返回: {score, issues, suggestions, method, model, retryRecommended}
    """
    rag_titles = rag_titles or []
    client = _get_critic_client()
    if client is None:
        result = _rule_based_critic(content, keywords, emotion)
        result["model"] = "rule-based"
        result["retryRecommended"] = result["score"] < CRITIC_THRESHOLD
        return result

    prompt = _build_critic_prompt(topic, content, keywords, emotion, rag_titles, art_style)
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是严格的文学评论家，只输出 JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=300,
        )
        raw = resp.choices[0].message.content or ""
        parsed = _parse_critic_response(raw)
        return {
            **parsed,
            "model": LLM_MODEL,
            "method": "llm",
            "retryRecommended": parsed["score"] < CRITIC_THRESHOLD,
        }
    except Exception as exc:
        # LLM 失败：兜底
        result = _rule_based_critic(content, keywords, emotion)
        result["model"] = "rule-fallback"
        result["llmError"] = str(exc)[:120]
        result["retryRecommended"] = result["score"] < CRITIC_THRESHOLD
        return result
