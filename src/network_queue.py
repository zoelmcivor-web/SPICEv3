"""
network_queue.py — Fault-tolerant offline telemetry queue for SPICE.

Requirement 10: Events triggered while the device is offline are queued
locally and flushed automatically once connectivity is restored.
"""

import asyncio
import json
import logging
import os
import time

from path_utils import get_writable_path

logger = logging.getLogger(__name__)
QUEUE_FILE = "offline_queue.json"


def _queue_path() -> str:
    return get_writable_path(QUEUE_FILE)


def _load_queue() -> list:
    path = _queue_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return []


def _save_queue(queue: list) -> None:
    try:
        with open(_queue_path(), "w", encoding="utf-8") as fh:
            json.dump(queue, fh, indent=2)
    except Exception as exc:  # noqa: BLE001
        logger.error("Queue save failed: %s", exc)


def enqueue_event(event: dict) -> None:
    """Push an event dict onto the persistent offline queue."""
    queue = _load_queue()
    event["queued_at"] = time.time()
    queue.append(event)
    _save_queue(queue)
    logger.info("Event queued offline: %s", event.get("Event_Type"))


def get_queue_depth() -> int:
    return len(_load_queue())


async def flush_queue(telemetry_logger) -> int:
    """
    Attempt to flush all queued events through *telemetry_logger*.
    Returns the number of events successfully flushed.
    Clears the queue file on success.
    """
    queue = _load_queue()
    if not queue:
        return 0

    flushed = 0
    for event in queue:
        try:
            telemetry_logger.log(
                participant_id=event.get("Participant_ID", "UNKNOWN"),
                scenario_type=event.get("Active_Scenario_Type", "UNKNOWN"),
                event_type=event.get("Event_Type", "Queued_Event"),
                latency_ms=event.get("Latency_ms", 0.0),
                data_exposure_category=event.get("Data_Exposure_Category", "None"),
            )
            flushed += 1
            await asyncio.sleep(0)   # yield to event loop between rows
        except Exception as exc:  # noqa: BLE001
            logger.error("Flush failed for event: %s — %s", event, exc)

    if flushed == len(queue):
        _save_queue([])
        logger.info("Offline queue flushed (%d events).", flushed)
    else:
        remaining = queue[flushed:]
        _save_queue(remaining)
        logger.warning("Partial flush: %d remaining.", len(remaining))

    return flushed
