import asyncio
import importlib
import sys
from collections.abc import Iterator
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest

with patch("openai.AsyncOpenAI"):
    from app.cache import semantic_cache


@pytest.fixture
def weather_agent_service_class(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[type]:
    service_module_name = "app.services.weather_agent_service"
    existing_service_module = sys.modules.pop(service_module_name, None)
    services_package = sys.modules.get("app.services")
    existing_service_attribute = getattr(
        services_package,
        "weather_agent_service",
        None,
    )

    settings_module = ModuleType("app.config")
    settings_module.settings = SimpleNamespace(
        weather_api_url="https://example.test",
        weather_timeout_seconds=1,
    )

    redis_cache_module = ModuleType("app.cache.redis_cache")
    redis_cache_module.AsyncRedisCache = type("AsyncRedisCache", (), {})

    crew_module = ModuleType("app.orchestrator.crewai.crew")
    crew_module.CrewAIOrchestrator = type("CrewAIOrchestrator", (), {})

    langgraph_module = ModuleType("app.orchestrator.langgraph.orchestrator")
    langgraph_module.LangGraphOrchestrator = type("LangGraphOrchestrator", (), {})

    guardrails_module = ModuleType("app.guardrails.input_guardrails")
    guardrails_module.MAX_QUERY_LENGTH = 100
    guardrails_module.GuardrailViolation = ValueError
    guardrails_module.validate_query = lambda query: query.strip()

    for name, module in (
        ("app.config", settings_module),
        ("app.cache.redis_cache", redis_cache_module),
        ("app.orchestrator.crewai.crew", crew_module),
        ("app.orchestrator.langgraph.orchestrator", langgraph_module),
        ("app.guardrails.input_guardrails", guardrails_module),
    ):
        monkeypatch.setitem(sys.modules, name, module)

    service_module = importlib.import_module(service_module_name)
    yield service_module.WeatherAgentService

    sys.modules.pop(service_module_name, None)
    if existing_service_module is not None:
        sys.modules[service_module_name] = existing_service_module
    if services_package is not None:
        if existing_service_attribute is None:
            services_package.__dict__.pop("weather_agent_service", None)
        else:
            services_package.weather_agent_service = existing_service_attribute


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


def test_semantic_hitl_returns_cached_weather_without_running_orchestrator(
    monkeypatch: pytest.MonkeyPatch,
    weather_agent_service_class,
) -> None:
    async def run_test() -> None:
        service = weather_agent_service_class()
        cached_response = "Delhi is 29°C and partly cloudy."
        initialize_cache = AsyncMock()
        get_cache = AsyncMock(return_value=cached_response)
        set_user_hitl = AsyncMock()
        run_orchestrator = AsyncMock()
        monkeypatch.setattr(semantic_cache, "get_semantic_cache", get_cache)
        monkeypatch.setattr(semantic_cache, "set_semantic_cache", AsyncMock())
        monkeypatch.setattr(
            semantic_cache,
            "initialize_semantic_cache",
            initialize_cache,
        )
        monkeypatch.setattr(
            service.crewai_orchestrator,
            "get_resolved_city",
            AsyncMock(return_value="Delhi"),
            raising=False,
        )
        monkeypatch.setattr(
            service.crewai_orchestrator,
            "set_user_hitl",
            set_user_hitl,
            raising=False,
        )
        monkeypatch.setattr(
            service.crewai_orchestrator,
            "run_weather_orchestrator_hitl",
            run_orchestrator,
            raising=False,
        )

        result = await service.process_weather_hitl_semantic(
            "What is the weather like in Delhi right now?",
            session_id="session123",
            user_id="user123",
        )

        assert result.status == "success"
        assert result.message == cached_response
        assert result.isCached is True
        assert result.cacheKey is None
        get_cache.assert_awaited_once_with(
            "What is the weather like in Delhi right now?",
            intent="current_weather",
            location="Delhi",
            scope="current",
        )
        initialize_cache.assert_awaited_once()
        set_user_hitl.assert_awaited_once_with(
            "What is the weather like in Delhi right now?",
            cached_response,
            "session123",
            "user123",
        )
        run_orchestrator.assert_not_awaited()

    asyncio.run(run_test())


def test_semantic_hitl_stores_successful_weather_response(
    monkeypatch: pytest.MonkeyPatch,
    weather_agent_service_class,
) -> None:
    async def run_test() -> None:
        service = weather_agent_service_class()
        get_cache = AsyncMock(return_value=None)
        initialize_cache = AsyncMock()
        set_cache = AsyncMock()
        get_city = AsyncMock(side_effect=["Delhi", "Delhi"])
        run_orchestrator = AsyncMock(
            return_value=("Delhi: 29°C and sunny.", "weather:key", False)
        )
        monkeypatch.setattr(semantic_cache, "get_semantic_cache", get_cache)
        monkeypatch.setattr(semantic_cache, "set_semantic_cache", set_cache)
        monkeypatch.setattr(
            semantic_cache,
            "initialize_semantic_cache",
            initialize_cache,
        )
        monkeypatch.setattr(
            service.crewai_orchestrator,
            "get_resolved_city",
            get_city,
            raising=False,
        )
        monkeypatch.setattr(
            service.crewai_orchestrator,
            "run_weather_orchestrator_hitl",
            run_orchestrator,
            raising=False,
        )

        result = await service.process_weather_hitl_semantic(
            "Give me the weather in Delhi",
            session_id="session123",
            user_id="user123",
        )

        assert result.message == "Delhi: 29°C and sunny."
        assert result.isCached is False
        get_cache.assert_awaited_once()
        initialize_cache.assert_awaited_once()
        set_cache.assert_awaited_once_with(
            "Give me the weather in Delhi",
            "Delhi: 29°C and sunny.",
            intent="current_weather",
            location="Delhi",
            scope="current",
        )
        run_orchestrator.assert_awaited_once_with(
            "Give me the weather in Delhi",
            session_id="session123",
            user_id="user123",
        )

    asyncio.run(run_test())


def test_semantic_hitl_does_not_reuse_cache_for_a_different_city(
    monkeypatch: pytest.MonkeyPatch,
    weather_agent_service_class,
) -> None:
    async def run_test() -> None:
        service = weather_agent_service_class()
        get_cache = AsyncMock()
        set_cache = AsyncMock()
        initialize_cache = AsyncMock()
        get_city = AsyncMock(side_effect=["Delhi", "Mumbai"])
        run_orchestrator = AsyncMock(
            return_value=("Mumbai: 28°C and rainy.", "weather:key", False)
        )
        monkeypatch.setattr(semantic_cache, "get_semantic_cache", get_cache)
        monkeypatch.setattr(semantic_cache, "set_semantic_cache", set_cache)
        monkeypatch.setattr(
            semantic_cache,
            "initialize_semantic_cache",
            initialize_cache,
        )
        monkeypatch.setattr(
            service.crewai_orchestrator,
            "get_resolved_city",
            get_city,
            raising=False,
        )
        monkeypatch.setattr(
            service.crewai_orchestrator,
            "run_weather_orchestrator_hitl",
            run_orchestrator,
            raising=False,
        )

        result = await service.process_weather_hitl_semantic(
            "What is the weather in Mumbai?",
            session_id="session123",
            user_id="user123",
        )

        assert result.message == "Mumbai: 28°C and rainy."
        get_cache.assert_not_awaited()
        initialize_cache.assert_awaited_once()
        set_cache.assert_awaited_once_with(
            "What is the weather in Mumbai?",
            "Mumbai: 28°C and rainy.",
            intent="current_weather",
            location="Mumbai",
            scope="current",
        )

    asyncio.run(run_test())


def test_semantic_hitl_does_not_cache_pending_approval(
    monkeypatch: pytest.MonkeyPatch,
    weather_agent_service_class,
) -> None:
    async def run_test() -> None:
        service = weather_agent_service_class()
        create_pending = AsyncMock(return_value={"approval_id": "approval123"})
        get_cache = AsyncMock()
        set_cache = AsyncMock()
        monkeypatch.setattr(semantic_cache, "get_semantic_cache", get_cache)
        monkeypatch.setattr(semantic_cache, "set_semantic_cache", set_cache)
        monkeypatch.setattr(
            service.crewai_orchestrator,
            "get_resolved_city",
            AsyncMock(return_value="Delhi"),
            raising=False,
        )
        monkeypatch.setattr(
            service.crewai_orchestrator,
            "create_pending",
            create_pending,
            raising=False,
        )

        result = await service.process_weather_hitl_semantic(
            "Broadcast a weather alert to all users",
            session_id="session123",
            user_id="user123",
        )

        assert result.status == "pending_approval"
        assert result.isCached is False
        get_cache.assert_not_awaited()
        set_cache.assert_not_awaited()
        create_pending.assert_awaited_once()

    asyncio.run(run_test())
