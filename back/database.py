"""
SQLite 持久化 — 诗歌索引、用户反馈、知识图谱、对话历史。
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import BASE_DIR, DATA_DIR, DB_PATH, VERTICAL_DOMAIN

logger = logging.getLogger("musagent.db")

_local = threading.local()
_poems_imported = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_conn() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = _connect()
        _local.conn = conn
    return conn


@contextmanager
def db_cursor():
    conn = get_conn()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise


_db_initialized = False


def ensure_db() -> None:
    global _db_initialized
    if not _db_initialized:
        init_db()


def init_db() -> None:
    global _db_initialized
    with db_cursor() as cur:
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS poems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                content TEXT NOT NULL,
                poem_type TEXT DEFAULT '现代诗',
                emotion TEXT DEFAULT '平静',
                keywords TEXT DEFAULT '[]',
                vertical TEXT DEFAULT 'literature_poetry',
                created_at TEXT NOT NULL,
                UNIQUE(title, author)
            );
            CREATE INDEX IF NOT EXISTS idx_poems_type ON poems(poem_type);
            CREATE INDEX IF NOT EXISTS idx_poems_emotion ON poems(emotion);
            CREATE INDEX IF NOT EXISTS idx_poems_vertical ON poems(vertical);
            CREATE INDEX IF NOT EXISTS idx_poems_author ON poems(author);

            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_id TEXT,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                comment TEXT DEFAULT '',
                topic TEXT DEFAULT '',
                content_preview TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                vertical TEXT DEFAULT 'literature_poetry',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_feedback_source ON feedback(source_type, created_at);

            CREATE TABLE IF NOT EXISTS qa_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                helpful INTEGER DEFAULT 1,
                tags TEXT DEFAULT '[]',
                vertical TEXT DEFAULT 'literature_poetry',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                vertical TEXT DEFAULT 'literature_poetry',
                source TEXT DEFAULT 'auto',
                frequency INTEGER DEFAULT 1,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                UNIQUE(name, entity_type, vertical)
            );
            CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);

            CREATE TABLE IF NOT EXISTS entity_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                head TEXT NOT NULL,
                relation TEXT NOT NULL,
                tail TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                source TEXT DEFAULT 'auto',
                vertical TEXT DEFAULT 'literature_poetry',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_rel_head ON entity_relations(head);
            CREATE INDEX IF NOT EXISTS idx_rel_tail ON entity_relations(tail);
            CREATE INDEX IF NOT EXISTS idx_rel_type ON entity_relations(relation);

            CREATE TABLE IF NOT EXISTS generation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                creation_type TEXT DEFAULT '现代诗',
                quality_score REAL DEFAULT 0,
                quality_label TEXT DEFAULT '',
                method TEXT DEFAULT '',
                passed_filter INTEGER DEFAULT 1,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                title TEXT DEFAULT '新对话',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_chat_sessions_client ON chat_sessions(client_id, updated_at DESC);

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                nlp TEXT DEFAULT '{}',
                llm_used INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id, id);

            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                display_name TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            """
        )
        _migrate_schema(cur)
    _db_initialized = True


def _migrate_schema(cur) -> None:
    """增量迁移 — 兼容已有数据库。"""
    try:
        cur.execute("ALTER TABLE chat_sessions ADD COLUMN user_id TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id, updated_at DESC)")
    except sqlite3.OperationalError:
        pass


