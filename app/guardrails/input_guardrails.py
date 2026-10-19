from httpx2 import query


MAX_QUERY_LENGTH = 100


class GuardrailViolation(ValueError):
    pass


def validate_query(query: str) -> str:
    query = query.strip()

    if not query or len(query) == 0:
        raise GuardrailViolation("Query cannot be empty")

    if "location" in query.casefold() or "unknown" in query.casefold() or "unspecified" in query.casefold():
        raise GuardrailViolation("Please specify a city or location.")

    if len(query) > MAX_QUERY_LENGTH:
        raise GuardrailViolation("Query exceeds the allowed length")

    return query
