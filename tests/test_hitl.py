import asyncio
from unittest.mock import AsyncMock

import pytest

from app.guardrails.hitl_guardrails import (
    extract_city_answer,
    extract_explicit_city,
    needs_location_clarification,
    requires_action_approval,
)
from app.schema.weather import ClarificationData, Status
from app.services.weather_agent_service import WeatherAgentService


@pytest.mark.parametrize(
    ("query", "resolved_city", "expected"),
    [
        ("Should I carry an umbrella tomorrow?", None, True),
        ("Weather in new delhi tomorrow?", None, False),
        ("What's the forecast for tomorrow?", None, True),
        ("Should I carry an umbrella tomorrow?", "Noida", False),
        ("How do I send a weather alert?", None, False),
    ],
)
def test_needs_location_clarification(
    query: str,
    resolved_city: str | None,
    expected: bool,
) -> None:
    assert needs_location_clarification(query, resolved_city) is expected


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Weather in New Delhi today?", "New Delhi"),
        ("Should I carry an umbrella in delhi tomorrow?", "delhi"),
        ("Weather for tomorrow?", None),
    ],
)
def test_extract_explicit_city(query: str, expected: str | None) -> None:
    assert extract_explicit_city(query) == expected


def test_extract_city_answer_accepts_city_or_rejects_sentences() -> None:
    assert extract_city_answer("Noida") == "Noida"
    assert extract_city_answer("Please tell me the forecast") is None


def test_action_detection_requires_a_bulk_recipient() -> None:
    assert requires_action_approval(
        "Send a severe weather alert to all customers"
    )
    assert not requires_action_approval("How do I send a weather alert?")


def test_missing_city_creates_typed_clarification_without_running_agent() -> None:
    async def run_test() -> None:
        service = WeatherAgentService.__new__(WeatherAgentService)
        service.crewai_orchestrator = type(
            "FakeOrchestrator",
            (),
            {
                "get_resolved_city": AsyncMock(return_value=None),
                "create_pending_clarification": AsyncMock(return_value="token-123"),
                "run_weather_orchestrator_hitl": AsyncMock(),
            },
        )()

        result = await service.process_weather_hitl(
            "Should I carry an umbrella tomorrow?",
            session_id="session-123",
            user_id="user-123",
        )

        assert result.status is Status.PENDING_CLARIFICATION
        assert result.data == ClarificationData(clarification_id="token-123")
        service.crewai_orchestrator.run_weather_orchestrator_hitl.assert_not_awaited()

    asyncio.run(run_test())


def test_clarification_answer_resumes_original_query_for_resolved_city() -> None:
    async def run_test() -> None:
        service = WeatherAgentService.__new__(WeatherAgentService)
        service.crewai_orchestrator = type(
            "FakeOrchestrator",
            (),
            {
                "consume_pending_clarification": AsyncMock(
                    return_value="Should I carry an umbrella tomorrow?"
                ),
                "run_weather_orchestrator_hitl": AsyncMock(
                    return_value=("Forecast", "cache-key", False)
                ),
                "set_resolved_city": AsyncMock(),
            },
        )()

        result = await service.process_weather_hitl(
            "Noida",
            session_id="session-123",
            user_id="user-123",
            clarification_id="token-123",
        )

        assert result.status is Status.SUCCESS
        service.crewai_orchestrator.consume_pending_clarification.assert_awaited_once_with(
            "token-123",
            "session-123",
            "user-123",
        )
        service.crewai_orchestrator.run_weather_orchestrator_hitl.assert_awaited_once_with(
            "Should I carry an umbrella tomorrow?",
            session_id="session-123",
            user_id="user-123",
            resolved_city="Noida",
        )
        service.crewai_orchestrator.set_resolved_city.assert_awaited_once_with(
            "session-123",
            "user-123",
            "Noida",
        )

    asyncio.run(run_test())


def test_consequential_action_is_rejected_without_execution() -> None:
    async def run_test() -> None:
        service = WeatherAgentService.__new__(WeatherAgentService)
        service.crewai_orchestrator = type(
            "FakeOrchestrator",
            (),
            {"run_weather_orchestrator_hitl": AsyncMock()},
        )()

        result = await service.process_weather_hitl(
            "Send a severe weather alert to all customers",
            session_id="session-123",
            user_id="user-123",
        )

        assert result.status is Status.FAIL
        assert "No action was taken" in result.message
        service.crewai_orchestrator.run_weather_orchestrator_hitl.assert_not_awaited()

    asyncio.run(run_test())
