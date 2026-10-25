# app/cache/semantic_cache.py
#pip install "redis>=5" openai numpy

import json
import os
import re

import numpy as np
from openai import AsyncOpenAI
from redis.asyncio import Redis
from redis.commands.search.field import TagField, TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
INDEX_NAME = "idx:weather_semantic"
PREFIX = "weather:semantic:"
EMBEDDING_MODEL = "text-embedding-3-small"
VECTOR_DIMENSIONS = 1536

CACHE_TTL_SECONDS = 120
SIMILARITY_THRESHOLD = 0.92

redis_client = Redis.from_url(
    REDIS_URL,
    decode_responses=False,
)

openai_client = AsyncOpenAI()


def location_key(location: str) -> str:
    """Convert a location into a stable, searchable identifier."""
    return re.sub(r"[^a-z0-9]+", "_", location.lower()).strip("_")


async def create_embedding(text: str) -> np.ndarray:
    result = await openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return np.asarray(
        result.data[0].embedding,
        dtype=np.float32,
    )


async def initialize_semantic_cache() -> None:
    """Create the Redis vector index once during application startup."""
    schema = [
        TagField("intent"),
        TagField("location_key"),
        TagField("units"),
        TagField("scope"),
        TextField("query"),
        TextField("response"),
        VectorField(
            "embedding",
            "FLAT",
            {
                "TYPE": "FLOAT32",
                "DIM": VECTOR_DIMENSIONS,
                "DISTANCE_METRIC": "COSINE",
            },
        ),
    ]

    try:
        await redis_client.ft(INDEX_NAME).create_index(
            schema,
            definition=IndexDefinition(
                prefix=[PREFIX],
                index_type=IndexType.HASH,
            ),
        )
    except Exception as exc:
        # Do not hide arbitrary connection or configuration errors.
        from redis.exceptions import ResponseError

        if not isinstance(exc, ResponseError) or "exist" not in str(exc).lower():
            raise


async def get_semantic_cache(
    query_text: str,
    *,
    intent: str,
    location: str,
    units: str = "metric",
    scope: str = "current",
) -> str | None:
    """Return a semantically similar cached response, if safe to reuse."""
    vector = await create_embedding(query_text)

    query = (
        Query(
            f"(@intent:{{{intent}}} "
            f"@location_key:{{{location_key(location)}}} "
            f"@units:{{{units}}} "
            f"@scope:{{{scope}}})"
            "=>[KNN 5 @embedding $vec AS distance]"
        )
        .sort_by("distance")
        .return_fields("response", "distance")
        .paging(0, 5)
        .dialect(2)
    )

    results = await redis_client.ft(INDEX_NAME).search(
        query,
        query_params={"vec": vector.tobytes()},
    )

    if not results.docs:
        return None

    best = results.docs[0]
    distance = float(best.distance)
    similarity = 1.0 - distance

    if similarity < SIMILARITY_THRESHOLD:
        return None

    return best.response.decode("utf-8")


async def set_semantic_cache(
    query_text: str,
    response: str,
    *,
    intent: str,
    location: str,
    units: str = "metric",
    scope: str = "current",
    ttl: int = CACHE_TTL_SECONDS,
) -> None:
    """Store a successful response and its embedding."""
    vector = await create_embedding(query_text)

    # Each write gets its own key; similar queries can coexist.
    key = f"{PREFIX}{__import__('uuid').uuid4().hex}"

    await redis_client.hset(
        key,
        mapping={
            "query": query_text.encode("utf-8"),
            "response": response.encode("utf-8"),
            "intent": intent,
            "location_key": location_key(location),
            "units": units,
            "scope": scope,
            "embedding": vector.tobytes(),
        },
    )
    await redis_client.expire(key, ttl)