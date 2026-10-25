import pytest

from app.agents.crewai.weather_aqi_agent import build_weather_aqi_crew
from app.orchestrator.crewai.agents import create_weather_orchestrator
from app.orchestrator.crewai import tools as crewai_tools
from app.tools.crewai import weather_aqi_tool


def test_waqi_tool_formats_provider_data(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "status": "ok",
                "data": {
                    "aqi": 82,
                    "dominentpol": "pm25",
                    "city": {"name": "Delhi"},
                    "iaqi": {"pm25": {"v": 82.0}, "pm10": {"v": 41}},
                    "time": {"s": "2026-10-25 10:00:00"},
                },
            }

    def fake_get(url: str, **kwargs: object) -> FakeResponse:
        assert url == "https://api.waqi.info/feed/New%20Delhi/"
        assert kwargs["params"] == {"token": "test-waqi-token"}
        assert kwargs["timeout"] == weather_aqi_tool.settings.weather_timeout_seconds
        return FakeResponse()

    monkeypatch.setattr(weather_aqi_tool.settings, "waqi_api_token", "test-waqi-token")
    monkeypatch.setattr(weather_aqi_tool.requests, "get", fake_get)

    report = weather_aqi_tool.fetch_air_quality("New Delhi")

    assert report == (
        "City: Delhi\n"
        "Air Quality Index (AQI): 82\n"
        "Dominant pollutant: pm25\n"
        "PM2.5: 82.0\n"
        "PM10: 41\n"
        "Observed at: 2026-10-25 10:00:00"
    )


def test_waqi_tool_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(weather_aqi_tool.settings, "waqi_api_token", None)

    with pytest.raises(RuntimeError, match="WAQI_API_TOKEN is not configured"):
        weather_aqi_tool.fetch_air_quality("Delhi")


def test_waqi_tool_rejects_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "error", "data": "Unknown station"}

    monkeypatch.setattr(weather_aqi_tool.settings, "waqi_api_token", "test-waqi-token")
    def fake_get(url: str, **kwargs: object) -> FakeResponse:
        assert url.endswith("/feed/Delhi/")
        assert kwargs["params"] == {"token": "test-waqi-token"}
        return FakeResponse()

    monkeypatch.setattr(weather_aqi_tool.requests, "get", fake_get)

    with pytest.raises(RuntimeError, match="did not return air-quality data"):
        weather_aqi_tool.fetch_air_quality("Delhi")


def test_aqi_specialist_is_registered_with_agent_orchestrator() -> None:
    resolved_cities: list[str] = []
    orchestrator = create_weather_orchestrator(resolved_cities.append)
    aqi_crew = build_weather_aqi_crew("Delhi")

    assert "get_air_quality" in {tool.name for tool in orchestrator.tools}
    assert aqi_crew.tasks[0].agent.tools[0].name == "get_air_quality"


def test_hitl_aqi_tool_remembers_resolved_city(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved_cities: list[str] = []
    monkeypatch.setattr(
        crewai_tools,
        "run_air_quality_agent",
        lambda city: f"AQI report for {city}",
    )

    result = crewai_tools._get_air_quality("Noida", resolved_cities.append)

    assert result == "AQI report for Noida"
    assert resolved_cities == ["Noida"]
