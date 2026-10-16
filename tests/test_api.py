import asyncio
from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.route.weather import get_weather_service
from app.route.weather_forecast import get_weather_forecast_service
from app.schema.weather import AgentResponse
from app.services.weather_service import (
    CityNotFoundError,
    WeatherProviderError,
    WeatherService,
)
from app.services.weather_agent_service import WeatherAgentService


class StubWeatherService:
    async def get_current_weather(self, city: str) -> dict[str, object]:
        return {
            "status": "success",
            "data": {
                "city": city,
                "temperature": 25,
                "feels_like": 26,
                "humidity": 60,
                "description": "Sunny",
                "wind_speed": 10,
            }
        }

    async def get_crewai_weather_report(self, city: str) -> dict[str, str]:
        return {"status": "success", "message": f"CrewAI report for {city}"}

    async def get_langgraph_weather_report(self, city: str) -> dict[str, str]:
        return {"status": "success", "message": f"LangGraph report for {city}"}

    async def get_autogen_weather_report(self, city: str) -> dict[str, str]:
        return {"status": "success", "message": f"AutoGen report for {city}"}

    async def get_google_adk_weather_report(self, city: str) -> dict[str, str]:
        return {"status": "success", "message": f"Google ADK report for {city}"}


class FailingWeatherService(StubWeatherService):
    async def get_current_weather(self, city: str) -> dict[str, object]:
        raise CityNotFoundError("City not found")

    async def get_autogen_weather_report(self, city: str) -> dict[str, str]:
        raise WeatherProviderError("Weather assistant unavailable")

class StubWeatherForecastService:
    async def get_weather_forecast(self, city: str, days: int = 3) -> dict[str, object]:
        return {
            "status": "success",
            "data": [{
                "date": "2026-09-30",
                "max_temp_c": 30,
                "min_temp_c": 20,
                "avg_temp_c": 25,
                "condition": "Sunny",
                "humidity": 60,
                "wind_speed_kmph": 10,
                "chance_of_rain": 0,
                "chance_of_snow": 0,
                "uv_index": 5,
            }],
            "isCached": False
        }

    async def get_weather_forecast_crewai(self, city: str) -> dict[str, str]:
        return {"status": "success", "message": f"CrewAI forecast report for {city}"}

class FailingWeatherForecastService(StubWeatherForecastService):
    async def get_weather_forecast(self, city: str, days: int = 3) -> dict[str, object]:
        raise CityNotFoundError("City not found")


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.setex_calls = 0

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> bool:
        self.values[key] = value
        self.setex_calls += 1
        return True