def import_poems_from_json(json_path: Path | None = None, force: bool = False) -> int:
    global _poems_imported
    ensure_db()
    if _poems_imported and not force:
        with db_cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM poems")
            count = cur.fetchone()["c"]
            if count > 0:
                return count

    path = json_path or (BASE_DIR.parent / "musagent" / "src" / "data" / "poems_extracted.json")
    if not path.exists():
        logger.warning("Poem JSON not found: %s", path)
        return 0

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, list):
        poems = raw
    else:
        poems = []
        for p in raw.get("modern", []):
            poems.append({**p, "type": p.get("type", "现代诗")})
        for p in raw.get("classical", []):
            poems.append({**p, "type": p.get("type", "古典诗")})

    now = _now_iso()
    inserted = 0
    with db_cursor() as cur:
        for poem in poems:
            keywords = poem.get("keywords") or []
            if isinstance(keywords, list) and keywords and isinstance(keywords[0], dict):
                keywords = [k.get("keyword", "") for k in keywords if k.get("keyword")]
            cur.execute(
                """
                INSERT OR IGNORE INTO poems
                (title, author, content, poem_type, emotion, keywords, vertical, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    poem.get("title", ""),
                    poem.get("author", ""),
                    poem.get("content", ""),
                    poem.get("type", poem.get("poem_type", "现代诗")),
                    poem.get("emotion", "平静"),
                    json.dumps(keywords[:12], ensure_ascii=False),
                    VERTICAL_DOMAIN,
                    now,
                ),
            )
            if cur.rowcount:
                inserted += 1
    _poems_imported = True
    logger.info("Imported %s poems into SQLite", inserted)
    return inserted


def query_poems(
    page: int = 1,
    page_size: int = 30,
    search: str = "",
    emotion: str = "all",
    poem_type: str = "all",
) -> dict:
    from kg_quality import format_author

    ensure_db()
    clauses = ["vertical = ?"]
    params: list[Any] = [VERTICAL_DOMAIN]

    if poem_type != "all":
        clauses.append("poem_type = ?")
        params.append(poem_type)
    if emotion != "all":
        clauses.append("emotion = ?")
        params.append(emotion)
    if search:
        clauses.append("(title LIKE ? OR author LIKE ? OR content LIKE ? OR keywords LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like, like])

    where = " AND ".join(clauses)
    offset = (max(page, 1) - 1) * page_size

    with db_cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS c FROM poems WHERE {where}", params)
        total = cur.fetchone()["c"]
        cur.execute(
            f"""
            SELECT id, title, author, content, poem_type AS type, emotion, keywords
            FROM poems WHERE {where}
            ORDER BY id ASC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        )
        rows = cur.fetchall()

    items = []
    for row in rows:
        kw = json.loads(row["keywords"] or "[]")
        items.append(
            {
                "id": row["id"],
                "title": row["title"],
                "author": format_author(row["author"]),
                "content": row["content"],
                "type": row["type"],
                "emotion": row["emotion"],
                "keywords": kw,
            }
        )
    return {
        "items": items,
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": max(1, (total + page_size - 1) // page_size),
        "source": "sqlite",
        "vertical": VERTICAL_DOMAIN,
    }


def save_feedback(
    source_type: str,
    rating: int,
    comment: str = "",
    topic: str = "",
    content_preview: str = "",
    source_id: str = "",
    metadata: dict | None = None,
) -> dict:
    ensure_db()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO feedback
            (source_type, source_id, rating, comment, topic, content_preview, metadata, vertical, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_type,
                source_id,
                rating,
                comment,
                topic,
                content_preview[:500],
                json.dumps(metadata or {}, ensure_ascii=False),
                VERTICAL_DOMAIN,
                _now_iso(),
            ),
        )
        fid = cur.lastrowid
    return {"id": fid, "saved": True}


def save_qa_feedback(
    question: str,
    answer: str,
    rating: int,
    helpful: bool = True,
    tags: list[str] | None = None,
) -> dict:
    ensure_db()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO qa_feedback
            (question, answer, rating, helpful, tags, vertical, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question,
                answer,
                rating,
                1 if helpful else 0,
                json.dumps(tags or [], ensure_ascii=False),
                VERTICAL_DOMAIN,
                _now_iso(),
            ),
        )
        qid = cur.lastrowid
    return {"id": qid, "saved": True}


def get_feedback_stats() -> dict:
    ensure_db()
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT source_type, COUNT(*) AS count, ROUND(AVG(rating), 2) AS avg_rating
            FROM feedback GROUP BY source_type
            """
        )
        by_source = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT COUNT(*) AS c, ROUND(AVG(rating), 2) AS avg FROM feedback")
        overall = dict(cur.fetchone())
        cur.execute(
            """
            SELECT COUNT(*) AS c, ROUND(AVG(rating), 2) AS avg
            FROM qa_feedback
            """
        )
        qa = dict(cur.fetchone())
    return {"overall": overall, "bySource": by_source, "qa": qa}


def upsert_entity(name: str, entity_type: str, source: str = "auto", metadata: dict | None = None) -> None:
    from kg_quality import is_valid_entity_name
    if not is_valid_entity_name(name, entity_type):
        return
    ensure_db()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO entities (name, entity_type, vertical, source, frequency, metadata, created_at)
            VALUES (?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(name, entity_type, vertical) DO UPDATE SET
                frequency = frequency + 1,
                metadata = excluded.metadata
            """,
            (name, entity_type, VERTICAL_DOMAIN, source, json.dumps(metadata or {}, ensure_ascii=False), _now_iso()),
        )


def save_relation(head: str, relation: str, tail: str, confidence: float = 0.5, source: str = "auto", metadata: dict | None = None) -> None:
    ensure_db()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO entity_relations
            (head, relation, tail, confidence, source, vertical, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (head, relation, tail, confidence, source, VERTICAL_DOMAIN, json.dumps(metadata or {}, ensure_ascii=False), _now_iso()),
        )


