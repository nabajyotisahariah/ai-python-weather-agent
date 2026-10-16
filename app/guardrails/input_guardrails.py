MAX_QUERY_LENGTH = 100


class GuardrailViolation(ValueError):
    pass


def validate_query(query: str) -> str:
    query = query.strip()

    if not query:
        raise GuardrailViolation("Query cannot be empty")

    if len(query) > MAX_QUERY_LENGTH:
        raise GuardrailViolation("Query exceeds the allowed length")

    return query
