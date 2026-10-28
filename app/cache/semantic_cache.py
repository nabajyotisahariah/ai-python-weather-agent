import re
import uuid

import numpy as np
from openai import AsyncOpenAI
from redis.asyncio import Redis
from redis.commands.search.field import TagField, TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from app.config import settings

INDEX_NAME = "idx:weather_semantic"
PREFIX = "weather:semantic:"
EMBEDDING_MODEL = "text-embedding-3-small"
VECTOR_DIMENSIONS = 1536

CACHE_TTL_SECONDS = 120
SIMILARITY_THRESHOLD = 0.92


class SemanticCache:
    _instance: "SemanticCache | None" = None
    _initialized = False

    def __new__(cls) -> "SemanticCache":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self.redis: Redis | None = (
            Redis.from_url(settings.redis_url, decode_responses=False)
            if settings.redis_enabled
            else None
        )
        self.openai_client = AsyncOpenAI()
        self._initialized = True

    @staticmethod
    def location_key(location: str) -> str:
        """Convert a location into a stable, searchable identifier."""
        return re.sub(r"[^a-z0-9]+", "_", location.lower()).strip("_")

    async def create_embedding(self, text: str) -> np.ndarray:
        result = await self.openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
        )
        return np.asarray(
            result.data[0].embedding,
            dtype=np.float32,
        )

    async def initialize_semantic_cache(self) -> None:
        """Create the Redis vector index once during application startup."""
        if self.redis is None:
            return

        print("Initializing semantic cache index...", index_name=INDEX_NAME, prefix=PREFIX)

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
            await self.redis.ft(INDEX_NAME).create_index(
                schema,
                definition=IndexDefinition(
                    prefix=[PREFIX],
                    index_type=IndexType.HASH,
                ),
            )
        except Exception as exc:
            from redis.exceptions import ResponseError

            if not isinstance(exc, ResponseError) or "exist" not in str(exc).lower():
                raise

    async def get_semantic_cache(
        self,
        query_text: str,
        *,
        intent: str,
        location: str,
        units: str = "metric",
        scope: str = "current",
    ) -> str | None:
        """Return a semantically similar cached response, if safe to reuse."""
        if self.redis is None:
            return None

        vector = await self.create_embedding(query_text)
        print(f"Searching semantic cache for query: '{query_text}' with intent: '{intent}', location: '{location}', units: '{units}', scope: '{scope}'")

        query = (
            Query(
                f"(@intent:{{{intent}}} "
                f"@location_key:{{{self.location_key(location)}}} "
                f"@units:{{{units}}} "
                f"@scope:{{{scope}}})"
                "=>[KNN 5 @embedding $vec AS distance]"
            )
            .sort_by("distance")
            .return_fields("response", "distance")
            .paging(0, 5)
            .dialect(2)
        )

        results = await self.redis.ft(INDEX_NAME).search(
            query,
            query_params={"vec": vector.tobytes()},
        )

        if not results.docs:
            return None

        best = results.docs[0]
        distance = float(best.distance)
        similarity = 1.0 - distance

        print(f"Best match distance {distance:.4f}, similarity: {similarity:.4f} for query: '{query_text}'")
        if similarity < SIMILARITY_THRESHOLD:
            return None
        print(f"Returning cached response for query: '{query_text}'")
        return best.response.decode("utf-8")

    async def set_semantic_cache(
        self,
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
        if self.redis is None:
            return

        vector = await self.create_embedding(query_text)
        key = f"{PREFIX}{uuid.uuid4().hex}"

        await self.redis.hset(
            key,
            mapping={
                "query": query_text.encode("utf-8"),
                "response": response.encode("utf-8"),
                "intent": intent,
                "location_key": self.location_key(location),
                "units": units,
                "scope": scope,
                "embedding": vector.tobytes(),
            },
        )
        await self.redis.expire(key, ttl)