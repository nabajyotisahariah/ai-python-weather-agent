# python tests/test_semantic_cache.py 

import numpy as np
import pytest
from redis.exceptions import RedisError

from app.cache.semantic_cache import SemanticCache


import pytest_asyncio

from app.cache.redis_cache import AsyncRedisCache

@pytest_asyncio.fixture
async def semantic_cache():
    SemanticCache._instance = None
    SemanticCache._initialized = False
    AsyncRedisCache._instance = None
    AsyncRedisCache._initialized = False
    
    cache = SemanticCache()

    if cache.redis is None:
        pytest.skip("Redis is disabled")

    try:
        await cache.redis.ping()
        await cache.initialize_semantic_cache()
    except (RedisError, OSError) as exc:
        pytest.skip(f"Redis Stack is unavailable: {exc}")

    # Use a deterministic embedding to avoid OpenAI API calls.
    vector = np.zeros(cache.VECTOR_DIMENSIONS, dtype=np.float32)
    vector[0] = 1.0

    async def fake_embedding(text: str) -> np.ndarray:
        return vector.copy()

    cache.create_embedding = fake_embedding

    yield cache

    # Clean up only keys created by this test.
    keys = await cache.redis.keys(f"{cache.PREFIX}*")
    if keys:
        await cache.redis.delete(*keys)


@pytest.mark.asyncio
async def test_semantic_cache_store_and_retrieve(semantic_cache):
    cache = semantic_cache

    query = "What is the weather in Noida today?"
    response = (
        "Current weather in Noida: 33°C, dusty conditions."
    )

    # Store the response.
    await cache.set_semantic_cache(
        query,
        response,
        intent="weather",
        location="Noida",
        units="metric",
        scope="current",
        ttl=120,
    )

    # Retrieve using a similar query.
    cached_response = await cache.get_semantic_cache(
        "Tell me today's weather in Noida",
        intent="weather",
        location="Noida",
        units="metric",
        scope="current",
    )

    assert cached_response == response


@pytest.mark.asyncio
async def test_semantic_cache_does_not_cross_locations(
    semantic_cache,
):
    cache = semantic_cache

    response = "Current weather in Noida: 33°C."

    await cache.set_semantic_cache(
        "What is the weather today?",
        response,
        intent="weather",
        location="Noida",
        units="metric",
        scope="current",
        ttl=120,
    )

    # The same embedding must not cause a cross-location hit.
    cached_response = await cache.get_semantic_cache(
        "What is the weather today?",
        intent="weather",
        location="Delhi",
        units="metric",
        scope="current",
    )

    assert cached_response is None


@pytest.mark.asyncio
async def test_semantic_cache_entry_expires(semantic_cache):
    cache = semantic_cache

    await cache.set_semantic_cache(
        "Weather in Noida",
        "Sunny, 30°C",
        intent="weather",
        location="Noida",
        units="metric",
        scope="current",
        ttl=1,
    )

    # Verify the TTL is applied to the stored Redis hash.
    keys = await cache.redis.keys(f"{cache.PREFIX}*")
    assert keys

    ttl = await cache.redis.ttl(keys[0])
    assert 0 <= ttl <= 1

if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
