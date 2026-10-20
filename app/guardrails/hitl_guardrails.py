"""Deterministic checks used before executing HITL weather requests."""

import re

ACTION_APPROVAL_PATTERNS = (
    r"\b(send|issue|publish|broadcast)\b.{0,100}"
    r"\b(alert|notification|email|message)\b.{0,100}"
    r"\b(all users|all customers|everyone)\b",
    r"\b(notify|email|message)\b.{0,100}"
    r"\b(all users|all customers|everyone)\b",
)

WEATHER_TERMS = (
    "weather",
    "rain",
    "umbrella",
    "forecast",
    "temperature",
)

LOCATION_STOP_WORDS = (
    "today",
    "tomorrow",
    "tonight",
    "now",
    "currently",
    "this",
    "next",
    "week",
    "month",
    "weekend",
    "for",
    "during",
    "weather",
    "forecast",
    "temperature",
    "rain",
    "umbrella",
    "please",
)


def requires_action_approval(query: str) -> bool:
    query = query.casefold()
    return any(re.search(pattern, query) for pattern in ACTION_APPROVAL_PATTERNS)


def needs_location_clarification(query: str, resolved_city: str | None) -> bool:
    query_lower = query.casefold()
    if re.match(
        r"^\s*(?:how\s+(?:do|can|to)\b|what\s+does\b|define\b|explain\b)",
        query_lower,
    ):
        return False

    weather_intent = any(
        re.search(rf"\b{re.escape(term)}\b", query_lower)
        for term in WEATHER_TERMS
    )

    return (
        weather_intent
        and extract_explicit_city(query) is None
        and resolved_city is None
    )


def extract_explicit_city(query: str) -> str | None:
    """Extract a location following a common preposition in a weather query."""
    match = re.search(
        r"\b(?:in|at|for)\s+([a-z][a-z .'-]{0,59})",
        query,
        re.IGNORECASE,
    )
    if match is None:
        return None

    city = match.group(1).strip(" .,'\"?!")
    stop_pattern = r"\b(?:" + "|".join(
        re.escape(word) for word in LOCATION_STOP_WORDS
    ) + r")\b"
    city = re.split(stop_pattern, city, maxsplit=1, flags=re.IGNORECASE)[0]
    city = city.strip(" .,'\"?!")
    city = re.sub(r"^(?:the|a|an)\s+", "", city, flags=re.IGNORECASE)
    if not city or city.casefold() in LOCATION_STOP_WORDS:
        return None
    return city


def extract_city_answer(query: str) -> str | None:
    """Accept either a city-only clarification reply or a location in a sentence."""
    explicit_city = extract_explicit_city(query)
    if explicit_city is not None:
        return explicit_city

    city = query.strip(" .,'\"?!")
    if re.fullmatch(r"[a-z][a-z .'-]{0,59}", city, re.IGNORECASE):
        return city
    return None
