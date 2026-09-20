from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.route.weather import get_weather_service
from app.services.weather_service import CityNotFoundError, WeatherProviderError


class StubWeatherService:
    async def get_current_weather(self, city: str) -> dict[str, str | int | float]:
        return {
            "city": city,
            "temperature": 25,
            "feels_like": 26,
            "humidity": 60,
            "description": "Sunny",
            "wind_speed": 10,
        }

    async def get_crewai_weather_report(self, city: str) -> dict[str, str]:
        return {"status": "ok", "message": f"CrewAI report for {city}"}

    async def get_opengen_weather_report(self, city: str) -> dict[str, str]:
        return {"status": "ok", "message": f"OpenGen report for {city}"}

    async def get_langgraph_weather_report(self, city: str) -> dict[str, str]:
        return {"status": "ok", "message": f"LangGraph report for {city}"}

    async def get_autogen_weather_report(self, city: str) -> dict[str, str]:
        return {"status": "ok", "message": f"AutoGen report for {city}"}

    async def get_google_adk_weather_report(self, city: str) -> dict[str, str]:
        return {"status": "ok", "message": f"Google ADK report for {city}"}


class FailingWeatherService(StubWeatherService):
    async def get_current_weather(self, city: str) -> dict[str, str | int | float]:
        raise CityNotFoundError("City not found")

    async def get_autogen_weather_report(self, city: str) -> dict[str, str]:
        raise WeatherProviderError("Weather assistant unavailable")


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_weather_service] = lambda: StubWeatherService()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_check(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_current_weather_returns_service_data(client: TestClient) -> None:
    response = client.get("/api/v1/weather", params={"city": "Delhi"})

    assert response.status_code == 200
    assert response.json()["city"] == "Delhi"
    assert response.json()["temperature"] == 25


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
        "status": "ok",
        "message": "AutoGen report for Delhi",
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