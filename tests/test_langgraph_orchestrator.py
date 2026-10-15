import asyncio
from unittest.mock import AsyncMock

import pytest
from langchain_openai import ChatOpenAI

from app.guardrails.input_guardrails import GuardrailViolation
from app.orchestrator.langgraph import orchestrator
from app.tools.langgraph import weather_tool
from app.tools.langgraph.weather_tool import get_weather_forecast


def test_orchestrator_graph_compiles_with_supervisor_and_specialists() -> None:
    llm = ChatOpenAI(api_key="test-key", model="gpt-4o-mini", temperature=0)

    graph = orchestrator._build_orchestrator_graph(llm)

    assert "orchestrator" in graph.nodes
    assert "specialists" in graph.nodes


def test_langgraph_orchestrator_returns_cached_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        orchestrator.redis_cache,
        "get",
        AsyncMock(return_value={"raw": "Cached forecast"}),
    )

    result = asyncio.run(
        orchestrator.run_weather_orchestrator_langgraph("Weather forecast for Delhi")
    )

    assert result == "Cached forecast"


def test_langgraph_orchestrator_rejects_empty_query_before_cache_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache_get = AsyncMock()
    monkeypatch.setattr(orchestrator.redis_cache, "get", cache_get)

    with pytest.raises(GuardrailViolation, match="Query cannot be empty"):
        asyncio.run(orchestrator.run_weather_orchestrator_langgraph(" "))

    cache_get.assert_not_awaited()


def test_forecast_tool_rejects_invalid_duration() -> None:
    with pytest.raises(
        GuardrailViolation,
        match="Forecast duration must be between 1 and 7 days",
    ):
        asyncio.run(
            get_weather_forecast.ainvoke({"city": "Delhi", "days": 8})
        )


def test_forecast_tool_formats_provider_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "weather": [
                    {
                        "date": "2026-10-15",
                        "maxtempC": "28",
                        "mintempC": "18",
                        "hourly": [
                            {"weatherDesc": [{"value": "Cloudy"}]},
                        ],
                    }
                ]
            }

    class FakeAsyncClient:
        def __init__(self, **_kwargs: object) -> None:
            assert "timeout" in _kwargs

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *_args: object) -> None:
            assert len(_args) == 3
            return None

        async def get(self, url: str, **kwargs: object) -> FakeResponse:
            assert url.endswith("/New%20York")
            assert kwargs["params"] == {"format": "j1"}
            return FakeResponse()

    monkeypatch.setattr(weather_tool.httpx, "AsyncClient", FakeAsyncClient)

    result = asyncio.run(
        get_weather_forecast.ainvoke({"city": "New York", "days": 1})
    )

    assert result == (
        "Date: 2026-10-15, Max Temp: 28°C, Min Temp: 18°C, Condition: Cloudy"
    )
