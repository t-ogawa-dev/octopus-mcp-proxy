"""
Tests for the Streamable HTTP session store abstraction (app/services/session_store.py).

Covers:
- InMemorySessionStore: register / is_valid / remove / TTL expiry / namespace isolation
- RedisSessionStore: backed by fakeredis, including key namespacing and TTL
- get_session_store(): backend selection via REDIS_URL, caching, namespace separation
"""

import time

import pytest

from app.services.session_store import (
    InMemorySessionStore,
    RedisSessionStore,
    get_session_store,
    reset_session_stores,
)


@pytest.fixture(autouse=True)
def _clear_stores():
    """Each test starts with a clean store cache."""
    reset_session_stores()
    yield
    reset_session_stores()


# ---------------------------------------------------------------------------
# InMemorySessionStore
# ---------------------------------------------------------------------------


class TestInMemorySessionStore:
    def test_register_and_validate(self):
        store = InMemorySessionStore()
        store.register("sid-1", ttl=60)
        assert store.is_valid("sid-1") is True

    def test_unknown_session_is_invalid(self):
        store = InMemorySessionStore()
        assert store.is_valid("never-registered") is False

    def test_remove_session(self):
        store = InMemorySessionStore()
        store.register("sid-1", ttl=60)
        store.remove("sid-1")
        assert store.is_valid("sid-1") is False

    def test_remove_unknown_is_noop(self):
        store = InMemorySessionStore()
        store.remove("nope")  # should not raise

    def test_expired_session_is_invalid(self):
        store = InMemorySessionStore()
        store.register("sid-1", ttl=0)
        time.sleep(0.01)
        assert store.is_valid("sid-1") is False

    def test_expired_session_is_pruned_on_register(self):
        store = InMemorySessionStore()
        store.register("old", ttl=0)
        time.sleep(0.01)
        store.register("new", ttl=60)
        # The expired one should have been pruned from internal storage
        assert "old" not in store._data
        assert store.is_valid("new") is True


# ---------------------------------------------------------------------------
# RedisSessionStore (fakeredis)
# ---------------------------------------------------------------------------


class TestRedisSessionStore:
    def _client(self):
        import fakeredis

        return fakeredis.FakeStrictRedis(decode_responses=True)

    def test_register_and_validate(self):
        store = RedisSessionStore(self._client(), prefix="accelmcp:session:mcp:")
        store.register("sid-1", ttl=60)
        assert store.is_valid("sid-1") is True

    def test_unknown_session_is_invalid(self):
        store = RedisSessionStore(self._client(), prefix="p:")
        assert store.is_valid("nope") is False

    def test_remove_session(self):
        store = RedisSessionStore(self._client(), prefix="p:")
        store.register("sid-1", ttl=60)
        store.remove("sid-1")
        assert store.is_valid("sid-1") is False

    def test_key_is_namespaced(self):
        client = self._client()
        store = RedisSessionStore(client, prefix="accelmcp:session:admin:")
        store.register("sid-9", ttl=60)
        # The raw key must carry the namespace prefix
        assert client.exists("accelmcp:session:admin:sid-9") == 1
        assert client.exists("sid-9") == 0

    def test_ttl_is_applied(self):
        client = self._client()
        store = RedisSessionStore(client, prefix="p:")
        store.register("sid-1", ttl=123)
        ttl = client.ttl("p:sid-1")
        assert 0 < ttl <= 123

    def test_two_namespaces_do_not_collide(self):
        client = self._client()
        mcp = RedisSessionStore(client, prefix="accelmcp:session:mcp:")
        admin = RedisSessionStore(client, prefix="accelmcp:session:admin:")
        mcp.register("shared-id", ttl=60)
        # Same id in the admin namespace is independent
        assert mcp.is_valid("shared-id") is True
        assert admin.is_valid("shared-id") is False


# ---------------------------------------------------------------------------
# get_session_store() backend selection
# ---------------------------------------------------------------------------


class TestGetSessionStore:
    def test_defaults_to_in_memory_without_redis_url(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        reset_session_stores()
        store = get_session_store("mcp")
        assert isinstance(store, InMemorySessionStore)

    def test_uses_redis_when_redis_url_set(self, monkeypatch):
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        reset_session_stores()

        import fakeredis

        # Patch redis.from_url so we don't need a real server
        def _fake_from_url(url, **kwargs):
            return fakeredis.FakeStrictRedis(decode_responses=True)

        import redis

        monkeypatch.setattr(redis, "from_url", _fake_from_url)

        store = get_session_store("mcp")
        assert isinstance(store, RedisSessionStore)

    def test_same_namespace_returns_cached_instance(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        reset_session_stores()
        a = get_session_store("mcp")
        b = get_session_store("mcp")
        assert a is b

    def test_different_namespaces_are_separate_instances(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        reset_session_stores()
        mcp = get_session_store("mcp")
        admin = get_session_store("admin")
        assert mcp is not admin

        # And they don't share session ids
        mcp.register("sid", ttl=60)
        assert mcp.is_valid("sid") is True
        assert admin.is_valid("sid") is False

    def test_reset_forces_backend_reselection(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        reset_session_stores()
        first = get_session_store("mcp")
        assert isinstance(first, InMemorySessionStore)

        # After reset + REDIS_URL set, a new store should be Redis-backed
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        reset_session_stores()

        import fakeredis
        import redis

        monkeypatch.setattr(redis, "from_url", lambda url, **kw: fakeredis.FakeStrictRedis(decode_responses=True))

        second = get_session_store("mcp")
        assert isinstance(second, RedisSessionStore)
        assert second is not first


# ---------------------------------------------------------------------------
# Integration with the MCP controller helpers (in-memory default)
# ---------------------------------------------------------------------------


class TestControllerHelpersUseStore:
    def test_mcp_controller_session_roundtrip(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        reset_session_stores()
        from app.controllers import mcp_controller

        mcp_controller._register_session("ctrl-sid")
        assert mcp_controller._is_valid_session("ctrl-sid") is True
        mcp_controller._remove_session("ctrl-sid")
        assert mcp_controller._is_valid_session("ctrl-sid") is False

    def test_admin_mcp_controller_session_roundtrip(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        reset_session_stores()
        from app.controllers import admin_mcp_controller

        admin_mcp_controller._register_session("admin-sid")
        assert admin_mcp_controller._is_valid_session("admin-sid") is True
        admin_mcp_controller._remove_session("admin-sid")
        assert admin_mcp_controller._is_valid_session("admin-sid") is False

    def test_mcp_and_admin_sessions_are_isolated(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        reset_session_stores()
        from app.controllers import admin_mcp_controller, mcp_controller

        mcp_controller._register_session("dup")
        # The same id is not valid on the admin namespace
        assert mcp_controller._is_valid_session("dup") is True
        assert admin_mcp_controller._is_valid_session("dup") is False

    def test_redis_outage_does_not_raise(self):
        from unittest.mock import MagicMock

        from redis.exceptions import ConnectionError as RedisConnectionError

        client = MagicMock()
        client.setex.side_effect = RedisConnectionError("down")
        client.exists.side_effect = RedisConnectionError("down")
        client.delete.side_effect = RedisConnectionError("down")
        store = RedisSessionStore(client, prefix="p:")

        store.register("sid-1", ttl=60)
        store.remove("sid-1")
        assert store.is_valid("sid-1") is True
