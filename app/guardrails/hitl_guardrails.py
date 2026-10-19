"""
Start with deterministic rules for known situations. Do not rely solely on an LLM to decide whether
a security-sensitive action is authorized.
"""

import re

ACTION_APPROVAL_PATTERNS = (
    r"\bsend\b.*\b(alert|notification|email)\b",
    r"\bnotify\b.*\b(all users|all customers)\b",
    r"\bbroadcast\b",
)

def requires_action_approval(query: str) -> bool:
    query = query.casefold()

    return any(
        re.search(pattern, query)
        for pattern in ACTION_APPROVAL_PATTERNS
    )


def needs_location_clarification(
    query: str,
    cached_context: list | None,
) -> bool:
    query_lower = query.casefold()

    weather_intent = any(
        word in query_lower
        for word in (
            "weather",
            "rain",
            "umbrella",
            "forecast",
            "temperature",
        )
    )

    if not weather_intent:
        return False

    # Improve this check with structured user preferences
    # and location extraction in production.
    has_location_context = bool(cached_context) and any(
        message.get("role") == "user"
        and any(
            phrase in message.get("content", "").casefold()
            for phrase in (
                "i am from",
                "i live in",
                "i moved to",
                "my city is",
            )
        )
        for message in cached_context
    )

    explicit_location = bool(
        re.search(
            r"\b(in|for|at|to)\s+[A-Z][a-z]+",
            query,
        )
    )

    return not has_location_context and not explicit_location