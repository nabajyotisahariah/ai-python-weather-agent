import asyncio
from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.route.weather import get_weather_service
from app.route.weather_forecast import get_weather_forcast_service
from app.services.weather_service import (
    CityNotFoundError,
    WeatherProviderError,
    WeatherService,
)


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

    async def get_weather_forcast_crewai(self, city: str) -> dict[str, str]:
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
    app.dependency_overrides[get_weather_forcast_service] = lambda: StubWeatherForecastService()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_check(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_current_weather_uses_redis_cache() -> None:
    async def run_test() -> None:
        cache = FakeRedis()
        http_client = FakeHttpClient()
        service = WeatherService(redis_client=cache)

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


def test_agent_report_uses_redis_cache() -> None:
    async def run_test() -> None:
        cache = FakeRedis()
        service = WeatherService(redis_client=cache)
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
    assert response.json() == {"detail": "City not found"}


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
    app.dependency_overrides[get_weather_forcast_service] = lambda: FailingWeatherForecastService()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/weather/forecast", params={"city": "Unknown"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "City not found"}


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
    with patch("app.services.weather_agent_service.run_weather_orchestrator") as mock_run:
        # Mock async function return
        mock_run.return_value = "Mocked CrewAI Response"
        async def async_mock(*args, **kwargs):
            return "Mocked CrewAI Response"
        mock_run.side_effect = async_mock
        response = client.get("/api/v1/weather/agent", params={"city": "Delhi"})
        
        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "message": "Mocked CrewAI Response",
            "isCached": False,
        }
