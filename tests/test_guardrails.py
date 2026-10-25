import pytest

from app.guardrails.input_guardrails import (
    MAX_QUERY_LENGTH,
    GuardrailViolation,
    validate_query,
)
from app.guardrails.hitl_guardrails import needs_location_clarification


def test_validate_query_strips_surrounding_whitespace() -> None:
    assert validate_query("  What is the weather in Delhi?  ") == (
        "What is the weather in Delhi?"
    )


@pytest.mark.parametrize("query", ["", " ", "\t\n"])
def test_validate_query_rejects_empty_input(query: str) -> None:
    with pytest.raises(GuardrailViolation, match="Query cannot be empty"):
        validate_query(query)


def test_validate_query_accepts_maximum_length() -> None:
    query = "a" * MAX_QUERY_LENGTH

    assert validate_query(query) == query


def test_validate_query_rejects_input_over_maximum_length() -> None:
    query = "a" * (MAX_QUERY_LENGTH + 1)

    with pytest.raises(GuardrailViolation, match="Query exceeds the allowed length"):
        validate_query(query)


def test_location_guardrail_accepts_city_in_query() -> None:
    assert needs_location_clarification(
        "What is the weather in Delhi?",
        resolved_city=None,
    ) is False


def test_location_guardrail_uses_saved_city() -> None:
    assert needs_location_clarification(
        "Will it rain tomorrow?",
        resolved_city="Delhi",
    ) is False


def test_location_guardrail_requests_city_when_missing() -> None:
    assert needs_location_clarification(
        "Will it rain tomorrow?",
        resolved_city=None,
    ) is True


@pytest.mark.parametrize(
    "query",
    [
        "What is the AQI?",
        "How is the air quality?",
        "Is there pollution?",
    ],
)
def test_location_guardrail_requests_city_for_air_quality(
    query: str,
) -> None:
    assert needs_location_clarification(query, resolved_city=None) is True


@pytest.mark.parametrize(
    "query",
    [
        "What is the AQI in Noida?",
        "What is the AQI for Noida?",
        "How is the air quality near Delhi?",
    ],
)
def test_location_guardrail_accepts_air_quality_city(
    query: str,
) -> None:
    assert needs_location_clarification(query, resolved_city=None) is False
