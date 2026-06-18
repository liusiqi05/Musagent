#!/usr/bin/env python3
"""写入演示用用户数据 — 反馈、问答、知识图谱、生成日志。"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from database import (
    db_cursor, ensure_db, import_poems_from_json, get_db_stats,
    save_feedback, save_qa_feedback, upsert_entity, save_relation, log_generation,
)
from config import VERTICAL_DOMAIN
import nlp_engine
from kg_engine import build_knowledge_graph_from_poems


def _days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days, hours=days % 5)).isoformat()


def seed_feedback() -> int:
    rows = [
        ("generation", 5, "意象很准，化用标注也有帮助", "雨夜里的自我和解", "把孤独叠成纸船\n放进月光铺就的河", "gen-001"),
        ("generation", 4, "LLM 版本比模板更有诗性", "校园爱情", "青春在课桌间缓慢显影", "gen-002"),
        ("generation", 5, "检索到的参考诗很贴切", "城市孤独", "霓虹沉入深色的海", "gen-003"),
        ("generation", 3, "关键词还行，生成略短", "黄昏散步", "风在窗外徘徊", "gen-004"),
        ("generation", 4, "质量评估分数和感受一致", "地铁与人群", "人群中的一张张脸", "gen-005"),
        ("chat", 5, "灵感菌共情到位", "最近有点焦虑", "我感受到了你内心的平静…", "chat-001"),
        ("chat", 4, "对话后回填主题很方便", "想写一首关于月亮的诗", "月亮是夜晚未拆封的信", "chat-002"),
        ("chat", 3, "回复偏短但有用", "不知道怎么开头", "也许可以试试把这些感受写下来", "chat-003"),
        ("polish", 5, "保守润色保留了原意", "地铁啃食着城市的肋骨", "地铁缓缓啃食着城市的肋骨", "pol-001"),
        ("polish", 4, "风格化版本文学感更强", "关于时光的片段", "关于时光的片段（润色版）", "pol-002"),
        ("retrieval", 4, "语义检索比关键词好", "幸福甜美的校园爱情", "", "ret-001"),
        ("retrieval", 5, "混合检索 Top3 都很相关", "雨夜 窗 孤独", "", "ret-002"),
    ]
    count = 0
    for i, (src, rating, comment, topic, preview, sid) in enumerate(rows):
        save_feedback(src, rating, comment, topic, preview, sid, {"seed": True, "batch": "demo"})
        count += 1
    return count


def seed_qa_feedback() -> int:
    pairs = [
        ("最近心情很低落，能帮我找点创作灵感吗？", "低落也是创作的土壤。试试从「雨夜」「窗」「安静」这些意象入手写一段短诗。", 5, True, ["chat", "emotion"]),
        ("校园爱情这个主题怎么扩展？", "可以联想：教室、操场、初恋、晚风、毕业。系统会自动做 Query Expansion。", 4, True, ["chat", "topic"]),
        ("生成的诗太短了怎么办？", "在高级选项里把篇幅改为「长」，或点击「沿用分析再生成」多试几次。", 4, True, ["chat", "howto"]),
        ("知识图谱有什么用？", "它会展示主题、实体、参考作品之间的关系，帮助理解系统如何「借鉴」检索结果。", 5, True, ["chat", "kg"]),
        ("润色和重新生成有什么区别？", "润色保留原文结构做文学化改写；重新生成会沿用分析结果只换 WriterAgent 输出。", 3, False, ["chat", "howto"]),
    ]
    for q, a, rating, helpful, tags in pairs:
        save_qa_feedback(q, a, rating, helpful, tags)
    return len(pairs)


def seed_generation_logs() -> int:
    logs = [
        ("雨夜里的自我和解", "现代诗", 0.78, "合格", "DeepSeek LLM 生成", True),
        ("校园爱情", "现代诗", 0.85, "优秀", "DeepSeek LLM 生成", True),
        ("城市孤独", "散文", 0.72, "合格", "算法模板生成", True),
        ("地铁与人群", "现代诗", 0.58, "待优化", "DeepSeek LLM 生成", False),
        ("黄昏散步", "古典诗", 0.81, "优秀", "DeepSeek LLM 生成", True),
        ("幸福甜美的校园爱情", "现代诗", 0.88, "优秀", "DeepSeek LLM 生成", True),
        ("霓虹下的告别", "短篇片段", 0.65, "合格", "算法模板生成", True),
        ("关于月亮", "现代诗", 0.74, "合格", "DeepSeek LLM 生成", True),
    ]
    for topic, ctype, score, label, method, passed in logs:
        log_generation(topic, ctype, score, label, method, passed, {"seed": True})
    return len(logs)


def seed_knowledge_graph() -> dict:
    """补充文学领域实体与关系。"""
    entities = [
        ("李白", "person"), ("杜甫", "person"), ("余光中", "person"), ("海子", "person"),
        ("月亮", "imagery"), ("雨夜", "imagery"), ("校园", "imagery"), ("霓虹", "imagery"),
        ("孤独", "imagery"), ("青春", "imagery"), ("《静夜思》", "work"), ("《面朝大海》", "work"),
        ("现代诗", "organization"), ("古典诗", "organization"),
    ]
    for name, etype in entities:
        upsert_entity(name, etype, source="seed")

    relations = [
        ("《静夜思》", "authored_by", "李白", 0.98),
        ("《静夜思》", "contains_imagery", "月亮", 0.92),
        ("《静夜思》", "has_emotion", "怀旧", 0.88),
        ("《静夜思》", "belongs_to_type", "古典诗", 0.95),
        ("《面朝大海》", "authored_by", "海子", 0.97),
        ("《面朝大海》", "has_emotion", "激昂", 0.85),
        ("雨夜", "co_occurs_with", "孤独", 0.72),
        ("校园", "co_occurs_with", "青春", 0.80),
        ("霓虹", "co_occurs_with", "城市", 0.75),
        ("城市孤独", "inspired_by", "《静夜思》", 0.68),
        ("校园爱情", "contains_imagery", "青春", 0.82),
        ("校园爱情", "contains_imagery", "校园", 0.85),
        ("余光中", "related_to", "乡愁", 0.70),
        ("月亮", "metaphor_of", "思念", 0.65),
    ]
    for head, rel, tail, conf in relations:
        save_relation(head, rel, tail, conf, source="seed")

    poems = nlp_engine.get_poem_list()
    kg = build_knowledge_graph_from_poems(poems, max_poems=200)
    return {"seedRelations": len(relations), "batchKg": kg.get("processedPoems", 0)}


def main():
    ensure_db()
    imported = import_poems_from_json()
    fb = seed_feedback()
    qa = seed_qa_feedback()
    logs = seed_generation_logs()
    kg = seed_knowledge_graph()
    stats = get_db_stats()
    print(json.dumps({
        "seeded": {"feedback": fb, "qaFeedback": qa, "generationLogs": logs, **kg},
        "poemsImported": imported,
        "db": stats,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
