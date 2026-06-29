"""
notification_channel.py
Registers the Android Notification Channel required by API 26+.
Import this at the top of main.py before any notification is fired.
"""
import sys
import logging

logger = logging.getLogger(__name__)

CHANNEL_ID   = "spice_simulation_channel"
CHANNEL_NAME = "Simulation Messages"

def register_channel():
    """
    Call once at app startup. Safe no-op on desktop.
    Creates the notification channel that the OS requires before
    any notification can appear outside the app on Android 8+.
    """
    if not getattr(sys, 'frozen', False):
        logger.info("register_channel: desktop mode, skipping")
        return

    try:
        from jnius import autoclass

        NotificationChannel = autoclass(
            'android.app.NotificationChannel')
        NotificationManager = autoclass(
            'android.app.NotificationManager')
        PythonActivity = autoclass(
            'org.kivy.android.PythonActivity')

        IMPORTANCE_HIGH = 4   # NotificationManager.IMPORTANCE_HIGH

        channel = NotificationChannel(
            CHANNEL_ID,
            CHANNEL_NAME,
            IMPORTANCE_HIGH
        )
        channel.setDescription("Delivers simulation scenario messages")
        channel.enableVibration(True)
        channel.enableLights(True)

        context = PythonActivity.mActivity
        manager = context.getSystemService(
            NotificationManager._class.getName())
        manager.createNotificationChannel(channel)

        logger.info("Notification channel registered: %s", CHANNEL_ID)

    except Exception as ex:
        logger.warning("register_channel failed: %s", ex)
        # App continues — in-app bold thread still works as fallback