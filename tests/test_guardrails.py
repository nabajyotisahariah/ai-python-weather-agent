import pytest

from app.guardrails.input_guardrails import (
    MAX_QUERY_LENGTH,
    GuardrailViolation,
    validate_query,
)


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
