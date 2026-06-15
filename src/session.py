"""
session.py — Local session state serialization for SPICE.

Requirement 9: The app auto-serializes its state whenever it loses focus
and reloads seamlessly on resume, preserving conversation history and
accumulated latency metrics.
"""

import json
import logging
import os
from datetime import datetime, timezone

from path_utils import get_writable_path

logger = logging.getLogger(__name__)
SESSION_FILE = "session_state.json"


def _session_path() -> str:
    return get_writable_path(SESSION_FILE)


def save_session(
    active_scenario_id: str,
    conversation_history: list[dict],
    accumulated_latency_ms: float,
    interaction_count: int,
    current_phase: int,
) -> None:
    """Persist full session state to disk."""
    state = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "active_scenario_id": active_scenario_id,
        "conversation_history": conversation_history,
        "accumulated_latency_ms": accumulated_latency_ms,
        "interaction_count": interaction_count,
        "current_phase": current_phase,
    }
    try:
        with open(_session_path(), "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
        logger.info("Session saved.")
    except Exception as exc:  # noqa: BLE001
        logger.error("Session save failed: %s", exc)


def load_session() -> dict | None:
    """
    Load the last saved session.  Returns None if no session file exists
    or it cannot be parsed.
    """
    path = _session_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Session load failed: %s", exc)
        return None


def clear_session() -> None:
    """Delete the session file (e.g., after a study ends)."""
    path = _session_path()
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as exc:  # noqa: BLE001
        logger.error("Session clear failed: %s", exc)
