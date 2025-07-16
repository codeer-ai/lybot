from __future__ import annotations
import os
from typing import Any, Dict, Optional

from loguru import logger

"""Centralised analytics helper using PostHog.

Import `capture` from this module and call it wherever an analytic event
needs to be sent.  The helper will no-op automatically when the
``POSTHOG_API_KEY`` environment variable is not set so the rest of the
codebase does not need to guard against missing configuration.
"""
try:
    from posthog import Posthog  # type: ignore
except Exception as exc:  # pragma: no cover – runtime optional dependency
    Posthog = None  # type: ignore  # pylint: disable=invalid-name
    logger.warning("PostHog import failed: %s. Analytics disabled.", exc)

__all__ = ["capture", "posthog"]

POSTHOG_API_KEY: Optional[str] = os.getenv("POSTHOG_API_KEY")
POSTHOG_HOST: str = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com")

posthog: Optional["Posthog"]
if Posthog is not None and POSTHOG_API_KEY:
    posthog = Posthog(project_api_key=POSTHOG_API_KEY, host=POSTHOG_HOST)  # type: ignore[arg-type]
    logger.info("PostHog analytics enabled – host=%s", POSTHOG_HOST)
else:
    posthog = None
    if not POSTHOG_API_KEY:
        logger.warning("POSTHOG_API_KEY not set; analytics disabled.")


def capture(
    distinct_id: str, event: str, properties: Optional[Dict[str, Any]] = None
) -> None:
    """Send an analytics event if PostHog is configured.

    Args:
        distinct_id:  A stable identifier for the user/session.  For our
                       purposes we pass the session_id generated in the API.
        event:        Name of the event (e.g. ``"chat_completion"``).
        properties:   Extra event data.
    """
    if posthog is None:
        return

    try:
        posthog.capture(
            distinct_id=distinct_id, event=event, properties=properties or {}
        )  # type: ignore[call-arg]
    except Exception as exc:  # noqa: BLE001 – we only want to avoid crashing caller
        # Swallow all analytics errors – never break user flow.
        logger.warning("PostHog capture failed: %s", exc)
