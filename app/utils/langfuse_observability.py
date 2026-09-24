import logging
from contextlib import contextmanager, nullcontext
from collections.abc import Generator
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

try:
    from langfuse import get_client
except ImportError:
    get_client = None


def is_enabled() -> bool:
    return bool(
        get_client
        and settings.langfuse_public_key
        and settings.langfuse_secret_key
    )


@contextmanager
def observe_operation(
    name: str,
    *,
    input_data: dict[str, Any],
) -> Generator[Any | None, None, None]:
    """Create a Langfuse span when configured, otherwise do nothing."""
    if not is_enabled():
        with nullcontext() as observation:
            yield observation
        return

    try:
        client = get_client()
        observation_context = client.start_as_current_observation(
            as_type="span",
            name=name,
            input=input_data,
        )
    except Exception:
        logger.exception("Langfuse observation failed for %s", name)
        with nullcontext() as observation:
            yield observation
        return

    with observation_context as observation:
        yield observation


def update_observation(
    observation: Any | None,
    *,
    output: Any | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    if observation is None:
        return

    try:
        observation.update(output=output, metadata=metadata)
    except Exception:
        logger.exception("Langfuse observation update failed")