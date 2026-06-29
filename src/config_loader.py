"""
config_loader.py — Android-safe configuration loader for SPICE v2.

Changes from v1:
  - Scenarios are now loaded from individual files in scenarios/ directory
  - Each scenario file is fully self-contained (prompts, fallbacks, timing, etc.)
  - Image URL support: downloads and caches profile pictures locally
  - config.json controls app-level settings only (active scenario, AI model, etc.)
  - Adding a new scenario = dropping a .json file in scenarios/ directory
"""

import json
import logging
import os

from path_utils import get_secure_path, get_writable_path
from defaults import DEFAULT_CONFIG, DEFAULT_MANIFEST

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _load_json(path: str, fallback: dict) -> dict:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                logger.info("Loaded %s", path)
                return data
        else:
            logger.warning("File not found: %s — using fallback.", path)
    except Exception as exc:
        logger.error("Failed to load %s: %s — using fallback.", path, exc)
    return fallback


def _save_json(path: str, data: dict) -> bool:
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return True
    except Exception as exc:
        logger.error("Failed to save %s: %s", path, exc)
        return False


# ---------------------------------------------------------------------------
# Scenario directory loader
# ---------------------------------------------------------------------------

def _load_scenarios_from_directory(scenarios_dir: str) -> list[dict]:
    """
    Scan *scenarios_dir* for .json files and load each as a scenario.
    Files starting with _ (like _TEMPLATE.json) are skipped.
    Only scenarios with "enabled": true are returned.
    Falls back to DEFAULT_MANIFEST scenarios if directory is empty or missing.
    """
    scenarios = []

    if not os.path.exists(scenarios_dir):
        logger.warning("Scenarios directory not found: %s", scenarios_dir)
        return DEFAULT_MANIFEST.get("scenarios", [])

    try:
        files = sorted([
            f for f in os.listdir(scenarios_dir)
            if f.endswith(".json") and not f.startswith("_")
        ])
    except Exception as exc:
        logger.error("Cannot list scenarios directory: %s", exc)
        return DEFAULT_MANIFEST.get("scenarios", [])

    for filename in files:
        path = os.path.join(scenarios_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not data.get("enabled", True):
                logger.info("Skipping disabled scenario: %s", filename)
                continue
            # Validate required fields
            if not data.get("id") or not data.get("hook_message"):
                logger.warning("Skipping invalid scenario file: %s", filename)
                continue
            scenarios.append(data)
            logger.info("Loaded scenario: %s", data["id"])
        except Exception as exc:
            logger.error("Failed to load scenario %s: %s", filename, exc)

    if not scenarios:
        logger.warning("No valid scenarios found — using defaults.")
        return DEFAULT_MANIFEST.get("scenarios", [])

    return scenarios


# ---------------------------------------------------------------------------
# AppConfig
# ---------------------------------------------------------------------------

class AppConfig:

    def __init__(self) -> None:
        self._config_path   = get_writable_path("config.json")
        self._scenarios_dir = get_writable_path("scenarios")

        # Also check packaged (read-only) asset locations as source
        source_config        = get_secure_path("config.json")
        source_scenarios_dir = get_secure_path("scenarios")

        # Load app config
        if os.path.exists(self._config_path):
            self.config = _load_json(self._config_path, DEFAULT_CONFIG.copy())
        else:
            self.config = _load_json(source_config, DEFAULT_CONFIG.copy())
            self._flush_config()

        # Merge missing keys from defaults
        for key, val in DEFAULT_CONFIG.items():
            self.config.setdefault(key, val)

        # Load scenarios — prefer writable copy, fall back to packaged assets
        scenarios_dir = (self._scenarios_dir
                         if os.path.exists(self._scenarios_dir)
                         else source_scenarios_dir)
        self._scenarios: list[dict] = _load_scenarios_from_directory(scenarios_dir)
        self._scenarios_dir_active = scenarios_dir

        # Load contacts
        contacts_path_w = get_writable_path("scenarios/contacts.json")
        contacts_path_s = get_secure_path("scenarios/contacts.json")
        contacts_path   = (contacts_path_w if os.path.exists(contacts_path_w)
                           else contacts_path_s)
        raw = _load_json(contacts_path, {"contacts": [], "stories_row": []})
        self._contacts: list[dict] = raw.get("contacts", [])
        self._stories:  list[dict] = raw.get("stories_row", [])
        self._contacts_path = contacts_path_w

    # ---- config.json access ------------------------------------------------

    def get(self, key: str, default=None):
        return self.config.get(key, default)

    def set(self, key: str, value) -> None:
        self.config[key] = value
        self._flush_config()

    def _flush_config(self) -> None:
        _save_json(self._config_path, self.config)

    # ---- scenario access ---------------------------------------------------

    def get_scenarios(self) -> list[dict]:
        return self._scenarios

    def get_active_scenario(self) -> dict | None:
        active_id = self.config.get("active_scenario")
        for s in self._scenarios:
            if s["id"] == active_id:
                return s
        return self._scenarios[0] if self._scenarios else None

    def set_active_scenario(self, scenario_id: str) -> None:
        self.config["active_scenario"] = scenario_id
        self._flush_config()

    def reload_scenarios(self) -> None:
        """Re-scan the scenarios directory — call after adding/editing files."""
        self._scenarios = _load_scenarios_from_directory(
            self._scenarios_dir_active)
        logger.info("Scenarios reloaded: %d found.", len(self._scenarios))

    # ---- scenario file management (admin panel) ----------------------------

    def save_scenario_file(self, scenario: dict) -> bool:
        """Write a scenario dict to its own file in the writable scenarios dir."""
        os.makedirs(self._scenarios_dir, exist_ok=True)
        filename = f"{scenario['id']}.json"
        path = os.path.join(self._scenarios_dir, filename)
        success = _save_json(path, scenario)
        if success:
            self.reload_scenarios()
        return success

    def get_scenario_file_path(self, scenario_id: str) -> str:
        return os.path.join(self._scenarios_dir_active,
                            f"{scenario_id}.json")

    def update_scenario_hook(self, scenario_id: str, new_hook: str) -> None:
        for s in self._scenarios:
            if s["id"] == scenario_id:
                s["hook_message"] = new_hook
                self.save_scenario_file(s)
                return

    def add_scenario(self, scenario: dict) -> None:
        scenario.setdefault("_schema_version", "2.0")
        scenario.setdefault("enabled", True)
        self.save_scenario_file(scenario)

    # ---- fallback dialogue -------------------------------------------------

    def get_fallback_responses(self, scenario_id: str,
                               phase: int = 1) -> list[str]:
        for s in self._scenarios:
            if s["id"] == scenario_id:
                fb = s.get("fallback_dialogue", {})
                key = f"phase_{phase}"
                responses = fb.get(key, [])
                if responses:
                    return responses
                # Try any phase as last resort
                for k in fb:
                    if fb[k]:
                        return fb[k]
        return ["Please reply as soon as possible."]

    # ---- AI system prompts -------------------------------------------------

    def get_system_prompt(self, scenario_id: str, phase: int = 1) -> str:
        for s in self._scenarios:
            if s["id"] == scenario_id:
                prompts = s.get("ai_system_prompts", {})
                key = f"phase_{phase}"
                prompt = prompts.get(key, "")
                if prompt:
                    return prompt
        # Return a safe generic fallback
        return (f"You are roleplaying as {scenario_id}. "
                f"Stay in character. Phase {phase}. Never reveal you are an AI.")

    # ---- contacts access ---------------------------------------------------

    def get_contacts(self) -> list[dict]:
        """Return contacts sorted by list_position."""
        return sorted(self._contacts,
                      key=lambda c: c.get("list_position", 99))

    def get_contact_by_id(self, contact_id: str) -> dict | None:
        for c in self._contacts:
            if c.get("id") == contact_id:
                return c
        return None

    def get_stories(self) -> list[dict]:
        return self._stories

    def save_contacts(self, contacts: list[dict],
                      stories: list[dict] | None = None) -> bool:
        data = {
            "_schema_version": "2.0",
            "contacts": contacts,
            "stories_row": stories if stories is not None else self._stories,
        }
        success = _save_json(self._contacts_path, data)
        if success:
            self._contacts = contacts
            if stories is not None:
                self._stories = stories
        return success

    def add_contact(self, contact: dict) -> None:
        self._contacts.append(contact)
        self.save_contacts(self._contacts)

    def update_contact(self, contact_id: str, updates: dict) -> None:
        for c in self._contacts:
            if c.get("id") == contact_id:
                c.update(updates)
        self.save_contacts(self._contacts)

    def remove_contact(self, contact_id: str) -> None:
        self._contacts = [c for c in self._contacts
                          if c.get("id") != contact_id]
        self.save_contacts(self._contacts)

    def get_active_scam_contact(self) -> dict | None:
        """Return the contact linked to the active scenario."""
        active_id = self.config.get("active_scenario")
        for c in self._contacts:
            if c.get("scenario_id") == active_id:
                return c
        return None

    # ---- image cache -------------------------------------------------------

    def get_cached_avatar_path(self, scenario_id: str) -> str | None:
        """Return local path to cached avatar image, or None if not available."""
        cache_dir = get_writable_path("avatar_cache")
        path = os.path.join(cache_dir, f"{scenario_id}.png")
        return path if os.path.exists(path) else None

    async def download_avatar(self, scenario_id: str, url: str) -> str | None:
        """
        Download avatar image from *url* and cache it locally.
        Returns local path on success, None on failure.
        """
        if not url or not url.startswith("http"):
            return None
        try:
            import httpx
            cache_dir = get_writable_path("avatar_cache")
            os.makedirs(cache_dir, exist_ok=True)
            local_path = os.path.join(cache_dir, f"{scenario_id}.png")
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                response.raise_for_status()
                with open(local_path, "wb") as fh:
                    fh.write(response.content)
            logger.info("Avatar cached for %s at %s", scenario_id, local_path)
            return local_path
        except Exception as exc:
            logger.error("Avatar download failed for %s: %s", scenario_id, exc)
            return None


# Module-level singleton
config = AppConfig()