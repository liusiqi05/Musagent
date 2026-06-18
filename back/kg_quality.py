"""
知识图谱实体质量过滤 — 去除脏作者、纯数字、无中文人名等。
"""
from __future__ import annotations

import re

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
JUNK_ID_RE = re.compile(r"^[a-zA-Z0-9._\-]{1,10}$")
NUMERIC_AUTHOR_RE = re.compile(r"^\d+$")
POEM_TITLE_HINT_RE = re.compile(r"[：:《》？！，。、]|病房|笔记|日记|致|写给|赠|\d{2,}")
WORK_TITLE_RE = re.compile(r"(一首|一条|一个|下午|春天|清真寺|河流|普通|实际|生活|景色|彩带|横飞)")
LONG_TITLE_MAX = 36
IMAGERY_WORDS = frozenset(
    "月 风 雨 雪 花 云 山 水 星 夜 春 秋 冬 夏 江 河 海 树 草 灯 路 城 梦 愁 忆 情 心 光 影 烟 霜 露 鸟 鱼 桥 窗 门 楼 台 岸 沙 石 竹 梅 兰 菊 松 柳 霞 虹 波 浪 潮 钟 鼓 琴 酒 茶 烟 火".split()
)

VERTICAL_LABELS = {
    "literature_poetry": "文学诗歌",
}

ENTITY_TYPE_LABELS = {
    "person": "人物",
    "location": "地点",
    "imagery": "意象",
    "work": "作品",
    "organization": "体裁",
    "time": "时间",
    "topic": "主题",
    "unknown": "其他",
}


def vertical_label(code: str) -> str:
    return VERTICAL_LABELS.get(code, "文学诗歌")


def entity_type_label(code: str) -> str:
    return ENTITY_TYPE_LABELS.get(code, "其他")


def format_author(author: str) -> str:
    author = (author or "").strip()
    if not author:
        return "佚名"
    if NUMERIC_AUTHOR_RE.match(author):
        short = author.lstrip("0") or author
        return f"网络诗人 · {short}"
    if JUNK_ID_RE.match(author):
        return "佚名"
    return author


def is_valid_entity_name(name: str, entity_type: str = "") -> bool:
    name = (name or "").strip()
    if not name or len(name) < 2:
        return False
    if name.isdigit():
        return False
    if entity_type == "work" and (name.startswith("《") or CJK_RE.search(name)):
        return len(name) <= 64
    if entity_type == "person":
        if not CJK_RE.search(name):
            return False
        if JUNK_ID_RE.match(name):
            return False
    if not CJK_RE.search(name):
        return False
    if len(name) > 64:
        return False
    if re.search(r"^\d+[^\u4e00-\u9fff]*$", name):
        return False
    return True


def _guess_entity_type(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return "unknown"
    if POEM_TITLE_HINT_RE.search(name) or WORK_TITLE_RE.search(name) or len(name) > 8:
        return "work"
    if name in IMAGERY_WORDS or (len(name) <= 2 and CJK_RE.search(name)):
        return "imagery"
    if 2 <= len(name) <= 4 and CJK_RE.search(name):
        return "person"
    return "unknown"


def infer_entity_types(nodes: list[dict], edges: list[dict]) -> list[dict]:
    """根据关系边推断 unknown 实体的类型。"""
    type_map: dict[str, str] = {}
    weight_map: dict[str, int] = {}

    for node in nodes:
        nid = node.get("id") or ""
        etype = node.get("type") or "unknown"
        if etype != "unknown":
            type_map[nid] = etype
        weight_map[nid] = max(weight_map.get(nid, 0), int(node.get("weight") or 1))

    for edge in edges:
        rel = edge.get("relation") or ""
        head, tail = edge.get("head", ""), edge.get("tail", "")
        if rel == "authored_by":
            type_map[head] = "work"
            if is_valid_entity_name(tail, "person"):
                type_map[tail] = "person"
        elif rel == "contains_imagery":
            type_map[tail] = "imagery"
        elif rel in ("evokes_emotion", "emotion_resonance", "has_emotion"):
            type_map[tail] = "topic"
        elif rel in ("imagery_co_occurs", "semantic_echo", "theme_echo"):
            if is_valid_entity_name(tail):
                type_map[tail] = type_map.get(tail) or "imagery"
        elif rel == "belongs_to_type":
            type_map[tail] = "organization"
        elif rel == "located_in":
            type_map[tail] = "location"
        elif rel == "inspired_by":
            type_map[tail] = "work"

    out = []
    seen: set[str] = set()
    for node in nodes:
        nid = node.get("id") or ""
        if not nid or nid in seen:
            continue
        seen.add(nid)
        etype = type_map.get(nid) or node.get("type") or "unknown"
        if etype == "unknown":
            etype = _guess_entity_type(nid)
        if etype == "person" and (POEM_TITLE_HINT_RE.search(nid) or WORK_TITLE_RE.search(nid) or len(nid) > 6):
            etype = "work"
        out.append({
            **node,
            "id": nid,
            "type": etype,
            "typeLabel": entity_type_label(etype),
            "weight": weight_map.get(nid, node.get("weight", 1)),
        })
    return out


def truncate_label(text: str, max_len: int = LONG_TITLE_MAX) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def filter_nodes(nodes: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for node in nodes:
        nid = node.get("id") or node.get("name") or ""
        etype = node.get("type") or "unknown"
        if not is_valid_entity_name(nid, etype):
            continue
        if nid in seen:
            continue
        seen.add(nid)
        out.append({**node, "id": nid, "type": etype, "typeLabel": entity_type_label(etype)})
    return out


def filter_edges(edges: list[dict], min_confidence: float = 0.6, max_meta_ratio: float = 0.25) -> list[dict]:
    from kg_engine import META_RELATIONS, sort_edges_by_literary_value

    sorted_edges = sort_edges_by_literary_value(edges)
    out = []
    meta_count = 0
    max_meta = max(1, int(len(sorted_edges) * max_meta_ratio))

    for edge in sorted_edges:
        head, tail = edge.get("head", ""), edge.get("tail", "")
        rel = edge.get("relation") or ""
        conf = float(edge.get("confidence") or 0)
        if conf < min_confidence and edge.get("source") not in ("seed", "topic", "bert-re", "retrieval", "poem_emotion"):
            continue
        if not is_valid_entity_name(head) or not is_valid_entity_name(tail):
            continue
        if len(head) > 48 or len(tail) > 48:
            continue
        if rel in META_RELATIONS:
            if meta_count >= max_meta:
                continue
            meta_count += 1
        out.append({
            **edge,
            "head": truncate_label(head, 28),
            "tail": truncate_label(tail, 20),
        })
    return out