def clear_vertical_relations(vertical: str | None = None) -> int:
    """清空垂直领域关系边，用于重建语义图谱。"""
    ensure_db()
    v = vertical or VERTICAL_DOMAIN
    with db_cursor() as cur:
        cur.execute("DELETE FROM entity_relations WHERE vertical = ?", (v,))
        return cur.rowcount


def get_knowledge_graph(limit: int = 80, entity: str = "", curated: bool = True) -> dict:
    from kg_quality import filter_nodes, filter_edges, vertical_label, entity_type_label, infer_entity_types

    ensure_db()
    with db_cursor() as cur:
        if entity:
            cur.execute(
                """
                SELECT head, relation, tail, confidence, source
                FROM entity_relations
                WHERE vertical = ? AND (head = ? OR tail = ?)
                ORDER BY confidence DESC LIMIT ?
                """,
                (VERTICAL_DOMAIN, entity, entity, limit * 2),
            )
        else:
            cur.execute(
                """
                SELECT head, relation, tail, confidence, source
                FROM entity_relations
                WHERE vertical = ?
                LIMIT ?
                """,
                (VERTICAL_DOMAIN, limit * 25),
            )
        edges = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT name, entity_type, frequency
            FROM entities WHERE vertical = ?
            ORDER BY frequency DESC LIMIT ?
            """,
            (VERTICAL_DOMAIN, min(limit * 2, 200)),
        )
        nodes = [{"id": r["name"], "type": r["entity_type"], "weight": r["frequency"]} for r in cur.fetchall()]

    if curated:
        from kg_engine import sort_edges_by_literary_value, diversify_edges_for_display
        edges = sort_edges_by_literary_value(edges)
        nodes = filter_nodes(nodes)
        edges = filter_edges(edges, min_confidence=0.65, max_meta_ratio=0.2)
        edges = diversify_edges_for_display(edges, limit)
        node_ids = {n["id"] for n in nodes}
        for e in edges:
            node_ids.add(e["head"])
            node_ids.add(e["tail"])
        nodes = filter_nodes([{"id": nid, "type": "unknown", "weight": 1} for nid in node_ids] + nodes)
        seen = {}
        for n in nodes:
            if n["id"] not in seen or n.get("weight", 0) > seen[n["id"]].get("weight", 0):
                seen[n["id"]] = n
        nodes = list(seen.values())[:limit]
        nodes = infer_entity_types(nodes, edges)

    for n in nodes:
        n["typeLabel"] = entity_type_label(n.get("type", "unknown"))

    return {
        "nodes": nodes,
        "edges": edges,
        "vertical": VERTICAL_DOMAIN,
        "verticalLabel": vertical_label(VERTICAL_DOMAIN),
        "entityCount": len(nodes),
        "relationCount": len(edges),
        "curated": curated,
    }


def log_generation(topic: str, creation_type: str, quality_score: float, quality_label: str, method: str, passed: bool, metadata: dict | None = None) -> None:
    ensure_db()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO generation_logs
            (topic, creation_type, quality_score, quality_label, method, passed_filter, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic,
                creation_type,
                quality_score,
                quality_label,
                method,
                1 if passed else 0,
                json.dumps(metadata or {}, ensure_ascii=False),
                _now_iso(),
            ),
        )


def get_db_stats() -> dict:
    ensure_db()
    with db_cursor() as cur:
        stats = {}
        for table in ("poems", "feedback", "qa_feedback", "entities", "entity_relations", "generation_logs", "chat_sessions", "chat_messages"):
            cur.execute(f"SELECT COUNT(*) AS c FROM {table}")
            stats[table] = cur.fetchone()["c"]
    return {"path": DB_PATH, "tables": stats, "vertical": VERTICAL_DOMAIN}


def _truncate_title(text: str, max_len: int = 28) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= max_len:
        return text or "新对话"
    return text[: max_len - 1] + "…"


def create_chat_session(client_id: str, title: str = "新对话", user_id: str | None = None) -> dict:
    ensure_db()
    session_id = str(uuid.uuid4())
    now = _now_iso()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO chat_sessions (id, client_id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, client_id, user_id, title, now, now),
        )
    return {
        "id": session_id,
        "clientId": client_id,
        "title": title,
        "createdAt": now,
        "updatedAt": now,
        "messageCount": 0,
    }


def list_chat_sessions(client_id: str, limit: int = 40, user_id: str | None = None) -> list[dict]:
    ensure_db()
    with db_cursor() as cur:
        if user_id:
            cur.execute(
                """
                SELECT s.id, s.title, s.created_at, s.updated_at,
                       (SELECT COUNT(*) FROM chat_messages m WHERE m.session_id = s.id) AS message_count,
                       (SELECT content FROM chat_messages m WHERE m.session_id = s.id AND m.role = 'user'
                        ORDER BY m.id ASC LIMIT 1) AS preview
                FROM chat_sessions s
                WHERE s.user_id = ? OR (s.user_id IS NULL AND s.client_id = ?)
                ORDER BY s.updated_at DESC
                LIMIT ?
                """,
                (user_id, client_id, limit),
            )
        else:
            cur.execute(
                """
                SELECT s.id, s.title, s.created_at, s.updated_at,
                       (SELECT COUNT(*) FROM chat_messages m WHERE m.session_id = s.id) AS message_count,
                       (SELECT content FROM chat_messages m WHERE m.session_id = s.id AND m.role = 'user'
                        ORDER BY m.id ASC LIMIT 1) AS preview
                FROM chat_sessions s
                WHERE s.client_id = ?
                ORDER BY s.updated_at DESC
                LIMIT ?
                """,
                (client_id, limit),
            )
        rows = cur.fetchall()
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "preview": (r["preview"] or "")[:48],
            "messageCount": r["message_count"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"],
        }
        for r in rows
    ]


def get_chat_session(session_id: str, client_id: str) -> dict | None:
    ensure_db()
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, title, created_at, updated_at FROM chat_sessions WHERE id = ? AND client_id = ?",
            (session_id, client_id),
        )
        row = cur.fetchone()
        if not row:
            return None
        cur.execute(
            """
            SELECT id, role, content, nlp, llm_used, created_at
            FROM chat_messages WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        )
        msgs = cur.fetchall()
    messages = []
    for m in msgs:
        nlp = json.loads(m["nlp"] or "{}")
        messages.append({
            "id": m["id"],
            "role": m["role"],
            "content": m["content"],
            "nlp": nlp if nlp else None,
            "llmUsed": bool(m["llm_used"]),
            "createdAt": m["created_at"],
        })
    return {
        "id": row["id"],
        "title": row["title"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "messages": messages,
    }


def get_chat_history_for_llm(session_id: str, limit: int = 20) -> list[dict]:
    ensure_db()
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT role, content FROM chat_messages
            WHERE session_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (session_id, limit),
        )
        rows = list(reversed(cur.fetchall()))
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def append_chat_message(
    session_id: str,
    role: str,
    content: str,
    nlp: dict | None = None,
    llm_used: bool = False,
) -> dict:
    ensure_db()
    now = _now_iso()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO chat_messages (session_id, role, content, nlp, llm_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, role, content, json.dumps(nlp or {}, ensure_ascii=False), 1 if llm_used else 0, now),
        )
        msg_id = cur.lastrowid
        cur.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (now, session_id))
        if role == "user":
            cur.execute("SELECT title FROM chat_sessions WHERE id = ?", (session_id,))
            title_row = cur.fetchone()
            if title_row and (title_row["title"] or "") in ("", "新对话"):
                cur.execute(
                    "UPDATE chat_sessions SET title = ? WHERE id = ?",
                    (_truncate_title(content), session_id),
                )
    return {"id": msg_id, "role": role, "content": content, "createdAt": now}


