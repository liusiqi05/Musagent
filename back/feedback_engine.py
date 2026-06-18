"""
用户反馈洞察 — 从评分数据提取偏好，回流到生成与检索。
"""
from __future__ import annotations

import json
from collections import Counter

from database import db_cursor, ensure_db


def get_feedback_insights() -> dict:
    """汇总用户反馈，供 Pipeline 与前端展示。"""
    ensure_db()
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT topic, rating, comment, source_type
            FROM feedback WHERE rating >= 4 AND topic != ''
            ORDER BY id DESC LIMIT 50
            """
        )
        good_rows = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT ROUND(AVG(rating), 2) AS avg, COUNT(*) AS c FROM feedback")
        overall = dict(cur.fetchone())
        cur.execute(
            """
            SELECT source_type, ROUND(AVG(rating), 2) AS avg, COUNT(*) AS c
            FROM feedback GROUP BY source_type
            """
        )
        by_source = [dict(r) for r in cur.fetchall()]

    topic_counter = Counter(r["topic"] for r in good_rows if r.get("topic"))
    preferred_topics = [t for t, _ in topic_counter.most_common(8)]

    tag_counter = Counter()
    for row in good_rows:
        comment = row.get("comment") or ""
        for tag in ("意象", "情感", "节奏", "化用", "检索"):
            if tag in comment:
                tag_counter[tag] += 1

    return {
        "overallAvg": overall.get("avg") or 0,
        "totalFeedback": overall.get("c") or 0,
        "preferredTopics": preferred_topics,
        "positiveTags": [t for t, _ in tag_counter.most_common(5)],
        "bySource": by_source,
        "generationHint": _build_generation_hint(preferred_topics, tag_counter),
    }


def _build_generation_hint(topics: list[str], tags: Counter) -> str:
    parts = []
    if topics:
        parts.append(f"用户近期好评主题：{'、'.join(topics[:4])}")
    if tags:
        parts.append(f"用户关注：{'、'.join(t for t, _ in tags.most_common(3))}")
    return "；".join(parts) if parts else ""


def apply_feedback_to_keywords(keywords: list[dict], insights: dict) -> list[dict]:
    """对高评分主题相关的关键词做轻量加权。"""
    preferred = set(insights.get("preferredTopics") or [])
    if not preferred:
        return keywords
    boosted = []
    for kw in keywords:
        word = kw.get("keyword", "")
        boost = 1.0
        for topic in preferred:
            if word in topic or topic in word:
                boost = 1.15
                break
        boosted.append({**kw, "tfidf": round((kw.get("tfidf") or 0) * boost, 4)})
    boosted.sort(key=lambda x: x.get("tfidf", 0), reverse=True)
    return boosted
