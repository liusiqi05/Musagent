"""
知识图谱引擎 — 结构化实体、关系抽取、文学垂直领域图谱构建。
关系抽取采用 BERT-NER + 规则模板 + 共现统计，并导出 RE 训练样本格式。
"""
from __future__ import annotations

import json
import logging
import re
from collections import Counter, defaultdict
from typing import Any

from config import VERTICAL_DOMAIN
from database import get_knowledge_graph, save_relation, upsert_entity

logger = logging.getLogger("musagent.kg")

# 文学语义关系（面向创作者：文本—意象—情感，而非书目元数据）
LITERATURE_RELATIONS = {
    "imagery_co_occurs": "意象共现",
    "evokes_emotion": "唤起情感",
    "emotion_resonance": "情感共鸣",
    "theme_echo": "主题呼应",
    "symbolizes": "象征",
    "semantic_echo": "语义呼应",
    "contains_imagery": "含意象",
    "metaphor_of": "比喻",
    "inspired_by": "借鉴",
    "co_occurs_with": "同现",
    "related_to": "关联",
    "located_in": "场景",
    "has_emotion": "情感基调",
    # 元数据类 — 保留但展示优先级低
    "authored_by": "作者",
    "belongs_to_type": "体裁",
    "has_attribute": "属性",
}

# 图谱展示时优先语义关系，压低「作者/体裁」元数据边
LITERARY_RELATION_PRIORITY = {
    "imagery_co_occurs": 100,
    "evokes_emotion": 98,
    "emotion_resonance": 96,
    "theme_echo": 94,
    "symbolizes": 92,
    "semantic_echo": 90,
    "metaphor_of": 88,
    "contains_imagery": 85,
    "inspired_by": 82,
    "has_emotion": 80,
    "co_occurs_with": 70,
    "related_to": 60,
    "located_in": 55,
    "has_attribute": 40,
    "authored_by": 15,
    "belongs_to_type": 10,
}

META_RELATIONS = frozenset({"authored_by", "belongs_to_type"})

RELATION_PATTERNS = [
    (re.compile(r"(.+?)如(.+?)般"), "metaphor_of"),
    (re.compile(r"(.+?)般的(.+?)"), "symbolizes"),
    (re.compile(r"(.+?)像(.+?)"), "metaphor_of"),
    (re.compile(r"(.+?)与(.+?)"), "imagery_co_occurs"),
    (re.compile(r"(.+?)在(.+?)"), "located_in"),
]

_kg_built = False


def extract_relations_from_text(text: str, entities: dict | None = None) -> list[dict]:
    """从文本中抽取关系三元组（BERT-RE + 规则 + 实体配对）。"""
    text = (text or "").strip()
    if not text:
        return []

    relations: list[dict] = []

    # BERT-RE 微调模型（若已训练）
    try:
        from re_model import extract_relations_bert
        bert_rels = extract_relations_bert(text, entities)
        relations.extend(bert_rels)
    except Exception:
        pass

    for pattern, rel in RELATION_PATTERNS:
        for match in pattern.finditer(text):
            head, tail = match.group(1).strip(), match.group(2).strip()
            if len(head) >= 2 and len(tail) >= 2:
                relations.append({
                    "head": head[:32],
                    "relation": rel,
                    "tail": tail[:32],
                    "confidence": 0.62,
                    "source": "pattern",
                })

    if entities:
        flat = []
        ent_src = entities.get("entities") if isinstance(entities.get("entities"), dict) else entities
        if isinstance(ent_src, dict):
            for etype, words in ent_src.items():
                if isinstance(words, list):
                    for w in words:
                        flat.append((w, etype))
        for i, (h, ht) in enumerate(flat):
            for j, (t, tt) in enumerate(flat):
                if i >= j or h == t:
                    continue
                if ht == "imagery" and tt == "imagery":
                    rel = "imagery_co_occurs"
                    conf = 0.72
                elif ht == tt:
                    rel = "co_occurs_with"
                    conf = 0.55
                else:
                    rel = "related_to"
                    conf = 0.52
                relations.append({
                    "head": h,
                    "relation": rel,
                    "tail": t,
                    "confidence": conf,
                    "source": "entity_pair",
                    "metadata": {"headType": ht, "tailType": tt},
                })

    dedup = {}
    for rel in relations:
        key = (rel["head"], rel["relation"], rel["tail"])
        if key not in dedup or rel["confidence"] > dedup[key]["confidence"]:
            dedup[key] = rel
    return list(dedup.values())[:40]


