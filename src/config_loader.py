"""
config_loader.py — Android-safe configuration loader for SPICE.
"""

import json
import logging
import os

from path_utils import get_secure_path, get_writable_path
from defaults import DEFAULT_CONFIG, DEFAULT_MANIFEST

logger = logging.getLogger(__name__)


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


class AppConfig:

    def __init__(self) -> None:
        self._config_path   = get_writable_path("config.json")
        self._manifest_path = get_writable_path("message_manifest.json")

        source_config   = get_secure_path("config.json")
        source_manifest = get_secure_path("message_manifest.json")

        if os.path.exists(self._config_path):
            self.config = _load_json(self._config_path, DEFAULT_CONFIG.copy())
        else:
            self.config = _load_json(source_config, DEFAULT_CONFIG.copy())
            self._flush_config()

        if os.path.exists(self._manifest_path):
            self.manifest = _load_json(self._manifest_path, DEFAULT_MANIFEST.copy())
        else:
            self.manifest = _load_json(source_manifest, DEFAULT_MANIFEST.copy())
            _save_json(self._manifest_path, self.manifest)

        for key, val in DEFAULT_CONFIG.items():
            self.config.setdefault(key, val)

    # ---- config.json access ------------------------------------------------

    def get(self, key: str, default=None):
        return self.config.get(key, default)

    def set(self, key: str, value) -> None:
        self.config[key] = value
        self._flush_config()

    def _flush_config(self) -> None:
        _save_json(self._config_path, self.config)

    # ---- manifest access ---------------------------------------------------

    def get_scenarios(self) -> list:
        return self.manifest.get("scenarios", DEFAULT_MANIFEST["scenarios"])

    def get_active_scenario(self):
        active_id = self.config.get("active_scenario")
        for s in self.get_scenarios():
            if s["id"] == active_id:
                return s
        scenarios = self.get_scenarios()
        return scenarios[0] if scenarios else None

    def set_active_scenario(self, scenario_id: str) -> None:
        self.config["active_scenario"] = scenario_id
        self._flush_config()

    def update_manifest(self, new_manifest: dict) -> None:
        self.manifest = new_manifest
        _save_json(self._manifest_path, new_manifest)

    # ---- fallback dialogue -------------------------------------------------

    def get_fallback_responses(self, scenario_id: str) -> list:
        fb = self.config.get("fallback_responses", {})
        return fb.get(scenario_id, ["Please reply as soon as possible."])

    # ---- admin panel helpers -----------------------------------------------

    def add_scenario(self, scenario: dict) -> None:
        self.manifest.setdefault("scenarios", []).append(scenario)
        _save_json(self._manifest_path, self.manifest)

    def update_scenario_hook(self, scenario_id: str, new_hook: str) -> None:
        for s in self.manifest.get("scenarios", []):
            if s["id"] == scenario_id:
                s["initial_hook_message"] = new_hook
        _save_json(self._manifest_path, self.manifest)


# Module-level singleton
config = AppConfig()