import re
from app.schema.weather import ActionIntent


ACTION_PATTERNS = (
    (
        "broadcast_alert",
        re.compile(
            r"\b(broadcast|send|issue|publish)\b.{0,100}"
            r"\b(alert|notification|email|message)\b"
            r".{0,100}\b(all users|all customers|everyone)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "bulk_notification",
        re.compile(
            r"\b(notify|email|message)\b.{0,100}"
            r"\b(all users|all customers|everyone)\b",
            re.IGNORECASE,
        ),
    ),
)


def detect_consequential_action(query: str) -> ActionIntent | None:
    for action, pattern in ACTION_PATTERNS:
        if pattern.search(query):
            return ActionIntent(action=action)

    return None

#temp = detect_consequential_action("Please broadcast an alert to all users about the weather warning.")
#print(temp)  # Output: ActionIntent(action='broadcast_alert', target=None)

def needs_location_clarification(
    query: str,
    resolved_city: str | None,
) -> bool:
    if resolved_city:
        return False

    # These examples are intentionally simple.
    # Use your intent router and location extractor in production.
    weather_terms = (
        "weather",
        "rain",
        "umbrella",
        "forecast",
        "temperature",
        "jacket",
        "coat",
        "snow",
        "sunny",
        "hot",
        "cold",
        "wind",
        "storm",
        "cloud",
    )

    query_lower = query.casefold()

    is_weather_query = any(
        term in query_lower for term in weather_terms
    )

    if not is_weather_query:
        return False

    location_match = re.search(
        r"\b(?:in|at|near)\s+([a-z][a-z.'-]*(?:\s+[a-z][a-z.'-]*)?)",
        query_lower,
    )

    if location_match is None:
        return True

    location = location_match.group(1).strip()

    if location in {
        "the morning",
        "the afternoon",
        "the evening",
        "the night",
        "my location",
        "my area",
        "here",
        "there",
        "today",
        "tomorrow",
        "tonight",
    }:
        return True

    return False