class FakeHttpClient:
    calls = 0

    async def __aenter__(self) -> "FakeHttpClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, *args: object, **kwargs: object) -> object:
        self.calls += 1
        return type(
            "FakeResponse",
            (),
            {
                "status_code": 200,
                "json": lambda self: {
                    "current_condition": [{
                        "temp_C": "25",
                        "FeelsLikeC": "26",
                        "humidity": "60",
                        "weatherDesc": [{"value": "Sunny"}],
                        "windspeedKmph": "10",
                    }],
                },
            },
        )()


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_weather_service] = lambda: StubWeatherService()
    app.dependency_overrides[get_weather_forecast_service] = lambda: StubWeatherForecastService()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_check(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_redis_health_check_returns_service_unavailable_on_timeout(
    client: TestClient,
) -> None:
    import redis

    with (
        patch("app.config.settings.redis_enabled", True),
        patch(
            "redis.Redis.from_url",
            side_effect=redis.exceptions.TimeoutError("Redis timed out"),
        ),
    ):
        response = client.get("/api/v1/health/redis")

    assert response.status_code == 503
    assert response.json() == {
        "status": "fail",
        "message": "Redis connection error.",
    }


def test_redis_health_check_reports_disabled_without_connecting(
    client: TestClient,
) -> None:
    with (
        patch("app.config.settings.redis_enabled", False),
        patch("redis.Redis.from_url") as redis_from_url,
    ):
        response = client.get("/api/v1/health/redis")

    assert response.status_code == 200
    assert response.json() == {"status": "disabled"}
    redis_from_url.assert_not_called()


def test_redis_cache_is_singleton_and_noop_without_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.cache.redis_cache import AsyncRedisCache

    async def run_test() -> None:
        cache = AsyncRedisCache()
        monkeypatch.setattr(cache, "redis", None)
        assert AsyncRedisCache() is cache
        assert await cache.get("weather:test") is None
        await cache.set("weather:test", {"value": "test"})

    asyncio.run(run_test())


def test_current_weather_uses_redis_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    async def run_test() -> None:
        cache = FakeRedis()
        http_client = FakeHttpClient()
        service = WeatherService()
        monkeypatch.setattr(service.cache, "redis", cache)

        with patch("app.services.weather_service.httpx.AsyncClient", return_value=http_client):
            first_result = await service.get_current_weather("Delhi")
            second_result = await service.get_current_weather("delhi")

        assert first_result["data"] == second_result["data"]
        assert first_result.get("isCached") is False
        assert second_result.get("isCached") is True
        assert http_client.calls == 1
        assert service.cache.redis is cache
        assert cache.setex_calls == 1

    asyncio.run(run_test())


def test_agent_report_uses_redis_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    async def run_test() -> None:
        cache = FakeRedis()
        service = WeatherService()
        monkeypatch.setattr(service.cache, "redis", cache)
        kickoff_calls = 0

        class FakeCrew:
            def kickoff(self, inputs: dict[str, str]) -> str:
                nonlocal kickoff_calls
                kickoff_calls += 1
                return f"CrewAI report for {inputs['city']}"

        with patch(
            "app.services.weather_service.build_weather_crew",
            return_value=FakeCrew(),
        ):
            first_result = await service.get_crewai_weather_report("Delhi")
            second_result = await service.get_crewai_weather_report("delhi")

        assert first_result == {
            "status": "success",
            "message": "CrewAI report for Delhi",
        }
        assert second_result == {
            "status": "success",
            "message": "CrewAI report for Delhi",
            "isCached": True,
        }
        assert kickoff_calls == 1
        assert cache.setex_calls == 1
        assert "weather:report:crewai:delhi" in cache.values

    asyncio.run(run_test())


def test_current_weather_returns_service_data(client: TestClient) -> None:
    response = client.get("/api/v1/weather", params={"city": "Delhi"})

    assert response.status_code == 200
    assert response.json()["data"]["city"] == "Delhi"
    assert response.json()["data"]["temperature"] == 25


def test_current_weather_maps_city_not_found_to_404() -> None:
    app.dependency_overrides[get_weather_service] = lambda: FailingWeatherService()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/weather", params={"city": "Unknown"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"status": "fail", "message": "City not found"}


def test_autogen_weather_returns_agent_response(client: TestClient) -> None:
    response = client.get("/api/v1/weather/autogen", params={"city": "Delhi"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "AutoGen report for Delhi",
        "isCached": False,
    }

def test_crewai_weather_returns_agent_response(client: TestClient) -> None:
    response = client.get("/api/v1/weather/crewai", params={"city": "Delhi"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "CrewAI report for Delhi",
        "isCached": False,
    }


def test_langgraph_weather_returns_agent_response(client: TestClient) -> None:
    response = client.get("/api/v1/weather/langgraph", params={"city": "Delhi"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "LangGraph report for Delhi",
        "isCached": False,
    }


def test_forecast_weather_returns_agent_response(client: TestClient) -> None:
    response = client.get("/api/v1/weather/forecast", params={"city": "Delhi"})

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["status"] == "success"
    assert json_response["data"][0]["condition"] == "Sunny"
    assert json_response["isCached"] is False


def test_forecast_weather_maps_city_not_found_to_404() -> None:
    app.dependency_overrides[get_weather_forecast_service] = lambda: FailingWeatherForecastService()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/weather/forecast", params={"city": "Unknown"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"status": "fail", "message": "City not found"}


def test_crewai_forecast_weather_returns_agent_response(client: TestClient) -> None:
    response = client.get("/api/v1/weather/forecast/crewai", params={"city": "Delhi"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "CrewAI forecast report for Delhi",
        "isCached": False,
    }


def test_autogen_weather_maps_provider_failure_to_502() -> None:
    app.dependency_overrides[get_weather_service] = lambda: FailingWeatherService()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/weather/autogen", params={"city": "Delhi"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {
        "status": "fail",
        "message": "Weather assistant unavailable",
    }


def test_unexpected_exception_uses_application_handler() -> None:
    async def raise_unexpected_error() -> None:
        raise RuntimeError("test failure")

    app.add_api_route("/test-unexpected-error", raise_unexpected_error)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/test-unexpected-error")
    finally:
        app.routes.pop()

    assert response.status_code == 500
    assert response.json() == {
        "status": "fail",
        "message": "Internal server error",
    }


def test_weather_agent_returns_agent_response(client: TestClient) -> None:
    # Just mock the run_weather_orchestrator for the test
    with (
        patch(
            "app.route.weather_agent.weather_agent_service._get_cached_report",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.route.weather_agent.weather_agent_service._cache_report",
            new=AsyncMock(),
        ),
        patch("app.services.weather_agent_service.run_weather_orchestrator") as mock_run,
    ):
        async def async_mock(*args, **kwargs):
            return "Mocked CrewAI Response"
            
        mock_run.side_effect = async_mock
        response = client.post("/api/v1/weather/agent", json={"city": "Delhi"})

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "message": "Mocked CrewAI Response",
            "isCached": False,
            "cacheKey": "weather:agent:crewai:delhi",
        }


def test_weather_langgraph_agent_returns_agent_response(client: TestClient) -> None:
    with (
        patch(
            "app.route.weather_agent.weather_agent_service._get_cached_report",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.route.weather_agent.weather_agent_service._cache_report",
            new=AsyncMock(),
        ),
        patch(
            "app.services.weather_agent_service.run_weather_orchestrator_langgraph",
            new=AsyncMock(
                return_value=(
                    "Mocked LangGraph Response",
                    "weather:orchestrator:langgraph:delhi",
                )
            ),
        ),
    ):
        response = client.post(
            "/api/v1/weather/agent/langgraph",
            json={"city": "Delhi"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "Mocked LangGraph Response",
        "isCached": False,
        "cacheKey": "weather:orchestrator:langgraph:delhi",
    }


def test_agent_providers_use_separate_report_cache_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run_test() -> None:
        service = WeatherAgentService()
        monkeypatch.setattr(service.cache, "redis", FakeRedis())
        await service._cache_report(
            "Delhi",
            AgentResponse(
                status="success",
                message="CrewAI report",
                isCached=False,
                cacheKey=service._report_cache_key("Delhi", "crewai"),
            ),
            "crewai",
        )
        await service._cache_report(
            "Delhi",
            AgentResponse(
                status="success",
                message="LangGraph report",
                isCached=False,
                cacheKey="weather:orchestrator:langgraph:delhi",
            ),
            "langgraph",
        )

        crewai_report = await service._get_cached_report("Delhi", "crewai")
        langgraph_report = await service._get_cached_report("Delhi", "langgraph")

        assert crewai_report is not None
        assert crewai_report.message == "CrewAI report"
        assert crewai_report.isCached is True
        assert crewai_report.cacheKey == "weather:agent:crewai:delhi"
        assert langgraph_report is not None
        assert langgraph_report.message == "LangGraph report"
        assert langgraph_report.isCached is True
        assert langgraph_report.cacheKey == "weather:orchestrator:langgraph:delhi"
        assert service._report_cache_key("Delhi", "crewai") != (
            service._report_cache_key("Delhi", "langgraph")
        )

    asyncio.run(run_test())


def test_agent_report_cache_key_normalizes_query_to_alphanumeric_words() -> None:
    assert (
        WeatherAgentService._report_cache_key(
            "Delhi upcoming weather for 10 days", "crewai"
        )
        == "weather:agent:crewai:delhi-upcoming-weather-for-10-days"
    )
    assert (
        WeatherAgentService._report_cache_key(
            "  Delhi,   upcoming weather! ", "crewai"
        )
        == "weather:agent:crewai:delhi-upcoming-weather"
    )


@pytest.mark.parametrize(
    ("method", "path", "kwargs", "expected_response"),
    [
        (
            "get",
            "/api/v1/weather/crewai",
            {"params": {"city": "x" * 1001}},
            {
                "status": "fail",
                "message": "Query exceeds the allowed length",
            },
        ),
        (
            "get",
            "/api/v1/weather/langgraph",
            {"params": {"city": "x" * 1001}},
            {
                "status": "fail",
                "message": "Query exceeds the allowed length",
            },
        ),
        (
            "get",
            "/api/v1/weather/autogen",
            {"params": {"city": "x" * 1001}},
            {
                "status": "fail",
                "message": "Query exceeds the allowed length",
            },
        ),
        (
            "get",
            "/api/v1/weather/forecast/crewai",
            {"params": {"city": "x" * 1001}},
            {
                "status": "fail",
                "message": "Query exceeds the allowed length",
            },
        ),
        (
            "post",
            "/api/v1/weather/agent",
            {"json": {"query": "x" * 1001}},
            {
                "status": "fail",
                "message": "Query exceeds the allowed length",
            },
        ),
    ],
)
def test_llm_routes_reject_queries_over_maximum_length(
    client: TestClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
    expected_response: dict[str, str],
) -> None:
    response = getattr(client, method)(path, **kwargs)

    assert response.status_code == 400
    assert response.json() == expected_response


def test_request_validation_error_uses_generic_response(client: TestClient) -> None:
    response = client.post(
        "/api/v1/weather/agent",
        json={"query": ["not", "a", "string"]},
    )

    assert response.status_code == 422
    assert response.json() == {
        "status": "fail",
        "message": "Request validation failed",
    }


def test_http_error_uses_generic_response(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"status": "fail", "message": "Not Found"}


@pytest.mark.parametrize(
    ("error", "status_code", "message"),
    [
        (CityNotFoundError("City not found"), 404, "City not found"),
        (
            WeatherProviderError("Weather assistant unavailable"),
            502,
            "Weather assistant unavailable",
        ),
    ],
)
def test_weather_agent_returns_generic_failure_response(
    client: TestClient,
    error: Exception,
    status_code: int,
    message: str,
) -> None:
    with patch(
        "app.route.weather_agent.weather_agent_service.process_weather_query",
        new=AsyncMock(side_effect=error),
    ):
        response = client.post(
            "/api/v1/weather/agent",
            json={"query": "What is the weather in Delhi?"},
        )

    assert response.status_code == status_code
    assert response.json() == {"status": "fail", "message": message}
