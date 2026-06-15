"""
path_utils.py — Android-safe file system resolution for SPICE.

On Android, assets live inside the APK sandbox. Standard Path(__file__).parent
calls fail silently or raise FileNotFoundError. This module provides a single
get_secure_path() helper that resolves correctly in both environments.
"""

import os
import sys

def get_secure_path(filename: str) -> str:
    """
    Return the absolute path to `filename` relative to the app's asset root.
    Works perfectly on both desktop (dev) and compiled serious_python Android APKs.
    """
    # Check if we are running inside the Android Python environment
    # serious_python stores the extracted script assets here
    android_app_dir = os.environ.get("PYTHONHOME") or os.environ.get("APP_DATA_DIR")

    if android_app_dir:
        # We are on Android! Look directly in the extracted asset directory
        base_path = android_app_dir
    elif getattr(sys, "frozen", False):
        # Desktop packaged bundle fallback
        base_path = os.path.dirname(sys.executable)
    else:
        # Standard desktop development mode
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, filename)


def get_writable_path(filename: str) -> str:
    """
    Return a path inside the app's writable data directory.
    Ensures state can be saved without hitting Android read-only permissions.
    """
    # Look for Flet's custom app storage environment variable on mobile
    storage = os.environ.get("FLET_APP_STORAGE_DATA")
    if storage:
        return os.path.join(storage, filename)

    # Fallback to the secure asset path if not explicitly separated
    return get_secure_path(filename)