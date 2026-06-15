"""
main.py — SPICE Android App Entry Point (v4)

Flet 0.85.3 padding/margin/border_radius API:
  ONLY direct class constructors work:
    ft.Padding(left, top, right, bottom)
    ft.Margin(left, top, right, bottom)
    ft.BorderRadius(top_left, top_right, bottom_left, bottom_right)
  ft.padding.all(), ft.padding.only(), ft.padding.symmetric() ALL fail.
  ft.border_radius.all() also fails.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

import flet as ft

from path_utils import get_secure_path, get_writable_path

try:
    from config_loader import config
except Exception as _e:
    logging.critical("config_loader failed: %s", _e)
    class _BareCfg:
        def get(self, k, d=None): return d
        def get_active_scenario(self): return None
        def get_fallback_responses(self, s): return ["Please reply."]
        def get_scenarios(self): return []
        def set(self, k, v): pass
        def set_active_scenario(self, s): pass
        def update_scenario_hook(self, s, h): pass
        def add_scenario(self, s): pass
    config = _BareCfg()  # type: ignore

try:
    from participant import profile_exists, load_profile, save_profile
except Exception as _e:
    logging.critical("participant module failed: %s", _e)
    def profile_exists(): return False  # type: ignore
    def load_profile(): return {}  # type: ignore
    def save_profile(f, l): return {"participant_id": "UNKNOWN", "first_name": f, "last_name": l}  # type: ignore

try:
    from telemetry import telemetry, scrub_message
except Exception as _e:
    logging.critical("telemetry module failed: %s", _e)
    class _BareTelemetry:
        def log(self, **kw): pass
    telemetry = _BareTelemetry()  # type: ignore
    def scrub_message(t): return t, None  # type: ignore

try:
    from session import save_session, load_session
except Exception as _e:
    logging.critical("session module failed: %s", _e)
    def save_session(*a, **kw): pass  # type: ignore
    def load_session(): return None  # type: ignore

try:
    from ai_engine import ChatEngine
except Exception as _e:
    logging.critical("ai_engine module failed: %s", _e)
    ChatEngine = None  # type: ignore

try:
    from network_queue import enqueue_event, flush_queue, get_queue_depth
except Exception as _e:
    logging.critical("network_queue module failed: %s", _e)
    def enqueue_event(e): pass  # type: ignore
    async def flush_queue(t): return 0  # type: ignore
    def get_queue_depth(): return 0  # type: ignore

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")

FB_BLUE       = "#1877F2"
FB_DARK       = "#1C1E21"
FB_BG         = "#F0F2F5"
FB_WHITE      = "#FFFFFF"
FB_GRAY       = "#65676B"
FB_LIGHT_GRAY = "#E4E6EB"
FB_TEXT       = "#050505"
FB_MESSENGER  = "#0084FF"

# ---------------------------------------------------------------------------
# Padding/Margin/BorderRadius helpers for Flet 0.85.3
# Only ft.Padding(), ft.Margin(), ft.BorderRadius() constructors work.
# ---------------------------------------------------------------------------
def _pad(left=0, right=0, top=0, bottom=0):
    return ft.Padding(left=left, top=top, right=right, bottom=bottom)

def _pad_all(v):
    return ft.Padding(left=v, top=v, right=v, bottom=v)

def _pad_xy(h=0, v=0):
    return ft.Padding(left=h, top=v, right=h, bottom=v)

def _mar(left=0, right=0, top=0, bottom=0):
    return ft.Margin(left=left, top=top, right=right, bottom=bottom)

def _br_all(v):
    return ft.BorderRadius(top_left=v, top_right=v, bottom_left=v, bottom_right=v)

# ---------------------------------------------------------------------------
# Global mutable state
# ---------------------------------------------------------------------------
_participant_profile: dict = {}
_chat_engine = None
_interaction_count: int = 0
_notification_render_time: float = 0.0
_message_render_time: float = 0.0
_admin_tap_count: int = 0
_font_scale: float = 1.0
_offline_mode: bool = False
_app_route: str = "boot"


def _pid() -> str:
    return _participant_profile.get("participant_id", "UNKNOWN")


def _active_scenario() -> dict:
    s = config.get_active_scenario()
    if s is None:
        return {
            "id": "family_impersonation",
            "threat_vector_classification": "Family_Impersonation",
            "sender_identity": {"display_name": "Alex (New Number)",
                                "profile_picture_asset": ""},
            "simulated_timestamp": "Just Now",
            "initial_hook_message": "Hey, it's me. I need your help urgently.",
            "evaluation_rule": "EMOTIONAL_IMPERSONATION_ENGAGEMENT",
        }
    return s


def _make_chat_engine():
    if ChatEngine is None:
        return None
    return ChatEngine(scenario=_active_scenario(),
                      participant_id=_pid(),
                      api_key=ANTHROPIC_API_KEY)


def _scaled(size: int) -> int:
    return int(size * _font_scale)


def _avatar(initial: str = "?", size: int = 40) -> ft.Container:
    return ft.Container(
        content=ft.Text(initial.upper(), color=FB_WHITE,
                        size=_scaled(14), weight=ft.FontWeight.BOLD),
        width=size, height=size,
        bgcolor=FB_BLUE,
        border_radius=size // 2,
        alignment=ft.Alignment(0, 0),
    )


# ===========================================================================
# VIEW BUILDERS
# ===========================================================================

def _error_view(msg: str) -> ft.Column:
    return ft.Column([
        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.ORANGE_700, size=64),
        ft.Text("Configuration Error", size=22, weight=ft.FontWeight.BOLD, color=FB_DARK),
        ft.Text("Please contact your research coordinator.",
                size=16, color=FB_GRAY, text_align=ft.TextAlign.CENTER),
        ft.Text(msg, size=11, color=FB_GRAY, italic=True,
                text_align=ft.TextAlign.CENTER, selectable=True),
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER, spacing=16, expand=True)


def _build_registration(page: ft.Page, on_complete) -> ft.Column:
    first_f = ft.TextField(
        label="First Name", text_size=_scaled(16),
        border_color=FB_BLUE, focused_border_color=FB_BLUE,
        content_padding=_pad(left=16, right=16, top=14, bottom=14))
    last_f = ft.TextField(
        label="Last Name", text_size=_scaled(16),
        border_color=FB_BLUE, focused_border_color=FB_BLUE,
        content_padding=_pad(left=16, right=16, top=14, bottom=14))
    err_lbl = ft.Text("", color=ft.Colors.RED_600, size=_scaled(13))

    def submit(e):
        if not (first_f.value or "").strip() or not (last_f.value or "").strip():
            err_lbl.value = "Please enter both first and last name."
            page.update()
            return
        global _participant_profile
        _participant_profile = save_profile(first_f.value, last_f.value)
        on_complete()

    return ft.Column([
        ft.Container(height=60),
        ft.Icon(ft.Icons.CONNECT_WITHOUT_CONTACT, size=72, color=FB_BLUE),
        ft.Text("Social Connect+ Assistant", size=_scaled(24),
                weight=ft.FontWeight.BOLD, color=FB_DARK),
        ft.Container(
            content=ft.Text(
                "Welcome to the 30-day mobile engagement\nand user experience layout evaluation.",
                size=_scaled(14), color=FB_GRAY, text_align=ft.TextAlign.CENTER),
            padding=_pad(left=24, right=24)),
        ft.Container(height=16),
        ft.Container(
            content=ft.Column([first_f, last_f, err_lbl], spacing=12),
            padding=_pad(left=32, right=32)),
        ft.Container(height=8),
        ft.ElevatedButton(
            "Begin Evaluation", on_click=submit,
            bgcolor=FB_BLUE, color=FB_WHITE,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            width=260, height=50),
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.START, spacing=12,
        expand=True, scroll=ft.ScrollMode.AUTO)


def _build_feed(page: ft.Page, on_notif_click) -> ft.Column:
    global _notification_render_time, _admin_tap_count
    _notification_render_time = time.time() * 1000

    scenario    = _active_scenario()
    sender      = scenario["sender_identity"]["display_name"]
    hook        = scenario["initial_hook_message"]
    admin_limit = config.get("admin_gesture_tap_count", 7)

    def logo_tap(e):
        global _admin_tap_count
        _admin_tap_count += 1
        if _admin_tap_count >= admin_limit:
            _admin_tap_count = 0
            _go(page, "admin")

    def notif_click(e):
        latency = time.time() * 1000 - _notification_render_time
        telemetry.log(participant_id=_pid(),
                      scenario_type=scenario["threat_vector_classification"],
                      event_type="Notification_Click",
                      latency_ms=latency)
        on_notif_click()

    nav = ft.Container(
        content=ft.Row([
            ft.GestureDetector(
                content=ft.Text("facebook", color=FB_BLUE, size=_scaled(24),
                                weight=ft.FontWeight.BOLD),
                on_tap=logo_tap),
            ft.Row([
                ft.Container(content=ft.Icon(ft.Icons.SEARCH, color=FB_DARK, size=22),
                             bgcolor=FB_LIGHT_GRAY, border_radius=20, padding=8),
                ft.Container(content=ft.Icon(ft.Icons.MESSAGE_OUTLINED, color=FB_DARK, size=22),
                             bgcolor=FB_LIGHT_GRAY, border_radius=20, padding=8,
                             on_click=notif_click),
            ], spacing=8),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        bgcolor=FB_WHITE,
        padding=_pad(left=16, right=16, top=44, bottom=10),
        shadow=ft.BoxShadow(blur_radius=4, color="#22000000", offset=ft.Offset(0, 2)))

    banner = ft.Container(
        content=ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.MESSAGE, color=FB_MESSENGER, size=28),
                ft.Column([
                    ft.Text(sender, weight=ft.FontWeight.BOLD,
                            size=_scaled(14), color=FB_TEXT),
                    ft.Text((hook[:55] + "…") if len(hook) > 55 else hook,
                            size=_scaled(12), color=FB_GRAY, max_lines=1),
                ], spacing=2, expand=True),
            ], spacing=12),
            padding=_pad_all(12), bgcolor=FB_WHITE, border_radius=12,
            shadow=ft.BoxShadow(blur_radius=8, color="#33000000", offset=ft.Offset(0, 2)),
            on_click=notif_click),
        padding=_pad(left=12, right=12, top=6, bottom=6))

    # Large rotating pool — picks 5 different posts each time feed loads
    import random as _random
    _ALL_POSTS = [
        ("Community Events",    "Join us this Saturday for the Farmers Market! 🌽", 142, 18),
        ("Local News",          "Road closure on Main St this weekend due to utility work.", 38, 5),
        ("Health & Wellness",   "Free flu shots available at the community center this Friday.", 201, 31),
        ("Neighborhood Watch",  "Friendly reminder to lock your vehicles at night. 🔒", 94, 12),
        ("Senior Center",       "Bingo night this Thursday! Doors open at 6pm. All welcome. 🎉", 211, 24),
        ("Community Garden",    "Tomatoes are ready! Stop by the garden on Oak Street to pick some up. 🍅", 87, 9),
        ("Local Library",       "New large-print book club starting next month. Sign up at the front desk.", 63, 7),
        ("Meals on Wheels",     "Volunteers needed for Tuesday and Thursday delivery routes this month.", 155, 22),
        ("Weather Update",      "Temperatures dropping this weekend — stay warm and check on neighbors! 🌨️", 178, 14),
        ("Parks & Recreation",  "The walking trail at Riverside Park has been repaved. Great time for a stroll!", 99, 11),
        ("Fire Department",     "Reminder: test your smoke detectors and replace batteries twice a year. 🔥", 320, 41),
        ("Local Church",        "Annual potluck dinner Sunday after service. Bring a dish to share! 🍽️", 134, 19),
        ("Animal Shelter",      "Three golden retrievers looking for forever homes this week. Come meet them! 🐶", 412, 67),
        ("Community Theater",   "Tickets still available for this weekend's production of Oklahoma! 🎭", 76, 8),
        ("Town Hall",           "Public meeting on proposed park improvements next Tuesday at 7pm.", 45, 6),
        ("Senior Services",     "Free tax preparation assistance available every Wednesday through April.", 88, 13),
        ("Health Dept",         "Reminder: Medicare open enrollment ends soon. Call 1-800-MEDICARE for help.", 102, 9),
        ("Book Club",           "This month we're reading 'The Thursday Murder Club.' New members welcome!", 71, 15),
        ("Community Pool",      "Senior swim hours extended to 8am-10am daily starting next week. 🏊", 93, 10),
        ("Neighborhood Assoc",  "Street sweeping scheduled for next Monday morning. Please move vehicles.", 56, 4),
    ]
    _random.shuffle(_ALL_POSTS)
    _selected_posts = _ALL_POSTS[:5]

    def _card(author, text, likes, comments):
        return ft.Container(
            content=ft.Column([
                ft.Row([_avatar(author[0]), ft.Column([
                    ft.Text(author, weight=ft.FontWeight.BOLD,
                            size=_scaled(14), color=FB_TEXT),
                    ft.Text("Just now", size=_scaled(11), color=FB_GRAY),
                ], spacing=1)], spacing=10),
                ft.Text(text, size=_scaled(14), color=FB_TEXT),
                ft.Divider(height=1, color=FB_LIGHT_GRAY),
                ft.Row([
                    ft.TextButton(f"👍 {likes}", style=ft.ButtonStyle(color=FB_GRAY)),
                    ft.TextButton(f"💬 {comments}", style=ft.ButtonStyle(color=FB_GRAY)),
                    ft.TextButton("↗ Share", style=ft.ButtonStyle(color=FB_GRAY)),
                ]),
            ], spacing=8),
            bgcolor=FB_WHITE, border_radius=8, padding=_pad_all(14),
            margin=_mar(top=4, bottom=4))

    feed = ft.ListView(
        [_card(a, t, l, c) for a, t, l, c in _selected_posts],
        expand=True, spacing=0,
        padding=_pad(left=8, right=8, top=4, bottom=4))

    return ft.Column([nav, banner, feed], spacing=0, expand=True)


def _build_chat(page: ft.Page, on_back) -> ft.Column:
    global _chat_engine, _interaction_count, _message_render_time

    scenario = _active_scenario()
    sender   = scenario["sender_identity"]["display_name"]

    # Create engine if needed
    if _chat_engine is None:
        _chat_engine = _make_chat_engine()
    if _chat_engine is None:
        return _error_view("Chat engine unavailable.")

    # Restore from session if returning to chat
    saved = load_session()
    if saved and saved.get("active_scenario_id") == scenario["id"]:
        _chat_engine.import_state({
            "history":    saved.get("conversation_history", []),
            "phase":      saved.get("current_phase", 1),
            "turn_count": saved.get("interaction_count", 0),
        })

    msgs_col = ft.ListView(
        expand=True, spacing=6,
        padding=_pad(left=10, right=10, top=10, bottom=10),
        auto_scroll=True)

    input_f = ft.TextField(
        hint_text="Aa",
        border_color=FB_LIGHT_GRAY, bgcolor=FB_LIGHT_GRAY,
        border_radius=24, text_size=_scaled(15),
        content_padding=_pad(left=16, right=16, top=12, bottom=12),
        expand=True, multiline=False)

    status_t = ft.Text("", size=_scaled(11), color=FB_GRAY, italic=True)

    _focus_t   = [0.0]
    _compose_t = [0.0]
    _prev_len  = [0]

    def on_focus(e):
        _focus_t[0] = time.time() * 1000
        telemetry.log(participant_id=_pid(),
                      scenario_type=scenario["threat_vector_classification"],
                      event_type="Input_Field_Focus",
                      latency_ms=_focus_t[0] - _message_render_time)

    def on_change(e):
        if _compose_t[0] == 0.0:
            _compose_t[0] = time.time() * 1000
        cur = len(e.control.value or "")
        if cur < _prev_len[0] > 0:
            telemetry.log(participant_id=_pid(),
                          scenario_type=scenario["threat_vector_classification"],
                          event_type="Cognitive_Revision", latency_ms=0)
        _prev_len[0] = cur

    input_f.on_focus  = on_focus
    input_f.on_change = on_change

    def _bubble(text: str, user: bool):
        """Add a word-wrapping message bubble constrained to ~75% screen width."""
        # Spacer pushes bubble to correct side and limits its width to ~75%
        spacer = ft.Container(expand=1)
        bubble = ft.Container(
            content=ft.Text(
                text,
                size=_scaled(15),
                color=FB_WHITE if user else FB_TEXT,
                no_wrap=False,
            ),
            bgcolor=FB_MESSENGER if user else FB_WHITE,
            border_radius=_br_all(20),
            padding=_pad(left=14, right=14, top=10, bottom=10),
            expand=3,  # bubble takes 3/4 of row width
            shadow=ft.BoxShadow(blur_radius=2, color="#18000000",
                                offset=ft.Offset(0, 1)) if not user else None,
        )
        if user:
            row_controls = [spacer, bubble]
        else:
            row_controls = [bubble, spacer]

        msgs_col.controls.append(
            ft.Row(row_controls, spacing=4,
                   vertical_alignment=ft.CrossAxisAlignment.START))
        page.update()

    async def _send_async(user_text: str):
        global _interaction_count, _message_render_time

        compose_ms = 0.0
        if _compose_t[0] > 0:
            compose_ms = time.time() * 1000 - _compose_t[0]
            _compose_t[0] = 0.0
        _prev_len[0] = 0

        _interaction_count += 1
        telemetry.log(participant_id=_pid(),
                      scenario_type=scenario["threat_vector_classification"],
                      event_type="Message_Sent", latency_ms=compose_ms)

        if _offline_mode:
            enqueue_event({"Participant_ID": _pid(),
                           "Active_Scenario_Type": scenario["threat_vector_classification"],
                           "Event_Type": "Message_Sent_Offline",
                           "Latency_ms": compose_ms,
                           "Data_Exposure_Category": "None"})
            status_t.value = "Sending…"
            page.update()
            return

        _bubble(user_text, user=True)
        status_t.value = "typing…"
        page.update()

        ai_reply, exposure_cat = await _chat_engine.send_message(user_text)

        status_t.value = ""
        _message_render_time = time.time() * 1000
        _bubble(ai_reply, user=False)

        save_session(active_scenario_id=scenario["id"],
                     conversation_history=_chat_engine.history,
                     accumulated_latency_ms=compose_ms,
                     interaction_count=_interaction_count,
                     current_phase=_chat_engine.phase)

    def on_send(e):
        text = (input_f.value or "").strip()
        if not text:
            return
        input_f.value = ""
        page.update()
        page.run_task(_send_async, text)

    input_f.on_submit = on_send

    send_btn = ft.IconButton(
        ft.Icons.SEND_ROUNDED,
        icon_color=FB_MESSENGER,
        icon_size=26,
        on_click=on_send)

    header = ft.Container(
        content=ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK,
                          on_click=lambda e: on_back(),
                          icon_color=FB_DARK, icon_size=26),
            _avatar(sender[0] if sender else "?", size=36),
            ft.Column([
                ft.Text(sender, weight=ft.FontWeight.BOLD,
                        size=_scaled(15), color=FB_TEXT),
                ft.Text("Active now", size=_scaled(12),
                        color=ft.Colors.GREEN_600),
            ], spacing=0, expand=True),
        ], spacing=8),
        bgcolor=FB_WHITE,
        padding=_pad(left=4, right=8, top=44, bottom=8),
        shadow=ft.BoxShadow(blur_radius=3, color="#22000000",
                            offset=ft.Offset(0, 2)))

    # Render full conversation history (so going back and returning works)
    if not _chat_engine.history:
        # Fresh conversation — show the hook
        hook = scenario.get("initial_hook_message", "Hello.")
        _chat_engine.history.append({"role": "assistant", "content": hook})
        _message_render_time = time.time() * 1000
        _bubble(hook, user=False)
        telemetry.log(participant_id=_pid(),
                      scenario_type=scenario["threat_vector_classification"],
                      event_type="Scenario_Hook_Rendered")
    else:
        # Returning to chat — rebuild bubbles from history
        for msg in _chat_engine.history:
            _bubble(msg["content"], user=(msg["role"] == "user"))

    bottom = ft.Container(
        content=ft.Column([
            status_t,
            ft.Row([input_f, send_btn], spacing=4),
        ], spacing=2),
        bgcolor=FB_WHITE,
        padding=_pad(left=10, right=10, top=8, bottom=24),
        shadow=ft.BoxShadow(blur_radius=4, color="#22000000",
                            offset=ft.Offset(0, -2)))

    return ft.Column([header, msgs_col, bottom], spacing=0, expand=True)


def _build_admin(page: ft.Page, on_close) -> ft.Column:
    import csv
    import shutil
    from datetime import datetime

    # ---- shared status label ----
    status_l = ft.Text("", color=ft.Colors.GREEN_700, size=_scaled(13))

    # ---- scenario config controls ----
    scenarios = config.get_scenarios()
    active_dd = ft.Dropdown(
        label="Active Scenario",
        options=[ft.dropdown.Option(s["id"], s["id"]) for s in scenarios],
        value=config.get("active_scenario"),
        border_color=FB_BLUE)
    hook_f       = ft.TextField(label="Edit Hook Message", multiline=True,
                                min_lines=3, max_lines=6,
                                border_color=FB_BLUE, text_size=_scaled(14))
    new_id_f     = ft.TextField(label="New Scenario ID",   border_color=FB_BLUE, text_size=_scaled(14))
    new_hook_f   = ft.TextField(label="New Hook Message",  border_color=FB_BLUE, text_size=_scaled(14),
                                multiline=True, min_lines=2)
    new_sender_f = ft.TextField(label="Sender Name",       border_color=FB_BLUE, text_size=_scaled(14))

    def save_active(e):
        global _chat_engine
        config.set_active_scenario(active_dd.value or "")
        if (hook_f.value or "").strip():
            config.update_scenario_hook(active_dd.value or "", hook_f.value.strip())
        # Reset chat engine so new scenario starts fresh with correct messages
        _chat_engine = None
        try:
            from session import clear_session
            clear_session()
        except Exception:
            pass
        status_l.value = "✓ Saved. Chat reset for new scenario."
        page.update()

    def add_new(e):
        if not (new_id_f.value or "").strip():
            status_l.value = "Scenario ID required."
            page.update()
            return
        config.add_scenario({
            "id": new_id_f.value.strip(),
            "threat_vector_classification": "Custom",
            "sender_identity": {"display_name": (new_sender_f.value or "").strip(),
                                "profile_picture_asset": ""},
            "simulated_timestamp": "Just Now",
            "initial_hook_message": (new_hook_f.value or "").strip(),
            "phase_thresholds": {"rapport_turns": 2, "urgency_turns": 2},
            "evaluation_rule": "CUSTOM",
        })
        status_l.value = f"✓ Scenario '{new_id_f.value.strip()}' added."
        page.update()

    # ---- data summary ----
    summary_col = ft.Column([], spacing=4)

    def _load_summary():
        summary_col.controls.clear()
        # Participant info
        profile = load_profile()
        pid   = profile.get("participant_id", "None")
        fname = profile.get("first_name", "—")
        lname = profile.get("last_name", "—")
        summary_col.controls.append(
            ft.Text(f"Participant: {fname} {lname}  (ID: {pid})",
                    size=_scaled(13), color=FB_DARK, weight=ft.FontWeight.BOLD))

        # Telemetry stats
        log_path = get_writable_path("telemetry_log.csv")
        total_rows = 0
        exposure_count = 0
        event_counts = {}
        last_rows = []
        try:
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8") as fh:
                    reader = csv.DictReader(fh)
                    for row in reader:
                        total_rows += 1
                        ev = row.get("Event_Type", "Unknown")
                        event_counts[ev] = event_counts.get(ev, 0) + 1
                        if row.get("Data_Exposure_Category", "None") != "None":
                            exposure_count += 1
                        last_rows.append(row)
                last_rows = last_rows[-5:]  # keep last 5
        except Exception as ex:
            summary_col.controls.append(
                ft.Text(f"Log read error: {ex}", size=11, color=ft.Colors.RED_600))

        summary_col.controls.append(
            ft.Text(f"Total logged events: {total_rows}",
                    size=_scaled(13), color=FB_GRAY))
        summary_col.controls.append(
            ft.Text(f"Data exposure alerts: {exposure_count}",
                    size=_scaled(13),
                    color=ft.Colors.RED_600 if exposure_count > 0 else FB_GRAY))
        for ev, count in event_counts.items():
            summary_col.controls.append(
                ft.Text(f"  {ev}: {count}", size=_scaled(12), color=FB_GRAY))

        if last_rows:
            summary_col.controls.append(ft.Divider())
            summary_col.controls.append(
                ft.Text("Last 5 events:", size=_scaled(12),
                        weight=ft.FontWeight.BOLD, color=FB_DARK))
            for row in last_rows:
                ts  = row.get("Timestamp", "")[:19].replace("T", " ")
                ev  = row.get("Event_Type", "")
                lat = row.get("Latency_ms", "0")
                exp = row.get("Data_Exposure_Category", "None")
                line = f"{ts}  {ev}  {lat}ms"
                if exp != "None":
                    line += f"  ⚠ {exp}"
                summary_col.controls.append(
                    ft.Text(line, size=10, color=FB_GRAY, selectable=True))

        page.update()

    def refresh_summary(e):
        _load_summary()
        status_l.value = "✓ Summary refreshed."
        page.update()

    # ---- export to Downloads ----
    def export_data(e):
        log_path     = get_writable_path("telemetry_log.csv")
        profile_path = get_writable_path("participant_profile.json")
        session_path = get_writable_path("session_state.json")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pid = load_profile().get("participant_id", "UNKNOWN")

        try:
            downloads = "/storage/emulated/0/Download"
            os.makedirs(downloads, exist_ok=True)
            exported = []

            if os.path.exists(log_path):
                dest = os.path.join(downloads, f"spice_telemetry_{pid}_{timestamp}.csv")
                shutil.copy2(log_path, dest)
                exported.append("telemetry_log.csv")

            if os.path.exists(profile_path):
                dest = os.path.join(downloads, f"spice_profile_{pid}_{timestamp}.json")
                shutil.copy2(profile_path, dest)
                exported.append("participant_profile.json")

            if os.path.exists(session_path):
                dest = os.path.join(downloads, f"spice_session_{pid}_{timestamp}.json")
                shutil.copy2(session_path, dest)
                exported.append("session_state.json")

            if exported:
                status_l.value = f"✓ Exported to Downloads: {', '.join(exported)}"
            else:
                status_l.value = "No data files found to export yet."
        except Exception as ex:
            status_l.value = f"Export failed: {ex}"
        page.update()

    # ---- reset participant (for next participant) ----
    def reset_participant(e):
        try:
            for fname in ["participant_profile.json", "telemetry_log.csv",
                          "session_state.json", "offline_queue.json"]:
                path = get_writable_path(fname)
                if os.path.exists(path):
                    os.remove(path)
            global _participant_profile, _chat_engine, _interaction_count, _app_route
            _participant_profile = {}
            _chat_engine = None
            _interaction_count = 0
            _app_route = "boot"
            status_l.value = "✓ Participant data cleared. Ready for next participant."
            _load_summary()
        except Exception as ex:
            status_l.value = f"Reset failed: {ex}"
        page.update()

    # Load summary on open
    _load_summary()

    # ---- layout ----
    return ft.Column([
        # Header
        ft.Container(
            content=ft.Row([
                ft.Text("SPICE Admin Panel", size=_scaled(18),
                        weight=ft.FontWeight.BOLD, color=FB_DARK),
                ft.IconButton(ft.Icons.CLOSE, on_click=lambda e: on_close()),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            bgcolor=FB_LIGHT_GRAY,
            padding=_pad(left=16, right=16, top=44, bottom=10)),

        ft.Container(
            content=ft.Column([

                # ── DATA SECTION ──────────────────────────────────────────
                ft.Text("Participant Data", size=_scaled(15),
                        weight=ft.FontWeight.BOLD, color=FB_DARK),
                summary_col,
                ft.Row([
                    ft.ElevatedButton(
                        "Refresh Summary",
                        on_click=refresh_summary,
                        bgcolor=FB_BLUE, color=FB_WHITE),
                    ft.ElevatedButton(
                        "Export to Downloads",
                        on_click=export_data,
                        bgcolor="#28A745", color=FB_WHITE),
                ], spacing=8, wrap=True),
                ft.ElevatedButton(
                    "Reset for Next Participant",
                    on_click=reset_participant,
                    bgcolor="#DC3545", color=FB_WHITE),

                ft.Divider(),

                # ── SCENARIO CONFIG SECTION ───────────────────────────────
                ft.Text("Scenario Configuration", size=_scaled(15),
                        weight=ft.FontWeight.BOLD, color=FB_DARK),
                active_dd, hook_f,
                ft.ElevatedButton("Save Changes", on_click=save_active,
                                  bgcolor=FB_BLUE, color=FB_WHITE),

                ft.Divider(),

                ft.Text("Add New Scenario", size=_scaled(14),
                        weight=ft.FontWeight.BOLD, color=FB_DARK),
                new_id_f, new_sender_f, new_hook_f,
                ft.ElevatedButton("Add Scenario", on_click=add_new,
                                  bgcolor=FB_BLUE, color=FB_WHITE),

                status_l,

            ], spacing=10),
            padding=_pad_all(16), expand=True),

    ], spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)


# ===========================================================================
# ROUTER
# ===========================================================================

def _go(page: ft.Page, route: str) -> None:
    global _app_route
    _app_route = route
    _render(page)


def _render(page: ft.Page) -> None:
    global _app_route
    page.controls.clear()
    route = _app_route or "boot"

    try:
        if route == "boot":
            _boot(page)
            return
        elif route == "registration":
            view = _build_registration(page, on_complete=lambda: _go(page, "feed"))
        elif route == "feed":
            view = _build_feed(page, on_notif_click=lambda: _go(page, "chat"))
        elif route == "chat":
            view = _build_chat(page, on_back=lambda: _go(page, "feed"))
        elif route == "admin":
            view = _build_admin(page, on_close=lambda: _go(page, "feed"))
        else:
            view = _error_view(f"Unknown route: {route}")

        page.add(view)

    except Exception as exc:
        logger.exception("Render error on route '%s': %s", route, exc)
        page.controls.clear()
        page.add(_error_view(str(exc)))

    page.update()


def _boot(page: ft.Page) -> None:
    global _participant_profile, _font_scale
    if profile_exists():
        _participant_profile = load_profile()
        _font_scale = config.get("accessibility_font_scale", 1.0) or 1.0
        _go(page, "feed")
    else:
        _go(page, "registration")


# ===========================================================================
# MAIN
# ===========================================================================

def main(page: ft.Page) -> None:
    page.title      = "Social Connect+ Assistant"
    page.bgcolor    = FB_BG
    page.padding    = 0
    page.spacing    = 0
    page.theme_mode = ft.ThemeMode.LIGHT

    # Push content below Android status bar
    try:
        if hasattr(page, "window") and hasattr(page.window, "status_bar_color"):
            page.window.status_bar_color = FB_BLUE
    except Exception:
        pass

    def on_lifecycle(e):
        if e.data in ("pause", "inactive", "detach"):
            if _chat_engine:
                scenario = _active_scenario()
                save_session(active_scenario_id=scenario["id"],
                             conversation_history=_chat_engine.history,
                             accumulated_latency_ms=0.0,
                             interaction_count=_interaction_count,
                             current_phase=_chat_engine.phase)

    page.on_app_lifecycle_state_change = on_lifecycle

    async def _queue_flush_loop():
        import asyncio
        while True:
            await asyncio.sleep(30)
            depth = get_queue_depth()
            if depth > 0:
                flushed = await flush_queue(telemetry)
                if flushed:
                    logger.info("Flushed %d queued events.", flushed)

    page.run_task(_queue_flush_loop)
    _render(page)


if __name__ == "__main__":
    ft.app(target=main)