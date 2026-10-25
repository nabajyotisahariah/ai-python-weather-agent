from app.guardrails.input_guardrails import GuardrailViolation

ALLOWED_TOOLS = {
    "get_weather",
    "get_weather_forecast",
    "get_air_quality",
    "search_faq",
}


def validate_tool_call(
    tool_name: str,
    arguments: dict[str, object],
) -> None:
    if tool_name not in ALLOWED_TOOLS:
        raise GuardrailViolation(f"Tool is not permitted: {tool_name}")

    if tool_name == "get_weather_forecast":
        days = arguments.get("days", 5)

        if (
            not isinstance(days, int)
            or isinstance(days, bool)
            or not 1 <= days <= 7
        ):
            raise GuardrailViolation(
                "Forecast duration must be between 1 and 7 days"
            )
