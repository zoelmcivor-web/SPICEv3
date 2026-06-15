"""
telemetry.py — Behavioral telemetry engine for SPICE.

Requirements addressed: 3, 6, 7, 14, 16.

IRB COMPLIANCE:
  Raw personal data (phone numbers, SSNs, bank accounts, passwords, etc.)
  is detected via regex patterns and IMMEDIATELY discarded.  Only the
  metadata category label is written to the log.  No actual PII ever
  touches telemetry_log.csv.
"""

import csv
import logging
import os
import re
import threading
from datetime import datetime, timezone

from path_utils import get_writable_path

logger = logging.getLogger(__name__)

LOG_FILE = "telemetry_log.csv"

# Absolute column schema (Requirement 16)
CSV_COLUMNS = [
    "Timestamp",
    "Participant_ID",
    "Active_Scenario_Type",
    "Event_Type",
    "Latency_ms",
    "Data_Exposure_Category",
    "Interaction_Count",
]

# ---------------------------------------------------------------------------
# PII detection patterns  (Requirement 6)
# ---------------------------------------------------------------------------
_PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("SSN",          re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b")),
    ("PHONE_NUMBER", re.compile(r"\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    ("BANK_ACCOUNT_NUMBER", re.compile(r"\b\d{8,17}\b")),
    ("CREDIT_CARD", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    ("EMAIL_ADDRESS", re.compile(r"\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b", re.I)),
    ("PASSWORD",     re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*\S+")),
    ("ROUTING_NUMBER", re.compile(r"\b\d{9}\b")),
    ("ZIP_CODE",     re.compile(r"\b\d{5}(?:-\d{4})?\b")),
    ("ADDRESS",      re.compile(
        r"\b\d{1,5}\s+\w[\w\s]{2,30}(street|st|avenue|ave|road|rd|blvd|drive|dr|lane|ln|way|court|ct|place|pl)\b",
        re.I
    )),
]


def scrub_message(text: str) -> tuple[str, str | None]:
    """
    Scan *text* for PII patterns.
    Returns (cleaned_placeholder, category_label | None).
    If PII is found, the raw text is discarded and ONLY the label is returned.
    """
    for category, pattern in _PII_PATTERNS:
        if pattern.search(text):
            logger.info("PII detected and scrubbed: %s", category)
            return f"[DATA_COMPROMISE: {category}]", category
    return text, None


# ---------------------------------------------------------------------------
# Telemetry writer
# ---------------------------------------------------------------------------

class TelemetryLogger:
    """
    Thread-safe CSV telemetry logger.
    All writes are performed on a background thread so the UI never blocks.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._path = get_writable_path(LOG_FILE)
        self._interaction_count = 0
        self._ensure_csv()

    def _ensure_csv(self) -> None:
        """Create the CSV file with headers if it doesn't exist yet."""
        try:
            if not os.path.exists(self._path):
                with open(self._path, "w", newline="", encoding="utf-8") as fh:
                    writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
                    writer.writeheader()
        except Exception as exc:  # noqa: BLE001
            logger.error("Could not initialise telemetry CSV: %s", exc)

    def log(
        self,
        participant_id: str,
        scenario_type: str,
        event_type: str,
        latency_ms: float = 0.0,
        data_exposure_category: str = "None",
    ) -> None:
        """Append one row to telemetry_log.csv (non-blocking)."""
        self._interaction_count += 1
        row = {
            "Timestamp": datetime.now(timezone.utc).isoformat(),
            "Participant_ID": participant_id,
            "Active_Scenario_Type": scenario_type,
            "Event_Type": event_type,
            "Latency_ms": round(latency_ms, 2),
            "Data_Exposure_Category": data_exposure_category,
            "Interaction_Count": self._interaction_count,
        }
        thread = threading.Thread(target=self._write_row, args=(row,), daemon=True)
        thread.start()

    def _write_row(self, row: dict) -> None:
        try:
            with self._lock:
                with open(self._path, "a", newline="", encoding="utf-8") as fh:
                    writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
                    writer.writerow(row)
        except Exception as exc:  # noqa: BLE001
            logger.error("Telemetry write failed: %s", exc)


# Module-level singleton
telemetry = TelemetryLogger()
