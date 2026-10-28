import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import numpy as np
import pytest

from app.cache import semantic_cache


def _create_cache(
    monkeypatch: pytest.MonkeyPatch,
    *,
    redis_enabled: bool = True,
) -> tuple[semantic_cache.SemanticCache, Mock, Mock, Mock]:
    monkeypatch.setattr(semantic_cache.SemanticCache, "_instance", None)
    monkeypatch.setattr(semantic_cache.SemanticCache, "_initialized", False)
    monkeypatch.setattr(semantic_cache.settings, "redis_enabled", redis_enabled)

    redis_index = Mock()
    redis_index.create_index = AsyncMock()
    redis_index.search = AsyncMock()

    redis_client = Mock()
    redis_client.ft = Mock(return_value=redis_index)
    redis_client.hset = AsyncMock()
    redis_client.expire = AsyncMock()

    embedding_api = Mock()
    embedding_api.create = AsyncMock(
        return_value=SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])],
        ),
    )
    openai_client = SimpleNamespace(embeddings=embedding_api)

    redis_factory = Mock(return_value=redis_client)
    openai_factory = Mock(return_value=openai_client)
    monkeypatch.setattr(semantic_cache.Redis, "from_url", redis_factory)
    monkeypatch.setattr(semantic_cache, "AsyncOpenAI", openai_factory)

    cache = semantic_cache.SemanticCache()
    return cache, redis_client, redis_index, embedding_api


@pytest.fixture
def cache_env(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[semantic_cache.SemanticCache, Mock, Mock, Mock]:
    return _create_cache(monkeypatch)


def test_semantic_cache_is_singleton(
    cache_env: tuple[semantic_cache.SemanticCache, Mock, Mock, Mock],
) -> None:
    cache, _, _, _ = cache_env

    assert semantic_cache.SemanticCache() is cache


def test_location_key_normalizes_city_name() -> None:
    assert semantic_cache.SemanticCache.location_key(" New Delhi, India ") == (
        "new_delhi_india"
    )


def test_create_embedding_uses_configured_model(
    cache_env: tuple[semantic_cache.SemanticCache, Mock, Mock, Mock],
) -> None:
    cache, _, _, embedding_api = cache_env

    vector = asyncio.run(cache.create_embedding("weather in Delhi"))

    assert vector.dtype == np.float32
    assert vector.tolist() == pytest.approx([0.1, 0.2, 0.3])
    embedding_api.create.assert_awaited_once_with(
        model=semantic_cache.EMBEDDING_MODEL,
        input="weather in Delhi",
    )


def test_initialize_creates_redis_vector_index(
    cache_env: tuple[semantic_cache.SemanticCache, Mock, Mock, Mock],
) -> None:
    cache, redis_client, redis_index, _ = cache_env

    asyncio.run(cache.initialize_semantic_cache())

    redis_client.ft.assert_called_once_with(semantic_cache.INDEX_NAME)
    redis_index.create_index.assert_awaited_once()
    schema = redis_index.create_index.await_args.args[0]
    assert len(schema) == 7


def test_get_returns_matching_cached_response(
    cache_env: tuple[semantic_cache.SemanticCache, Mock, Mock, Mock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache, _, redis_index, _ = cache_env
    monkeypatch.setattr(
        cache,
        "create_embedding",
        AsyncMock(return_value=np.array([0.1, 0.2], dtype=np.float32)),
    )
    redis_index.search.return_value = SimpleNamespace(
        docs=[SimpleNamespace(distance="0.05", response=b"Sunny in Delhi")],
    )

    result = asyncio.run(
        cache.get_semantic_cache(
            "Will it be sunny?",
            intent="current_weather",
            location="Delhi",
        )
    )

    assert result == "Sunny in Delhi"
    redis_index.search.assert_awaited_once()


@pytest.mark.parametrize(
    "docs",
    [
        [],
        [SimpleNamespace(distance="0.2", response=b"Not similar enough")],
    ],
)
def test_get_returns_none_when_no_safe_match(
    cache_env: tuple[semantic_cache.SemanticCache, Mock, Mock, Mock],
    monkeypatch: pytest.MonkeyPatch,
    docs: list[SimpleNamespace],
) -> None:
    cache, _, redis_index, _ = cache_env
    monkeypatch.setattr(
        cache,
        "create_embedding",
        AsyncMock(return_value=np.array([0.1, 0.2], dtype=np.float32)),
    )
    redis_index.search.return_value = SimpleNamespace(docs=docs)

    result = asyncio.run(
        cache.get_semantic_cache(
            "Will it be sunny?",
            intent="current_weather",
            location="Delhi",
        )
    )

    assert result is None


def test_set_stores_cache_entry_and_ttl(
    cache_env: tuple[semantic_cache.SemanticCache, Mock, Mock, Mock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache, redis_client, _, _ = cache_env
    monkeypatch.setattr(
        cache,
        "create_embedding",
        AsyncMock(return_value=np.array([0.1, 0.2], dtype=np.float32)),
    )

    asyncio.run(
        cache.set_semantic_cache(
            "Will it be sunny?",
            "Sunny in Delhi",
            intent="current_weather",
            location="New Delhi",
            scope="current",
            ttl=45,
        )
    )

    key = redis_client.hset.await_args.args[0]
    mapping = redis_client.hset.await_args.kwargs["mapping"]
    assert key.startswith(semantic_cache.PREFIX)
    assert mapping["query"] == b"Will it be sunny?"
    assert mapping["response"] == b"Sunny in Delhi"
    assert mapping["intent"] == "current_weather"
    assert mapping["location_key"] == "new_delhi"
    assert mapping["scope"] == "current"
    assert mapping["embedding"] == np.array([0.1, 0.2], dtype=np.float32).tobytes()
    redis_client.expire.assert_awaited_once_with(key, 45)


def test_cache_methods_are_noops_when_redis_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache, redis_client, redis_index, embedding_api = _create_cache(
        monkeypatch,
        redis_enabled=False,
    )

    async def exercise_disabled_cache() -> None:
        await cache.initialize_semantic_cache()
        assert await cache.get_semantic_cache(
            "Weather in Delhi",
            intent="current_weather",
            location="Delhi",
        ) is None
        await cache.set_semantic_cache(
            "Weather in Delhi",
            "Sunny",
            intent="current_weather",
            location="Delhi",
        )

    asyncio.run(exercise_disabled_cache())

    assert cache.redis is None
    redis_client.ft.assert_not_called()
    redis_client.hset.assert_not_awaited()
    redis_index.create_index.assert_not_awaited()
    embedding_api.create.assert_not_awaited()
