# pip install pytest_asyncio
# python -m pytest tests/test_semantic_cache.py -v -s

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
        print(f"Cleaning up {len(keys)} keys from Redis...")
        #await cache.redis.delete(*keys)


@pytest.mark.asyncio
async def test_semantic_cache_store_and_retrieve(semantic_cache):
    print("Running test_semantic_cache_store_and_retrieve...")
    # cache = semantic_cache

    # query = "What is the weather in Noida today?"
    # response = (
    #     "Current weather in Noida: 33°C, dusty conditions."
    # )

    # # Store the response.
    # await cache.set_semantic_cache(
    #     query,
    #     response,
    #     intent="weather",
    #     location="Noida",
    #     units="metric",
    #     scope="current",
    #     ttl=120,
    # )

    # # Retrieve using a similar query.
    # cached_response = await cache.get_semantic_cache(
    #     "Tell me today's weather in Noida",
    #     intent="weather",
    #     location="Noida",
    #     units="metric",
    #     scope="current",
    # )

    # assert cached_response == response


@pytest.mark.asyncio
async def test_semantic_cache_does_not_cross_locations(
    semantic_cache,
):
    print("Running test_semantic_cache_does_not_cross_locations...")
    # cache = semantic_cache

    # response = "Current weather in Noida: 33°C."

    # await cache.set_semantic_cache(
    #     "What is the weather today?",
    #     response,
    #     intent="weather",
    #     location="Noida",
    #     units="metric",
    #     scope="current",
    #     ttl=120,
    # )

    # # The same embedding must not cause a cross-location hit.
    # cached_response = await cache.get_semantic_cache(
    #     "What is the weather today?",
    #     intent="weather",
    #     location="Delhi",
    #     units="metric",
    #     scope="current",
    # )

    # assert cached_response is None


@pytest.mark.asyncio
async def test_semantic_cache_entry_expires(semantic_cache):
    print("Running test_semantic_cache_entry_expires...")
    # cache = semantic_cache

    # await cache.set_semantic_cache(
    #     "Weather in Noida",
    #     "Sunny, 30°C",
    #     intent="weather",
    #     location="Noida",
    #     units="metric",
    #     scope="current",
    #     ttl=1,
    # )

    # # Verify the TTL is applied to the stored Redis hash.
    # keys = await cache.redis.keys(f"{cache.PREFIX}*")
    # assert keys

    # ttl = await cache.redis.ttl(keys[0])
    # assert 0 <= ttl <= 1


