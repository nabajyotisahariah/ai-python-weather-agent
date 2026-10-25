import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest

with patch("openai.AsyncOpenAI"):
    from app.cache import semantic_cache


def test_initialize_semantic_cache_creates_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index = SimpleNamespace(create_index=AsyncMock())
    redis_client = SimpleNamespace(ft=Mock(return_value=index))
    monkeypatch.setattr(semantic_cache, "redis_client", redis_client)

    asyncio.run(semantic_cache.initialize_semantic_cache())

    redis_client.ft.assert_called_once_with(semantic_cache.INDEX_NAME)
    index.create_index.assert_awaited_once()


def test_set_semantic_cache_stores_response_and_expiration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vector = np.zeros(semantic_cache.VECTOR_DIMENSIONS, dtype=np.float32)
    create_embedding = AsyncMock(return_value=vector)
    redis_client = SimpleNamespace(
        hset=AsyncMock(),
        expire=AsyncMock(),
    )
    monkeypatch.setattr(semantic_cache, "create_embedding", create_embedding)
    monkeypatch.setattr(semantic_cache, "redis_client", redis_client)

    asyncio.run(
        semantic_cache.set_semantic_cache(
            "Weather in Delhi?",
            "29°C, partly cloudy.",
            intent="current_weather",
            location="Delhi",
            ttl=45,
        )
    )

    key, = redis_client.hset.await_args.args
    mapping = redis_client.hset.await_args.kwargs["mapping"]
    assert key.startswith(semantic_cache.PREFIX)
    assert mapping == {
        "query": b"Weather in Delhi?",
        "response": "29°C, partly cloudy.".encode("utf-8"),
        "intent": "current_weather",
        "location_key": "delhi",
        "units": "metric",
        "scope": "current",
        "embedding": vector.tobytes(),
    }
    redis_client.expire.assert_awaited_once_with(key, 45)
    create_embedding.assert_awaited_once_with("Weather in Delhi?")


@pytest.mark.parametrize(
    ("distance", "expected"),
    [(0.05, "29°C, partly cloudy."), (0.1, None)],
)
def test_get_semantic_cache_applies_similarity_threshold(
    monkeypatch: pytest.MonkeyPatch,
    distance: float,
    expected: str | None,
) -> None:
    vector = np.zeros(semantic_cache.VECTOR_DIMENSIONS, dtype=np.float32)
    create_embedding = AsyncMock(return_value=vector)
    index = SimpleNamespace(
        search=AsyncMock(
            return_value=SimpleNamespace(
                docs=[
                    SimpleNamespace(
                        distance=str(distance),
                        response="29°C, partly cloudy.".encode("utf-8"),
                    )
                ]
            )
        )
    )
    redis_client = SimpleNamespace(ft=Mock(return_value=index))
    monkeypatch.setattr(semantic_cache, "create_embedding", create_embedding)
    monkeypatch.setattr(semantic_cache, "redis_client", redis_client)

    result = asyncio.run(
        semantic_cache.get_semantic_cache(
            "Current weather in Delhi?",
            intent="current_weather",
            location="Delhi",
        )
    )

    assert result == expected
    redis_client.ft.assert_called_once_with(semantic_cache.INDEX_NAME)
    index.search.assert_awaited_once()
    assert index.search.await_args.kwargs["query_params"] == {
        "vec": vector.tobytes()
    }
