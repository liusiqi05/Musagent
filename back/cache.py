"""
缓存层 — Redis 优先，不可用时降级为进程内 LRU。
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from typing import Any

from config import CACHE_TTL_SECONDS, REDIS_ENABLED, REDIS_URL

logger = logging.getLogger("musagent.cache")

_redis_client = None
_redis_checked = False
_memory_cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
_MEMORY_MAX = 512


def _redis_available() -> bool:
    global _redis_client, _redis_checked
    if REDIS_ENABLED == "false":
        return False
    if _redis_checked:
        return _redis_client is not None
    _redis_checked = True
    try:
        import redis
        client = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=1.5)
        client.ping()
        _redis_client = client
        logger.info("Redis cache connected: %s", REDIS_URL)
        return True
    except Exception as exc:
        if REDIS_ENABLED == "true":
            logger.warning("Redis required but unavailable: %s", exc)
        else:
            logger.info("Redis unavailable, using in-memory cache: %s", exc)
        _redis_client = None
        return False


def _mem_get(key: str) -> Any | None:
    item = _memory_cache.get(key)
    if not item:
        return None
    expires_at, value = item
    if expires_at < time.time():
        _memory_cache.pop(key, None)
        return None
    _memory_cache.move_to_end(key)
    return value


def _mem_set(key: str, value: Any, ttl: int) -> None:
    _memory_cache[key] = (time.time() + ttl, value)
    _memory_cache.move_to_end(key)
    while len(_memory_cache) > _MEMORY_MAX:
        _memory_cache.popitem(last=False)


def make_cache_key(namespace: str, payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"musagent:{namespace}:{digest}"


def cache_get(key: str) -> Any | None:
    if _redis_available():
        try:
            raw = _redis_client.get(key)
            return json.loads(raw) if raw else None
        except Exception as exc:
            logger.warning("Redis get failed: %s", exc)
    return _mem_get(key)


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    ttl = ttl or CACHE_TTL_SECONDS
    if _redis_available():
        try:
            _redis_client.setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str))
            return
        except Exception as exc:
            logger.warning("Redis set failed: %s", exc)
    _mem_set(key, value, ttl)


def cache_delete_prefix(prefix: str) -> int:
    removed = 0
    if _redis_available():
        try:
            keys = list(_redis_client.scan_iter(match=f"{prefix}*"))
            if keys:
                removed = _redis_client.delete(*keys)
        except Exception as exc:
            logger.warning("Redis delete failed: %s", exc)
    stale = [k for k in _memory_cache if k.startswith(prefix)]
    for key in stale:
        _memory_cache.pop(key, None)
        removed += 1
    return removed


def get_cache_info() -> dict:
    return {
        "backend": "redis" if _redis_available() else "memory",
        "ttlSeconds": CACHE_TTL_SECONDS,
        "memoryEntries": len(_memory_cache),
    }
