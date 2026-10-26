"""
Streamable HTTP session store.

The MCP and Admin-MCP endpoints issue a ``Mcp-Session-Id`` on ``initialize`` and
validate it on subsequent Streamable HTTP requests. When Octopus MCP Proxy runs as a single
container the session set can live in process memory, but when the MCP endpoint is
scaled out (multiple replicas / separate hosts) the session must be shared so that a
follow-up request handled by a different replica still recognizes the session.

This module provides a small abstraction with two backends:

- ``InMemorySessionStore``: process-local dict with TTL pruning (single-instance / no Redis).
- ``RedisSessionStore``: shared store backed by Redis ``SETEX`` keys (multi-instance).

The backend is chosen by the ``REDIS_URL`` environment variable:
- set  -> Redis (shared across replicas/hosts)
- unset -> in-memory (zero extra infra; fine for a single container)

Stores are namespaced (e.g. "mcp", "admin") so the two endpoints never collide.
"""

import logging
import os
import threading
import time

from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

# Default session lifetime in seconds (1 hour), matching the previous in-controller TTLs.
DEFAULT_TTL_SECONDS = 3600


class InMemorySessionStore:
    """Process-local session store with lazy TTL expiry. Thread-safe."""

    def __init__(self):
        self._data: dict[str, float] = {}
        self._lock = threading.Lock()

    def register(self, session_id: str, ttl: int = DEFAULT_TTL_SECONDS) -> None:
        now = time.time()
        with self._lock:
            self._data[session_id] = now + ttl
            # Opportunistically prune expired sessions
            expired = [sid for sid, exp in self._data.items() if exp < now]
            for sid in expired:
                self._data.pop(sid, None)

    def is_valid(self, session_id: str) -> bool:
        with self._lock:
            exp = self._data.get(session_id)
            if exp is None:
                return False
            if exp < time.time():
                self._data.pop(session_id, None)
                return False
            return True

    def remove(self, session_id: str) -> None:
        with self._lock:
            self._data.pop(session_id, None)


class RedisSessionStore:
    """Shared session store backed by Redis. TTL is handled by Redis key expiry.

    Session IDs only route legacy Streamable HTTP clients; authentication is done
    with bearer tokens. A Redis outage is therefore logged and treated as "session
    valid" instead of failing every MCP request with a 500.
    """

    def __init__(self, client, prefix: str):
        self._client = client
        self._prefix = prefix

    def _key(self, session_id: str) -> str:
        return f"{self._prefix}{session_id}"

    def register(self, session_id: str, ttl: int = DEFAULT_TTL_SECONDS) -> None:
        try:
            self._client.setex(self._key(session_id), ttl, "1")
        except RedisError:
            logger.exception("Session store unavailable; session not registered")

    def is_valid(self, session_id: str) -> bool:
        try:
            return bool(self._client.exists(self._key(session_id)))
        except RedisError:
            logger.exception("Session store unavailable; accepting session")
            return True

    def remove(self, session_id: str) -> None:
        try:
            self._client.delete(self._key(session_id))
        except RedisError:
            logger.exception("Session store unavailable; session not removed")


# Cache of stores per namespace so each controller reuses one instance.
_stores: dict[str, object] = {}
_stores_lock = threading.Lock()


def _build_store(namespace: str):
    """Build the appropriate backend for the given namespace based on REDIS_URL."""
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        import redis

        client = redis.from_url(redis_url, decode_responses=True)
        return RedisSessionStore(client, prefix=f"accelmcp:session:{namespace}:")
    return InMemorySessionStore()


def get_session_store(namespace: str):
    """Return a cached session store for the namespace, creating it on first use.

    Lazily evaluated so REDIS_URL is read at first request time (after the process
    environment is fully populated), and so tests default to the in-memory backend.
    """
    store = _stores.get(namespace)
    if store is None:
        with _stores_lock:
            store = _stores.get(namespace)
            if store is None:
                store = _build_store(namespace)
                _stores[namespace] = store
    return store


def reset_session_stores() -> None:
    """Clear cached stores. Intended for tests to force backend re-selection."""
    with _stores_lock:
        _stores.clear()