def sort_edges_by_literary_value(edges: list[dict]) -> list[dict]:
    """语义关系优先，元数据关系靠后。"""
    return sorted(
        edges,
        key=lambda e: (
            LITERARY_RELATION_PRIORITY.get(e.get("relation", ""), 30),
            float(e.get("confidence") or 0),
        ),
        reverse=True,
    )


def diversify_edges_for_display(edges: list[dict], limit: int = 80) -> list[dict]:
    """展示时保证多种语义关系都有代表，避免单一类型占满视图。"""
    from collections import defaultdict

    by_rel: dict[str, list[dict]] = defaultdict(list)
    for e in edges:
        by_rel[e.get("relation", "")].append(e)

    per_type = max(6, limit // max(len(by_rel), 1))
    mixed: list[dict] = []
    for rel in sorted(by_rel.keys(), key=lambda r: LITERARY_RELATION_PRIORITY.get(r, 0), reverse=True):
        mixed.extend(by_rel[rel][:per_type])
    return sort_edges_by_literary_value(mixed)[:limit]


def _poem_emotion(poem: dict) -> str:
    emo = (poem.get("emotion") or "").strip()
    if emo and emo not in ("未知", "平静", ""):
        return emo
    cached = poem.get("_kg_emotion")
    if cached is not None:
        return cached
    content = (poem.get("content") or "").strip()
    if not content:
        poem["_kg_emotion"] = ""
        return ""
    try:
        from nlp_engine import segment, _analyze_sentiment_dictionary
        words = segment(content[:300])["words"]
        emo = _analyze_sentiment_dictionary(words).get("dominant", "")
        if emo in ("平静", "未知"):
            emo = ""
    except Exception:
        emo = ""
    poem["_kg_emotion"] = emo
    return emo


def _poem_keywords(poem: dict) -> list[str]:
    cached = poem.get("_kg_keywords")
    if cached is not None:
        return cached
    keywords = poem.get("keywords") or []
    if keywords and isinstance(keywords[0], dict):
        keywords = [k.get("keyword", "") for k in keywords if k.get("keyword")]
    out = []
    seen = set()
    for kw in keywords:
        w = (kw if isinstance(kw, str) else str(kw)).strip()
        if len(w) >= 2 and w not in seen:
            seen.add(w)
            out.append(w[:20])
    if len(out) >= 2:
        poem["_kg_keywords"] = out[:10]
        return out[:10]

    # 库内无 keywords 时：优先文学意象词典 + 情感词面，再 TF-IDF
    content = (poem.get("content") or poem.get("title") or "").strip()
    if not content:
        poem["_kg_keywords"] = out
        return out
    try:
        from nlp_engine import segment, extract_keywords, EMOTION_DICT, _is_low_quality_word
        from kg_quality import IMAGERY_WORDS

        words = segment(content[:400])["words"]
        emotion_surface = {kw for kws in EMOTION_DICT.values() for kw in kws}

        def _poetic_word(w: str) -> bool:
            if _is_low_quality_word(w) or w in seen:
                return False
            if w in IMAGERY_WORDS or w in emotion_surface:
                return True
            if len(w) < 2 or len(w) > 4:
                return False
            if not all("\u4e00" <= c <= "\u9fff" for c in w):
                return False
            if w.endswith(("过", "着", "了", "地", "得", "起来")) or w.startswith(("关于", "这样", "什么", "如何")):
                return False
            return len(w) <= 3

        for w in words:
            if w in IMAGERY_WORDS and w not in seen:
                seen.add(w)
                out.append(w)
        for w in words:
            if w in emotion_surface and w not in seen:
                seen.add(w)
                out.append(w[:20])
        if len(out) < 3:
            for item in extract_keywords(words, 12, words):
                w = item.get("keyword", "")
                if _poetic_word(w):
                    seen.add(w)
                    out.append(w[:20])
            for w in words:
                if _poetic_word(w):
                    seen.add(w)
                    out.append(w)
    except Exception:
        pass
    poem["_kg_keywords"] = out[:10]
    return out[:10]


def _build_text_semantic_relations(poem: dict) -> list[dict]:
    """从单首诗内部抽取意象共现、情感—意象、文本语义关系。"""
    from kg_quality import is_valid_entity_name

    title = (poem.get("title") or "").strip()[:28]
    content = poem.get("content") or ""
    emotion = _poem_emotion(poem)
    keywords = _poem_keywords(poem)
    rels: list[dict] = []

    # 意象 ↔ 意象（同在一首诗内共现）
    for i, k1 in enumerate(keywords):
        for k2 in keywords[i + 1 : min(i + 4, len(keywords))]:
            if k1 != k2:
                rels.append({
                    "head": k1,
                    "relation": "imagery_co_occurs",
                    "tail": k2,
                    "confidence": 0.82,
                    "source": "poem_imagery",
                    "metadata": {"work": title},
                })

    # 意象 → 情感（文本内的情感质感）
    if emotion and emotion not in ("平静", "未知"):
        for kw in keywords[:6]:
            rels.append({
                "head": kw,
                "relation": "evokes_emotion",
                "tail": emotion,
                "confidence": 0.85,
                "source": "poem_emotion",
            })
        if title:
            rels.append({
                "head": title,
                "relation": "emotion_resonance",
                "tail": emotion,
                "confidence": 0.88,
                "source": "poem_emotion",
            })

    # 主题/标题 — 意象（文本内容层）
    if title:
        for kw in keywords[:5]:
            rels.append({
                "head": title,
                "relation": "contains_imagery",
                "tail": kw,
                "confidence": 0.8,
                "source": "poem_keywords",
            })

    # 正文模式：比喻、象征（批量建图仅用规则，避免加载 BERT-RE）
    for pattern, rel in RELATION_PATTERNS:
        for match in pattern.finditer(content):
            head, tail = match.group(1).strip(), match.group(2).strip()
            if len(head) >= 2 and len(tail) >= 2:
                rels.append({
                    "head": head[:32],
                    "relation": rel,
                    "tail": tail[:32],
                    "confidence": 0.62,
                    "source": "pattern",
                })

    return rels


def build_poem_relations(poem: dict) -> list[dict]:
    from kg_quality import is_valid_entity_name

    title = poem.get("title", "")
    author = (poem.get("author", "") or "").strip()
    if not is_valid_entity_name(author, "person"):
        author = ""
    poem_type = poem.get("type", poem.get("poem_type", "现代诗"))
    emotion = poem.get("emotion", "平静")

    rels = _build_text_semantic_relations(poem)

    # 元数据关系：保留但置信度刻意降低，避免霸占图谱
    if title and author:
        rels.append({
            "head": title, "relation": "authored_by", "tail": author,
            "confidence": 0.62, "source": "poem_meta",
        })
    if title and poem_type:
        rels.append({
            "head": title, "relation": "belongs_to_type", "tail": poem_type,
            "confidence": 0.58, "source": "poem_meta",
        })

    dedup = {}
    for rel in rels:
        key = (rel["head"], rel["relation"], rel["tail"])
        if key not in dedup or rel["confidence"] > dedup[key]["confidence"]:
            dedup[key] = rel
    return list(dedup.values())


def persist_entities_and_relations(entities: dict, relations: list[dict], source: str = "pipeline") -> dict:
    saved_entities = 0
    saved_relations = 0

    ent_map = entities.get("entities") if isinstance(entities.get("entities"), dict) else entities
    if isinstance(ent_map, dict):
        for etype, words in ent_map.items():
            if not isinstance(words, list):
                continue
            for word in words:
                if word and len(word) >= 2:
                    upsert_entity(word, etype, source=source)
                    saved_entities += 1

    for rel in relations:
        save_relation(
            rel["head"],
            rel["relation"],
            rel["tail"],
            confidence=float(rel.get("confidence", 0.5)),
            source=rel.get("source", source),
            metadata=rel.get("metadata"),
        )
        saved_relations += 1

    return {"entities": saved_entities, "relations": saved_relations}


def build_knowledge_graph_from_poems(poems: list[dict], max_poems: int = 800, clear_existing: bool = True) -> dict:
    """批量从诗歌库构建文学垂直知识图谱（语义关系为主）。"""
    from kg_quality import is_valid_entity_name
    from database import clear_vertical_relations

    global _kg_built
    if clear_existing:
        clear_vertical_relations()

    relation_counter: Counter = Counter()
    entity_counter: Counter = Counter()
    emotion_imagery: dict[str, Counter] = defaultdict(Counter)
    from kg_quality import IMAGERY_WORDS as _IMAGERY
    from nlp_engine import EMOTION_DICT
    emotion_surface = {k for kws in EMOTION_DICT.values() for k in kws}

    for poem in poems[:max_poems]:
        rels = build_poem_relations(poem)
        for rel in rels:
            save_relation(rel["head"], rel["relation"], rel["tail"], rel["confidence"], rel.get("source", "batch"))
            relation_counter[rel["relation"]] += 1
        for kw in _poem_keywords(poem):
            upsert_entity(kw, "imagery", source="batch")
            entity_counter[kw] += 1
            emo = _poem_emotion(poem)
            if emo and (kw in _IMAGERY or kw in emotion_surface):
                emotion_imagery[emo][kw] += 1
        if poem.get("author") and is_valid_entity_name(str(poem.get("author", "")), "person"):
            upsert_entity(poem["author"], "person", source="batch")
        if poem.get("title"):
            upsert_entity(poem["title"], "work", source="batch")

    # 跨诗情感—意象：同一情感下高频意象互相关联（仅统计文学意象词）
    for emotion, kw_counts in emotion_imagery.items():
        if emotion in ("平静", "未知", "") or len(kw_counts) < 2:
            continue
        top_kw = [w for w, c in kw_counts.most_common(8) if w in _IMAGERY or c >= 2]
        if len(top_kw) < 2:
            continue
        for i, k1 in enumerate(top_kw):
            save_relation(k1, "evokes_emotion", emotion, 0.86, "corpus_emotion")
            relation_counter["evokes_emotion"] += 1
            for k2 in top_kw[i + 1 : i + 3]:
                save_relation(k1, "emotion_resonance", k2, 0.75, "corpus_emotion",
                               metadata={"sharedEmotion": emotion})
                relation_counter["emotion_resonance"] += 1

    _kg_built = True
    graph = get_knowledge_graph(limit=120)
    return {
        "built": True,
        "processedPoems": min(len(poems), max_poems),
        "relationTypes": dict(relation_counter.most_common(12)),
        "topImagery": [w for w, _ in entity_counter.most_common(15)],
        "graph": graph,
        "vertical": VERTICAL_DOMAIN,
        "relationLabels": LITERATURE_RELATIONS,
        "focus": "text_semantic",
    }


def analyze_topic_graph(
    topic: str,
    entities: dict,
    similar_works: list[dict] | None = None,
    emotion: str = "",
    keywords: list | None = None,
) -> dict:
    """针对单次创作主题构建局部子图 — 主题/意象/情感/参考文本，而非作者元数据。"""
    relations = extract_relations_from_text(topic, entities)
    nodes = defaultdict(lambda: {"type": "unknown", "weight": 1})
    topic_label = (topic or "主题")[:24]
    nodes[topic_label] = {"id": topic_label, "type": "topic", "weight": 3}

    ent_map = entities.get("entities") if isinstance(entities.get("entities"), dict) else {}
    for etype, words in ent_map.items():
        for w in words or []:
            nodes[w] = {"id": w, "type": etype, "weight": nodes[w]["weight"] + 1}
            upsert_entity(w, etype, source="topic")
            relations.append({
                "head": topic_label,
                "relation": "contains_imagery" if etype == "imagery" else "theme_echo",
                "tail": w,
                "confidence": 0.84,
                "source": "topic",
            })

    dom_emotion = (emotion or "").strip()
    if dom_emotion and dom_emotion not in ("自动", "未知"):
        nodes[dom_emotion] = {"id": dom_emotion, "type": "topic", "weight": 2}
        relations.append({
            "head": topic_label,
            "relation": "emotion_resonance",
            "tail": dom_emotion,
            "confidence": 0.9,
            "source": "topic",
        })
        for w in (ent_map.get("imagery") or [])[:4]:
            relations.append({
                "head": w,
                "relation": "evokes_emotion",
                "tail": dom_emotion,
                "confidence": 0.86,
                "source": "topic",
            })

    for kw_item in (keywords or [])[:5]:
        kw = kw_item.get("keyword", kw_item) if isinstance(kw_item, dict) else str(kw_item)
        kw = kw.strip()
        if len(kw) < 2:
            continue
        nodes[kw] = {"id": kw, "type": "imagery", "weight": 2}
        relations.append({
            "head": topic_label,
            "relation": "theme_echo",
            "tail": kw,
            "confidence": 0.83,
            "source": "topic",
        })

    for work in (similar_works or [])[:3]:
        title = (work.get("title") or "")[:28]
        if not title:
            continue
        nodes[title] = {"id": title, "type": "work", "weight": 2}
        relations.append({
            "head": topic_label,
            "relation": "inspired_by",
            "tail": title,
            "confidence": float(work.get("rerankScore") or work.get("similarity") or 0.72),
            "source": "retrieval",
        })
        work_emotion = (work.get("emotion") or work.get("dominant") or "").strip()
        if work_emotion:
            relations.append({
                "head": title,
                "relation": "emotion_resonance",
                "tail": work_emotion,
                "confidence": 0.8,
                "source": "retrieval",
            })
        for term in (work.get("matchedTerms") or work.get("semanticExplanation", {}).get("sharedKeywords") or [])[:4]:
            term = str(term).strip()
            if len(term) < 2:
                continue
            nodes[term] = {"id": term, "type": "imagery", "weight": 2}
            relations.append({
                "head": topic_label,
                "relation": "semantic_echo",
                "tail": term,
                "confidence": 0.78,
                "source": "retrieval",
            })
            relations.append({
                "head": title,
                "relation": "contains_imagery",
                "tail": term,
                "confidence": 0.76,
                "source": "retrieval",
            })

    persist_entities_and_relations(ent_map, relations, source="topic")

    from kg_quality import filter_nodes, filter_edges, vertical_label

    re_method = "意象/情感语义规则"
    try:
        from re_model import get_re_model_info
        if get_re_model_info().get("available"):
            re_method = "BERT-RE + 语义规则"
    except Exception:
        pass

    raw_nodes = list(nodes.values())
    raw_edges = sort_edges_by_literary_value(relations)[:30]
    clean_nodes = filter_nodes(raw_nodes)
    clean_edges = filter_edges(raw_edges, min_confidence=0.55, max_meta_ratio=0.15)

    return {
        "nodes": clean_nodes,
        "edges": clean_edges,
        "vertical": VERTICAL_DOMAIN,
        "verticalLabel": vertical_label(VERTICAL_DOMAIN),
        "relationLabels": LITERATURE_RELATIONS,
        "method": re_method,
        "topic": topic[:48],
    }


def export_re_training_samples(poems: list[dict], output_path: str, limit: int = 2000) -> dict:
    """导出关系抽取 BERT 微调训练样本（含负样本）。"""
    try:
        from re_model import export_dataset
        return export_dataset(poems, output_path, limit=limit)
    except Exception as exc:
        logger.warning("export_dataset failed, fallback: %s", exc)

    samples = []
    for poem in poems[:limit]:
        text = f"{poem.get('title', '')} {poem.get('content', '')}"[:256]
        for rel in build_poem_relations(poem):
            if rel["relation"] in ("authored_by", "has_emotion", "contains_imagery", "belongs_to_type"):
                samples.append({
                    "text": text,
                    "head": rel["head"],
                    "tail": rel["tail"],
                    "relation": rel["relation"],
                    "label": 1,
                    "vertical": VERTICAL_DOMAIN,
                })

    path_written = False
    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                for row in samples:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            path_written = True
        except Exception as exc:
            logger.warning("Export RE samples failed: %s", exc)

    return {
        "count": len(samples),
        "path": output_path if path_written else None,
        "relations": list({s["relation"] for s in samples}),
        "note": "可用于 ckiplab/bert-base-chinese 或 hfl/chinese-bert-wwm-ext 关系抽取微调",
    }
