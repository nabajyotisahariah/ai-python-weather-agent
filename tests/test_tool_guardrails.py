import asyncio

import pytest

from app.guardrails.input_guardrails import GuardrailViolation
from app.guardrails.tool_guardrails import ALLOWED_TOOLS, validate_tool_call
from app.tools.mcp import weather_tools


@pytest.mark.parametrize(
    "tool_name",
    ["get_weather", "get_weather_forecast", "search_faq"],
)
def test_validate_tool_call_allows_permitted_tools(tool_name: str) -> None:
    assert tool_name in ALLOWED_TOOLS
    validate_tool_call(tool_name, {})


def test_validate_tool_call_rejects_unpermitted_tools() -> None:
    with pytest.raises(GuardrailViolation, match="Tool is not permitted"):
        validate_tool_call("delete_data", {})


@pytest.mark.parametrize("days", [1, 7])
def test_validate_tool_call_accepts_forecast_duration_boundaries(
    days: int,
) -> None:
    validate_tool_call("get_weather_forecast", {"days": days})


@pytest.mark.parametrize("days", [0, 8, True, False, 1.5, "3", None])
def test_validate_tool_call_rejects_invalid_forecast_duration(
    days: object,
) -> None:
    with pytest.raises(
        GuardrailViolation,
        match="Forecast duration must be between 1 and 7 days",
    ):
        validate_tool_call("get_weather_forecast", {"days": days})


def test_mcp_forecast_rejects_invalid_duration_before_service_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_called = False

    class StubForecastService:
        async def get_weather_forecast(
            self,
            city: str,
            days: int,
        ) -> None:
            nonlocal service_called
            service_called = True

    monkeypatch.setattr(
        weather_tools,
        "weather_forecast_service",
        StubForecastService(),
    )

    with pytest.raises(GuardrailViolation):
        asyncio.run(weather_tools.get_weather_forecast("Delhi", True))

    assert not service_called
