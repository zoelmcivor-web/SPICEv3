"""
participant.py — Participant registration and profile management for SPICE.

Handles first-launch registration, profile persistence, and the
state flag that bypasses the gateway on subsequent launches.

IRB NOTE: Only first name, last name, and a generated participant ID are
stored.  No sensitive PII beyond the cover-story registration fields is
ever written to disk.
"""

import json
import logging
import os
import uuid

from path_utils import get_writable_path

logger = logging.getLogger(__name__)

PROFILE_FILE = "participant_profile.json"


def _profile_path() -> str:
    return get_writable_path(PROFILE_FILE)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def profile_exists() -> bool:
    """Return True if a completed participant profile is already on disk."""
    path = _profile_path()
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("registration_complete", False)
    except Exception as exc:  # noqa: BLE001
        logger.error("Could not read profile: %s", exc)
        return False


def load_profile() -> dict:
    """Load and return the participant profile dict.  Returns {} on failure."""
    try:
        with open(_profile_path(), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:  # noqa: BLE001
        logger.warning("load_profile failed: %s", exc)
        return {}


def save_profile(first_name: str, last_name: str) -> dict:
    """
    Sanitise inputs, generate a participant ID, write participant_profile.json,
    and return the profile dict.
    """
    # Sanitise: strip whitespace, title-case.
    first = first_name.strip().title()
    last = last_name.strip().title()

    participant_id = f"P-{uuid.uuid4().hex[:8].upper()}"

    profile = {
        "participant_id": participant_id,
        "first_name": first,
        "last_name": last,
        "registration_complete": True,
    }

    path = _profile_path()
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(profile, fh, indent=2)
        logger.info("Profile saved for %s (ID: %s)", first, participant_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to save profile: %s", exc)

    return profile