@pytest.mark.asyncio
async def test_semantic_cache_multiple_use_cases(semantic_cache):
    cache = semantic_cache
    records = [
        ("Current weather in Noida", "Noida: sunny, 33°C", "weather", "Noida", "metric", "current"),
        ("Current weather in Delhi", "Delhi: cloudy, 28°C", "weather", "Delhi", "metric", "current"),
        ("Noida weather forecast", "Noida forecast: rain tomorrow", "weather", "Noida", "metric", "forecast"),
        ("London weather forecast", "London forecast: windy tomorrow", "weather", "London", "imperial", "forecast"),
        ("Delhi air quality", "Delhi AQI: 154", "air_quality", "Delhi", "metric", "current"),
        ("Mumbai air quality", "Mumbai AQI: 82", "air_quality", "Mumbai", "metric", "current"),
        ("Tokyo current weather", "Tokyo: clear, 68°F", "weather", "Tokyo", "imperial", "current"),
        ("Sydney weather forecast", "Sydney forecast: sunny tomorrow", "weather", "Sydney", "imperial", "forecast"),
        ("Paris current weather", "Paris: light rain, 19°C", "weather", "Paris", "metric", "current"),
        ("New York weather forecast", "New York forecast: snow tomorrow", "weather", "New York", "imperial", "forecast"),
        ("Current weather in Toronto", "Toronto: partly cloudy, 21°C", "weather", "Toronto", "metric", "current"),
        ("Toronto weather forecast", "Toronto forecast: showers tomorrow", "weather", "Toronto", "metric", "forecast"),
        ("Toronto air quality", "Toronto AQI: 42", "air_quality", "Toronto", "metric", "current"),
        ("Current weather in Berlin", "Berlin: sunny, 72°F", "weather", "Berlin", "imperial", "current"),
        ("Berlin weather forecast", "Berlin forecast: cloudy tomorrow", "weather", "Berlin", "imperial", "forecast"),
        ("Berlin air quality", "Berlin AQI: 36", "air_quality", "Berlin", "metric", "current"),
        ("Current weather in Singapore", "Singapore: humid, 31°C", "weather", "Singapore", "metric", "current"),
        ("Singapore weather forecast", "Singapore forecast: thunderstorms tomorrow", "weather", "Singapore", "metric", "forecast"),
        ("Singapore air quality", "Singapore PSI: 48", "air_quality", "Singapore", "metric", "current"),
        ("Current weather in Madrid", "Madrid: clear, 77°F", "weather", "Madrid", "imperial", "current"),
        ("Madrid weather forecast", "Madrid forecast: sunny tomorrow", "weather", "Madrid", "imperial", "forecast"),
        ("Madrid air quality", "Madrid AQI: 29", "air_quality", "Madrid", "metric", "current"),
        ("Current weather in Rome", "Rome: light rain, 18°C", "weather", "Rome", "metric", "current"),
        ("Rome weather forecast", "Rome forecast: partly sunny tomorrow", "weather", "Rome", "metric", "forecast"),
        ("Rome air quality", "Rome AQI: 51", "air_quality", "Rome", "metric", "current"),
        ("Current weather in Amsterdam", "Amsterdam: breezy, 64°F", "weather", "Amsterdam", "imperial", "current"),
        ("Amsterdam weather forecast", "Amsterdam forecast: rain tomorrow", "weather", "Amsterdam", "imperial", "forecast"),
        ("Amsterdam air quality", "Amsterdam AQI: 31", "air_quality", "Amsterdam", "metric", "current"),
        ("Current weather in Seoul", "Seoul: clear, 24°C", "weather", "Seoul", "metric", "current"),
        ("Seoul weather forecast", "Seoul forecast: cloudy tomorrow", "weather", "Seoul", "metric", "forecast"),
        ("Seoul air quality", "Seoul AQI: 67", "air_quality", "Seoul", "metric", "current"),
        ("Current weather in Bangkok", "Bangkok: hot, 89°F", "weather", "Bangkok", "imperial", "current"),
        ("Bangkok weather forecast", "Bangkok forecast: showers tomorrow", "weather", "Bangkok", "imperial", "forecast"),
        ("Bangkok air quality", "Bangkok AQI: 73", "air_quality", "Bangkok", "metric", "current"),
        ("Current weather in Cairo", "Cairo: sunny, 35°C", "weather", "Cairo", "metric", "current"),
        ("Cairo weather forecast", "Cairo forecast: clear tomorrow", "weather", "Cairo", "metric", "forecast"),
        ("Cairo air quality", "Cairo AQI: 91", "air_quality", "Cairo", "metric", "current"),
        ("Current weather in Istanbul", "Istanbul: overcast, 66°F", "weather", "Istanbul", "imperial", "current"),
        ("Istanbul weather forecast", "Istanbul forecast: showers tomorrow", "weather", "Istanbul", "imperial", "forecast"),
        ("Istanbul air quality", "Istanbul AQI: 58", "air_quality", "Istanbul", "metric", "current"),
        ("Current weather in Vancouver", "Vancouver: cloudy, 16°C", "weather", "Vancouver", "metric", "current"),
        ("Vancouver weather forecast", "Vancouver forecast: rain tomorrow", "weather", "Vancouver", "metric", "forecast"),
        ("Vancouver air quality", "Vancouver AQI: 24", "air_quality", "Vancouver", "metric", "current"),
        ("Current weather in Chicago", "Chicago: windy, 58°F", "weather", "Chicago", "imperial", "current"),
        ("Chicago weather forecast", "Chicago forecast: sunny tomorrow", "weather", "Chicago", "imperial", "forecast"),
        ("Chicago air quality", "Chicago AQI: 39", "air_quality", "Chicago", "metric", "current"),
        ("Current weather in Auckland", "Auckland: mild, 20°C", "weather", "Auckland", "metric", "current"),
        ("Auckland weather forecast", "Auckland forecast: cloudy tomorrow", "weather", "Auckland", "metric", "forecast"),
        ("Auckland air quality", "Auckland AQI: 18", "air_quality", "Auckland", "metric", "current"),
        ("Current weather in San Francisco", "San Francisco: foggy, 61°F", "weather", "San Francisco", "imperial", "current"),
        ("San Francisco weather forecast", "San Francisco forecast: fog tomorrow", "weather", "San Francisco", "imperial", "forecast"),
    ]

    for query, response, intent, location, units, scope in records:
        await cache.set_semantic_cache(
            query,
            response,
            intent=intent,
            location=location,
            units=units,
            scope=scope,
            ttl=120,
        )

    use_cases = [
        ("How is it in Noida now?", "weather", "Noida", "metric", "current", records[0][1]),
        ("Will it rain in Noida?", "weather", "Noida", "metric", "forecast", records[2][1]),
        ("What's the air quality in Delhi?", "air_quality", "Delhi", "metric", "current", records[4][1]),
        ("Give me the forecast for New York", "weather", "New York", "imperial", "forecast", records[9][1]),
        ("What's the weather like in Toronto?", "weather", "Toronto", "metric", "current", records[10][1]),
        ("Will Toronto have rain tomorrow?", "weather", "Toronto", "metric", "forecast", records[11][1]),
        ("How polluted is Berlin today?", "air_quality", "Berlin", "metric", "current", records[15][1]),
        ("Tell me today's weather in Madrid in Fahrenheit", "weather", "Madrid", "imperial", "current", records[19][1]),
        ("What's the air quality in Rome?", "air_quality", "Rome", "metric", "current", records[24][1]),
        ("Is Seoul's air quality okay?", "air_quality", "Seoul", "metric", "current", records[30][1]),
        ("Forecast Bangkok weather in Fahrenheit", "weather", "Bangkok", "imperial", "forecast", records[32][1]),
        ("What is Cairo's weather right now?", "weather", "Cairo", "metric", "current", records[34][1]),
        ("Check the air quality in Istanbul", "air_quality", "Istanbul", "metric", "current", records[39][1]),
        ("What's the forecast for Vancouver?", "weather", "Vancouver", "metric", "forecast", records[41][1]),
        ("Current conditions in Chicago, in Fahrenheit", "weather", "Chicago", "imperial", "current", records[43][1]),
        ("How is the air quality in Auckland?", "air_quality", "Auckland", "metric", "current", records[48][1]),
        ("Give me San Francisco's current weather in Fahrenheit", "weather", "San Francisco", "imperial", "current", records[49][1]),
         ("Give me Assam's current weather in Fahrenheit", "weather", "Assam", "imperial", "current", "Assam"),
    ]

    for query, intent, location, units, scope, expected_response in use_cases:
        cached_response = await cache.get_semantic_cache(
            query,
            intent=intent,
            location=location,
            units=units,
            scope=scope,
        )
        print(f"Query: '{query}' | Expected: '{expected_response}' | Cached: '{cached_response}'")
        assert cached_response == expected_response


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