def delete_chat_session(session_id: str, client_id: str) -> bool:
    ensure_db()
    with db_cursor() as cur:
        cur.execute("DELETE FROM chat_sessions WHERE id = ? AND client_id = ?", (session_id, client_id))
        return cur.rowcount > 0


def create_user(username: str, password_hash: str, password_salt: str, email: str = "", display_name: str = "") -> dict:
    ensure_db()
    user_id = str(uuid.uuid4())
    now = _now_iso()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (id, username, email, password_hash, password_salt, display_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, username.strip(), email.strip() or None, password_hash, password_salt, display_name or username, now),
        )
    return {
        "id": user_id,
        "username": username.strip(),
        "email": email.strip() or None,
        "displayName": display_name or username.strip(),
        "createdAt": now,
    }


def get_user_by_username(username: str) -> dict | None:
    ensure_db()
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, username, email, password_hash, password_salt, display_name, created_at FROM users WHERE username = ?",
            (username.strip(),),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "passwordHash": row["password_hash"],
        "passwordSalt": row["password_salt"],
        "displayName": row["display_name"],
        "createdAt": row["created_at"],
    }


def get_user_by_id(user_id: str) -> dict | None:
    ensure_db()
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, username, email, display_name, created_at FROM users WHERE id = ?",
            (user_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "displayName": row["display_name"],
        "createdAt": row["created_at"],
    }


def bind_client_sessions_to_user(client_id: str, user_id: str) -> int:
    """登录后将匿名对话绑定到账号，便于跨设备同步。"""
    ensure_db()
    with db_cursor() as cur:
        cur.execute(
            "UPDATE chat_sessions SET user_id = ? WHERE client_id = ? AND user_id IS NULL",
            (user_id, client_id),
        )
        return cur.rowcount
