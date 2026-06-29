"""
<<<<<<< HEAD
main.py — SPICE v7  (notification-channel update)
Pixel-perfect Messenger clone with:
  - Android Notification Channel registered at startup (API 26+ fix)
  - POST_NOTIFICATIONS runtime permission requested on Android 13+
  - Every button interactive with realistic Messenger responses
  - Notification delivered as bold unread message in chat list
  - 30-second (configurable) delayed message arrival
"""
from __future__ import annotations
import asyncio, logging, os, random, sys, time
=======
main.py — SPICE v7
Pixel-perfect Messenger clone with:
  - Every button interactive with realistic Messenger responses
  - Notification delivered as bold unread message in chat list (not overlay)
  - 30-second delayed message arrival from Medicare contact
"""
from __future__ import annotations
import asyncio, logging, os, random, time
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
from typing import Optional
import flet as ft
from path_utils import get_secure_path, get_writable_path

# ── Imports with fallbacks ────────────────────────────────────────────────────
try:
    from config_loader import config
except Exception as _e:
    logging.critical("config_loader: %s", _e)
    class _C:
        def get(self,k,d=None): return d
        def get_active_scenario(self): return None
        def get_contacts(self): return []
        def get_stories(self): return []
        def get_active_scam_contact(self): return None
        def get_fallback_responses(self,s,p=1): return ["Please reply."]
        def get_system_prompt(self,s,p=1): return ""
        def get_scenarios(self): return []
        def set(self,k,v): pass
        def set_active_scenario(self,s): pass
        def update_scenario_hook(self,s,h): pass
        def add_scenario(self,s): pass
        def update_contact(self,i,u): pass
        def add_contact(self,c): pass
    config = _C()

try:
    from participant import profile_exists, load_profile, save_profile
except Exception:
    def profile_exists(): return False
    def load_profile(): return {}
    def save_profile(f,l): return {"participant_id":"UNKNOWN","first_name":f,"last_name":l}

try:
    from telemetry import telemetry, scrub_message
except Exception:
    class _T:
        def log(self,**k): pass
    telemetry = _T()
    def scrub_message(t): return t, None

try:
    from session import save_session, load_session
except Exception:
    def save_session(*a,**k): pass
    def load_session(): return None

try:
    from ai_engine import ChatEngine
except Exception:
    ChatEngine = None

try:
    from network_queue import enqueue_event, flush_queue, get_queue_depth
except Exception:
    def enqueue_event(e): pass
    async def flush_queue(t): return 0
    def get_queue_depth(): return 0

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY","")

<<<<<<< HEAD
# ══════════════════════════════════════════════════════════════════════════════
# ANDROID NOTIFICATION CHANNEL — must be registered before first notification
# ══════════════════════════════════════════════════════════════════════════════
NOTIF_CHANNEL_ID   = "spice_simulation_channel"
NOTIF_CHANNEL_NAME = "Simulation Messages"

def _register_notification_channel():
    """
    Register the Android Notification Channel required by API 26+ (Android 8+).
    Without this, ALL notifications are silently dropped by the OS — no error,
    no crash, nothing appears on the lock screen or notification shade.

    Safe no-op on desktop / development mode.
    Called once at module load time, before main() runs.
    """
    if not getattr(sys, 'frozen', False):
        logger.info("_register_notification_channel: desktop mode — skipping")
        return
    try:
        from jnius import autoclass  # available inside serious_python on Android

        NotificationChannel = autoclass('android.app.NotificationChannel')
        NotificationManager = autoclass('android.app.NotificationManager')
        PythonActivity      = autoclass('org.kivy.android.PythonActivity')

        # NotificationManager.IMPORTANCE_HIGH = 4
        # Produces heads-up banners + lock screen notifications
        IMPORTANCE_HIGH = 4

        channel = NotificationChannel(
            NOTIF_CHANNEL_ID,
            NOTIF_CHANNEL_NAME,
            IMPORTANCE_HIGH
        )
        channel.setDescription("Delivers SPICE simulation scenario messages")
        channel.enableVibration(True)
        channel.enableLights(True)

        context = PythonActivity.mActivity
        manager = context.getSystemService(
            NotificationManager._class.getName())
        manager.createNotificationChannel(channel)

        logger.info("Android notification channel registered: %s",
                    NOTIF_CHANNEL_ID)

    except Exception as ex:
        # Non-fatal — in-app bold thread still works as fallback
        logger.warning("_register_notification_channel failed: %s", ex)


# Register channel immediately at import time so it is ready before
# _schedule_notif fires, regardless of how long the delay is.
_register_notification_channel()


# ── Colors (exact Messenger) ──────────────────────────────────────────────────
BG        = "#FFFFFF"
BLUE      = "#0099FF"   # messenger wordmark
SEND_BLU  = "#0084FF"   # bubbles, buttons
BUBBLE_IN = "#EBEBEB"
TXT_DARK  = "#000000"
TXT_MED   = "#1C1E21"
TXT_GRAY  = "#8A8D91"
DIVIDER   = "#E4E6EB"
INPUT_BG  = "#F0F2F5"
GREEN     = "#31A24C"
WHITE     = "#FFFFFF"

# ── Layout helpers (Flet 0.85.3 — no .all/.only/.symmetric) ──────────────────
def P(l=0,r=0,t=0,b=0): return ft.Padding(left=l,top=t,right=r,bottom=b)
def Pa(v):               return ft.Padding(left=v,top=v,right=v,bottom=v)
def M(l=0,r=0,t=0,b=0): return ft.Margin(left=l,top=t,right=r,bottom=b)
def BR(v):               return ft.BorderRadius(top_left=v,top_right=v,
                                                bottom_left=v,bottom_right=v)
def BS(l=0,r=0,t=0,b=0,c=DIVIDER):
    s=ft.BorderSide
    return ft.Border(left=s(l,c),right=s(r,c),top=s(t,c),bottom=s(b,c))

# ── Global state ──────────────────────────────────────────────────────────────
_profile:         dict  = {}
_chat_engine             = None
_interactions:    int   = 0
_msg_render_t:    float = 0.0
_notif_render_t:  float = 0.0
_admin_taps:      int   = 0
_route:           str   = "boot"
_chat_unread:     bool  = True
_notif_fired:     bool  = False
_session_store:   dict  = {}
_page_ref                = None
_notif_log:       list  = []
_notif_fire_time: float = 0.0

def _pid(): return _profile.get("participant_id","UNKNOWN")

=======
# ── Colors (exact Messenger) ──────────────────────────────────────────────────
BG        = "#FFFFFF"
BLUE      = "#0099FF"   # messenger wordmark
SEND_BLU  = "#0084FF"   # bubbles, buttons
BUBBLE_IN = "#EBEBEB"
TXT_DARK  = "#000000"
TXT_MED   = "#1C1E21"
TXT_GRAY  = "#8A8D91"
DIVIDER   = "#E4E6EB"
INPUT_BG  = "#F0F2F5"
GREEN     = "#31A24C"
WHITE     = "#FFFFFF"

# ── Layout helpers (Flet 0.85.3 — no .all/.only/.symmetric) ──────────────────
def P(l=0,r=0,t=0,b=0): return ft.Padding(left=l,top=t,right=r,bottom=b)
def Pa(v):               return ft.Padding(left=v,top=v,right=v,bottom=v)
def M(l=0,r=0,t=0,b=0): return ft.Margin(left=l,top=t,right=r,bottom=b)
def BR(v):               return ft.BorderRadius(top_left=v,top_right=v,
                                                bottom_left=v,bottom_right=v)
def BS(l=0,r=0,t=0,b=0,c=DIVIDER):
    s=ft.BorderSide
    return ft.Border(left=s(l,c),right=s(r,c),top=s(t,c),bottom=s(b,c))

# ── Global state ──────────────────────────────────────────────────────────────
_profile:         dict  = {}
_chat_engine             = None
_interactions:    int   = 0
_msg_render_t:    float = 0.0
_notif_render_t:  float = 0.0
_admin_taps:      int   = 0
_route:           str   = "boot"
_chat_unread:     bool  = True    # True = Medicare visible at top from launch
_notif_fired:     bool  = False
_session_store:   dict  = {}      # replaces page.session
_page_ref                = None   # set in main(), used by deferred tasks
_notif_log:       list  = []      # log of fired notifications for feed screen
_notif_fire_time: float = 0.0     # timestamp when notification fired

def _pid(): return _profile.get("participant_id","UNKNOWN")

>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
def _scenario():
    s = config.get_active_scenario()
    return s or {
        "id":"medicare_authority",
        "threat_vector_classification":"Authority_Threat",
        "sender_identity":{"display_name":"Medicare Services",
                           "initials_fallback":"M","initials_color":"#0057A8"},
        "hook_message":"Hi, this is Sarah from Medicare Services. I need to speak with you urgently about your coverage — please respond as soon as you can.",
        "simulation_timing":{"simulated_timestamp":"Just Now"},
        "phase_thresholds":{"rapport_turns":1,"urgency_turns":1},
    }

def _make_engine():
    """Always returns a working engine — uses fallback if ChatEngine unavailable."""
    if ChatEngine is not None:
        try:
            engine = ChatEngine(scenario=_scenario(), participant_id=_pid(),
                                api_key=ANTHROPIC_API_KEY)
            return engine
        except Exception as ex:
            logger.error("ChatEngine init failed: %s", ex)
<<<<<<< HEAD
=======
    # Return a minimal fallback engine that delivers hook + fallback replies
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
    class _FallbackEngine:
        def __init__(self):
            self.history = []
            self.phase = 1
            self.turn_count = 0
        async def send_message(self, text):
            self.history.append({"role":"user","content":text})
            self.turn_count += 1
            sc = _scenario()
            responses = config.get_fallback_responses(sc.get("id",""), self.phase)
            import random as _r
            reply = _r.choice(responses) if responses else "Please reply as soon as possible."
            self.history.append({"role":"assistant","content":reply})
            return reply, None
        def import_state(self, state):
            self.history = state.get("history", [])
            self.phase = state.get("phase", 1)
            self.turn_count = state.get("turn_count", 0)
    return _FallbackEngine()

# ── Avatar ────────────────────────────────────────────────────────────────────
def _av(initial:str, size:int, color:str=SEND_BLU, online:bool=False) -> ft.Stack:
    ds = max(10, size//5)
    layers = [ft.Container(
        content=ft.Text(initial.upper()[:1], color=WHITE,
                        size=size*0.38, weight=ft.FontWeight.BOLD),
        width=size, height=size, bgcolor=color,
        border_radius=size//2, alignment=ft.Alignment(0,0))]
    if online:
<<<<<<< HEAD
=======
        # Offset inward slightly so dot overlaps avatar border like real Messenger
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
        offset = max(2, size//14)
        layers.append(ft.Container(
            content=ft.Container(width=ds, height=ds, bgcolor=GREEN,
                                 border_radius=ds//2,
                                 border=BS(2,2,2,2,BG)),
<<<<<<< HEAD
=======
            # Use margin to push dot inward from bottom-right corner
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
            margin=ft.Margin(left=size-ds-offset, top=size-ds-offset,
                             right=0, bottom=0),
            width=ds, height=ds))
    return ft.Stack(layers, width=size, height=size)

# ── Shared modal / placeholder screens ───────────────────────────────────────
def _modal(page:ft.Page, title:str, icon, body:str, back_label:str="Back",
           back_fn=None):
<<<<<<< HEAD
    page.controls.clear()
=======
    """Generic full-screen placeholder matching Messenger's visual style."""
    page.controls.clear()
    # Header bar
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
    header = ft.Container(
        content=ft.Row([
            ft.GestureDetector(
                content=ft.Row([
                    ft.Icon(ft.Icons.ARROW_BACK, color=SEND_BLU, size=24),
                    ft.Text(back_label, color=SEND_BLU, size=15),
                ], spacing=4),
                on_tap=back_fn or (lambda e: None)),
            ft.Container(expand=1),
        ]),
        padding=P(12,12,44,10), bgcolor=BG,
        shadow=ft.BoxShadow(blur_radius=2,color="#18000000",offset=ft.Offset(0,1)))
<<<<<<< HEAD
=======
    # Centered body — use Stack with alignment for true centering
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
    body_col = ft.Column([
        ft.Icon(icon, size=72, color=SEND_BLU),
        ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=TXT_MED),
        ft.Text(body, size=14, color=TXT_GRAY, text_align=ft.TextAlign.CENTER),
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=12)
<<<<<<< HEAD
    center = ft.Container(content=body_col, expand=True, alignment=ft.Alignment(0,0))
=======
    center = ft.Container(
        content=body_col,
        expand=True,
        alignment=ft.Alignment(0, 0))
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
    page.add(ft.Container(
        content=ft.Column([header, center], spacing=0, expand=True),
        bgcolor=BG, expand=True))
    page.update()

# ══════════════════════════════════════════════════════════════════════════════
# VIEWS
# ══════════════════════════════════════════════════════════════════════════════

def _error_view(msg:str) -> ft.Column:
    return ft.Column([
        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED,color=ft.Colors.ORANGE_700,size=56),
        ft.Text("Configuration Error",size=20,weight=ft.FontWeight.BOLD),
        ft.Text("Please contact your research coordinator.",size=14,
                color=TXT_GRAY,text_align=ft.TextAlign.CENTER),
        ft.Text(msg,size=10,color=TXT_GRAY,italic=True,
                text_align=ft.TextAlign.CENTER,selectable=True),
    ],horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,spacing=14,expand=True)

# ── Registration ──────────────────────────────────────────────────────────────
def _build_reg(page:ft.Page, done) -> ft.Column:
    f1=ft.TextField(label="First Name",text_size=16,
                    border_color=SEND_BLU,focused_border_color=SEND_BLU,
                    content_padding=P(16,16,14,14))
    f2=ft.TextField(label="Last Name",text_size=16,
                    border_color=SEND_BLU,focused_border_color=SEND_BLU,
                    content_padding=P(16,16,14,14))
    err=ft.Text("",color=ft.Colors.RED_600,size=13)
    def go(e):
        global _profile
        if not (f1.value or "").strip() or not (f2.value or "").strip():
            err.value="Please enter both names."; page.update(); return
        _profile=save_profile(f1.value,f2.value)
        done()
<<<<<<< HEAD
=======
        # Schedule notification for new registrant
        # Keep _chat_unread=True so Medicare stays bold in inbox
        # Only reset _notif_fired so the timer can fire fresh
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
        global _notif_fired, _chat_engine
        _notif_fired = False
        _chat_engine = None
        if _page_ref:
            logger.info("New registration — scheduling notification in %ss",
                        config.get("notification_delay_seconds", 60))
            _page_ref.run_task(_schedule_notif, _page_ref)
    return ft.Column([
        ft.Container(height=60),
        ft.Icon(ft.Icons.CONNECT_WITHOUT_CONTACT,size=68,color=SEND_BLU),
        ft.Text("Social Connect+ Assistant",size=22,
                weight=ft.FontWeight.BOLD,color=TXT_MED),
        ft.Container(content=ft.Text(
            "Welcome to the 30-day mobile engagement\nand user experience layout evaluation.",
            size=14,color=TXT_GRAY,text_align=ft.TextAlign.CENTER),
            padding=P(24,24)),
        ft.Container(height=12),
        ft.Container(content=ft.Column([f1,f2,err],spacing=12),
                     padding=P(32,32)),
        ft.Container(height=6),
        ft.ElevatedButton("Begin Evaluation",on_click=go,
                          bgcolor=SEND_BLU,color=WHITE,
                          style=ft.ButtonStyle(
                              shape=ft.RoundedRectangleBorder(radius=8)),
                          width=260,height=48),
    ],horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.START,
        spacing=12,expand=True,scroll=ft.ScrollMode.AUTO)

# ── Chat list ─────────────────────────────────────────────────────────────────
<<<<<<< HEAD
_DEFAULT_CONTACTS = [
=======
# Default contacts shown if contacts.json fails to load on Android
_DEFAULT_CONTACTS = [
    {"id":"contact_medicare","display_name":"Medicare Services","initials":"M",
     "initials_color":"#0057A8","is_active_online":True,"list_position":1,
     "scenario_id":"medicare_authority","preview_override":"MEDICARE NOTICE: Your health coverage...",
     "timestamp":"Just Now","is_unread":True,"filler_conversation":[]},
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
    {"id":"contact_mom","display_name":"Mom","initials":"M",
     "initials_color":"#E91E8C","is_active_online":True,"list_position":2,
     "scenario_id":"","preview_override":"You: Sounds good! See you Sunday 😊",
     "timestamp":"2h","is_unread":False,
     "filler_conversation":[
         {"role":"user","content":"Hey mom, are we still on for Sunday?"},
         {"role":"assistant","content":"Of course! I'm making your favorite. Does 2pm work?"},
         {"role":"user","content":"Perfect, I'll bring dessert 😊"},
         {"role":"assistant","content":"Sounds good! See you Sunday 😊"}]},
    {"id":"contact_sarah","display_name":"Sarah","initials":"S",
     "initials_color":"#9C27B0","is_active_online":True,"list_position":3,
     "scenario_id":"","preview_override":"Did you see the game last night?",
     "timestamp":"5h","is_unread":False,
     "filler_conversation":[
         {"role":"assistant","content":"Did you see the game last night? That ending was unbelievable!"},
         {"role":"user","content":"I know! I couldn't believe it"},
         {"role":"assistant","content":"We should watch the next one together 🍿"},
         {"role":"user","content":"Deal! Just let me know when"}]},
    {"id":"contact_james","display_name":"James","initials":"J",
     "initials_color":"#2196F3","is_active_online":False,"list_position":4,
     "scenario_id":"","preview_override":"You: Let me know what you think",
     "timestamp":"Yesterday","is_unread":False,
     "filler_conversation":[
         {"role":"user","content":"Hey James, did you get a chance to look at those photos?"},
         {"role":"assistant","content":"Just looking now, they look great!"},
         {"role":"user","content":"Let me know what you think"}]},
    {"id":"contact_linda","display_name":"Linda","initials":"L",
     "initials_color":"#4CAF50","is_active_online":True,"list_position":5,
     "scenario_id":"","preview_override":"Photo","timestamp":"Mon",
     "is_unread":False,
     "filler_conversation":[
         {"role":"assistant","content":"Look what I found at the antique shop! 📷"},
         {"role":"user","content":"Oh wow that's beautiful!"},
         {"role":"assistant","content":"The little shop on Main Street, so many treasures"},
         {"role":"user","content":"I'll check it out this weekend"}]},
    {"id":"contact_robert","display_name":"Robert","initials":"R",
     "initials_color":"#FF5722","is_active_online":False,"list_position":6,
     "scenario_id":"","preview_override":"You: 👍","timestamp":"Sun",
     "is_unread":False,
     "filler_conversation":[
         {"role":"assistant","content":"Hey, did you end up finding a plumber?"},
         {"role":"user","content":"Yes finally! Guy came yesterday"},
         {"role":"assistant","content":"Oh great, that was a long time coming"},
         {"role":"user","content":"👍"}]},
    {"id":"contact_carol","display_name":"Carol","initials":"C",
     "initials_color":"#795548","is_active_online":True,"list_position":7,
     "scenario_id":"","preview_override":"Call me when you get a chance",
     "timestamp":"Sat","is_unread":False,
     "filler_conversation":[
         {"role":"assistant","content":"Hey, call me when you get a chance. Nothing urgent, just want to catch up!"},
         {"role":"user","content":"Will do, I'll call after dinner tonight"},
         {"role":"assistant","content":"Perfect, talk to you then!"}]},
    {"id":"contact_david","display_name":"David","initials":"D",
     "initials_color":"#607D8B","is_active_online":False,"list_position":8,
     "scenario_id":"","preview_override":"You: Okay sounds good 👍",
     "timestamp":"Fri","is_unread":False,
     "filler_conversation":[
         {"role":"assistant","content":"Are you coming to the neighborhood meeting Thursday?"},
         {"role":"user","content":"What time does it start?"},
         {"role":"assistant","content":"7pm at the community center"},
         {"role":"user","content":"Okay sounds good 👍"}]},
]

_DEFAULT_STORIES = [
<<<<<<< HEAD
=======
    # These are configurable from Admin → Profile → Active Users Row
    # Researchers can change names, initials, and colors from the admin panel
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
    {"name":"Kaylee","initials":"K","color":"#E91E63","is_active":True},
    {"name":"Laurann","initials":"L","color":"#9C27B0","is_active":True},
    {"name":"Jeanne","initials":"J","color":"#3F51B5","is_active":True},
    {"name":"Sharon","initials":"S","color":"#009688","is_active":False},
    {"name":"Mark","initials":"M","color":"#FF5722","is_active":True},
    {"name":"Betty","initials":"B","color":"#795548","is_active":False},
]


def _build_list(page:ft.Page, open_scam, open_filler) -> ft.Column:
    global _notif_render_t, _admin_taps
    _notif_render_t = time.time()*1000

<<<<<<< HEAD
    contacts  = config.get_contacts() or _DEFAULT_CONTACTS
    stories   = config.get_stories()  or _DEFAULT_STORIES
=======
    # Use config contacts if available, fall back to hardcoded defaults
    # This ensures the list always shows on Android even if contacts.json
    # fails to load from the packaged asset path
    contacts  = config.get_contacts() or _DEFAULT_CONTACTS
    stories   = config.get_stories()  or _DEFAULT_STORIES
    # Build scam contact directly from active scenario — never depends on
    # contacts.json matching correctly. This is the only reliable approach.
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
    _active_sc = _scenario()
    _sc_si     = _active_sc.get("sender_identity", {})
    _sc_hook   = _active_sc.get("hook_message",
                                _active_sc.get("initial_hook_message",""))
    _sc_preview= (_sc_hook[:42] + "…") if len(_sc_hook) > 42 else _sc_hook

    scam_contact_hardcoded = {
        "id":               "scam_contact_active",
        "display_name":     _sc_si.get("display_name","Medicare Services"),
        "initials":         _sc_si.get("initials_fallback",
                                       _sc_si.get("display_name","M")[:1].upper()),
        "initials_color":   _sc_si.get("initials_color","#0057A8"),
        "is_active_online": True,
        "scenario_id":      _active_sc.get("id","medicare_authority"),
        "preview_override": _sc_preview,
        "timestamp":        "Just Now",
        "is_unread":        True,
        "filler_conversation": [],
    }
    scam_id = "scam_contact_active"

<<<<<<< HEAD
    scam_c = config.get_active_scam_contact()
    if scam_c:
=======
    # Also check contacts.json in case researcher customised it
    scam_c = config.get_active_scam_contact()
    if scam_c:
        # Merge — use contacts.json display name if set, else scenario
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
        scam_contact_hardcoded["display_name"] = scam_c.get(
            "display_name", scam_contact_hardcoded["display_name"])
        scam_contact_hardcoded["initials"] = scam_c.get(
            "initials", scam_contact_hardcoded["initials"])
        scam_contact_hardcoded["initials_color"] = scam_c.get(
            "initials_color", scam_contact_hardcoded["initials_color"])
<<<<<<< HEAD

    admin_lim = 5
=======
    admin_lim = 5  # fixed at 5 taps — not configurable to prevent accidental changes
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d

    def tap_wordmark(e):
        global _admin_taps
        _admin_taps += 1
        if _admin_taps >= admin_lim:
            _admin_taps = 0
            _go(page, "password")

    # ── Header ────────────────────────────────────────────────────────────────
    header=ft.Container(
        content=ft.Row([
            ft.GestureDetector(
                content=ft.Text("messenger",size=26,
                                weight=ft.FontWeight.W_800,color=BLUE),
                on_tap=tap_wordmark),
            ft.Row([
<<<<<<< HEAD
                ft.GestureDetector(
                    content=ft.Container(
                        content=ft.Icon(ft.Icons.EDIT_SQUARE,color=TXT_MED,size=22),
=======
                # Compose new message
                ft.GestureDetector(
                    content=ft.Container(
                        content=ft.Icon(ft.Icons.EDIT_SQUARE,
                                        color=TXT_MED,size=22),
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
                        bgcolor=INPUT_BG,border_radius=20,padding=9),
                    on_tap=lambda e: _modal(page,"New Message",
                                            ft.Icons.EDIT_OUTLINED,
                                            "Search for a person or group to message.",
                                            back_fn=lambda ev: _go(page,"list"))),
<<<<<<< HEAD
                ft.GestureDetector(
                    content=ft.Container(
                        content=ft.Text("f",size=16,weight=ft.FontWeight.BOLD,
=======
                # Facebook f icon
                ft.GestureDetector(
                    content=ft.Container(
                        content=ft.Text("f",size=16,
                                        weight=ft.FontWeight.BOLD,
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
                                        color=SEND_BLU),
                        width=40,height=40,bgcolor=INPUT_BG,
                        border_radius=20,alignment=ft.Alignment(0,0)),
                    on_tap=lambda e: _modal(page,"Opening Facebook",
                                            ft.Icons.FACEBOOK,
                                            "Switching to the Facebook app...",
                                            back_fn=lambda ev: _go(page,"list"))),
            ],spacing=8),
        ],alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        bgcolor=BG,padding=P(16,16,44,8))

    # ── Search bar ────────────────────────────────────────────────────────────
<<<<<<< HEAD
    meta_ai_icon = ft.Stack([
        ft.Container(width=24,height=24,bgcolor="#A855F7",border_radius=12),
        ft.Container(width=18,height=18,bgcolor="#3B82F6",border_radius=9,
                     margin=ft.Margin(left=3,top=3,right=0,bottom=0)),
        ft.Container(width=10,height=10,bgcolor=INPUT_BG,border_radius=5,
=======
    # Meta AI icon: gradient ring approximated with concentric circles
    meta_ai_icon = ft.Stack([
        ft.Container(width=24, height=24,
                     bgcolor="#A855F7", border_radius=12),
        ft.Container(width=18, height=18,
                     bgcolor="#3B82F6", border_radius=9,
                     margin=ft.Margin(left=3,top=3,right=0,bottom=0)),
        ft.Container(width=10, height=10,
                     bgcolor=INPUT_BG, border_radius=5,
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
                     margin=ft.Margin(left=7,top=7,right=0,bottom=0)),
    ], width=24, height=24)

    search=ft.GestureDetector(
        content=ft.Container(
            content=ft.Row([
                meta_ai_icon,
                ft.Text("Ask Meta AI or search",color=TXT_GRAY,size=15),
            ],spacing=10),
            bgcolor=INPUT_BG,border_radius=24,
            padding=P(14,14,11,11),margin=P(14,14,2,10)),
<<<<<<< HEAD
        on_tap=lambda e: _modal(page,"Search",ft.Icons.SEARCH,
=======
        on_tap=lambda e: _modal(page,"Search",
                                ft.Icons.SEARCH,
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
                                "Search for people, groups, or messages.",
                                back_fn=lambda ev: _go(page,"list")))

    # ── Stories row ───────────────────────────────────────────────────────────
    def _story(initial,name,color=SEND_BLU,online=False,create=False):
        if create:
            av=ft.Container(
                content=ft.Icon(ft.Icons.ADD,color=SEND_BLU,size=26),
                width=68,height=68,bgcolor=INPUT_BG,border_radius=34,
                alignment=ft.Alignment(0,0))
        else:
            av=_av(initial,68,color,online)
        col=ft.Column([av,
                       ft.Text(name,size=11,color=TXT_MED,
                               text_align=ft.TextAlign.CENTER,max_lines=1,
                               overflow=ft.TextOverflow.ELLIPSIS)],
                      horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                      spacing=4,width=76)
        def tap_story(e):
            if create:
                _modal(page,"Create Story",ft.Icons.ADD_CIRCLE_OUTLINE,
                       "Add a photo or video to share with friends.",
                       back_fn=lambda ev: _go(page,"list"))
            else:
                _modal(page,f"{name}'s Story",ft.Icons.SLIDESHOW,
                       f"{name} posted a story.",
                       back_fn=lambda ev: _go(page,"list"))
        return ft.GestureDetector(content=col,on_tap=tap_story)

    story_items=[_story("","Create story",create=True)]
    for s in stories:
        story_items.append(_story(s.get("initials","?"),s.get("name",""),
                                  color=s.get("color",SEND_BLU),
                                  online=s.get("is_active",False)))
    stories_row=ft.Container(
        content=ft.Row(story_items,scroll=ft.ScrollMode.AUTO,spacing=6),
<<<<<<< HEAD
        padding=P(14,14,4,8))
=======
        padding=P(14,14,8,12))
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d

    # ── Thread rows ───────────────────────────────────────────────────────────
    def _thread(contact:dict)->ft.Container:
        name    = contact.get("display_name","")
        initial = contact.get("initials",name[:1])
        color   = contact.get("initials_color",SEND_BLU)
        online  = contact.get("is_active_online",False)
        ts      = contact.get("timestamp","")
        is_scam = contact.get("scenario_id") == _active_sc.get("id","")
        unread  = is_scam and _chat_unread

        override=contact.get("preview_override","")
        if override:
            preview=override
        else:
            conv=contact.get("filler_conversation",[])
            if conv:
                last=conv[-1]
                prefix="You: " if last["role"]=="user" else ""
                preview=prefix+last["content"]
            else:
                preview=""
        preview=(preview[:42]+"…") if len(preview)>42 else preview

<<<<<<< HEAD
=======
        # Update preview/timestamp if notification fired
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
        if is_scam and _chat_unread:
            sc=_scenario()
            hook=sc.get("hook_message",sc.get("initial_hook_message",""))
            preview=(hook[:42]+"…") if len(hook)>42 else hook
            ts="Just Now"

        def handler(e):
            global _chat_unread
            lat=time.time()*1000-_notif_render_t
            if is_scam:
                telemetry.log(participant_id=_pid(),
                              scenario_type=_scenario().get("threat_vector_classification",""),
                              event_type="Notification_Click",latency_ms=lat)
                _chat_unread=False
                open_scam()
            else:
                _session_store["filler_contact"]=contact
                open_filler()

        return ft.Container(
            content=ft.Row([
                _av(initial,56,color,online),
                ft.Column([
                    ft.Row([
                        ft.Text(name,size=16,
                                weight=ft.FontWeight.W_700 if unread
                                else ft.FontWeight.W_500,
                                color=TXT_DARK if unread else TXT_MED,
                                expand=True,max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Container(width=10,height=10,
                                     bgcolor=SEND_BLU,border_radius=5,
                                     visible=unread),
                    ],vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(f"{preview} · {ts}" if ts else preview,
                            size=13,
                            color=TXT_DARK if unread else "#8A8D91",
                            weight=ft.FontWeight.W_700 if unread
                            else ft.FontWeight.NORMAL,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS),
                ],spacing=3,expand=True),
<<<<<<< HEAD
            ],spacing=12,vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=P(14,14,8,8),bgcolor=BG,
            on_click=handler,ink=True)

    filler_contacts  = [c for c in contacts if not c.get("scenario_id")]
    display_contacts = [scam_contact_hardcoded] + filler_contacts
    rows=[_thread(c) for c in display_contacts]
    thread_list=ft.ListView(rows,expand=True,spacing=0,padding=P(0,0,0,0))

    # ── Bottom nav ────────────────────────────────────────────────────────────
    def _tab(icon,icon_on,label,active=False,badge=False,on_tap=None):
        col=SEND_BLU if active else TXT_GRAY
        ic_w=ft.Stack([
            ft.Icon(icon_on if active else icon,color=col,size=26),
            ft.Container(
                content=ft.Container(width=8,height=8,
                                     bgcolor="#FF3B30",border_radius=4),
                visible=badge,alignment=ft.Alignment(1,-1),
                width=26,height=26),
        ]) if badge else ft.Icon(icon_on if active else icon,color=col,size=26)
        return ft.Container(
            content=ft.GestureDetector(
                content=ft.Column([ic_w,
                                   ft.Text(label,size=10,color=col,
                                           weight=ft.FontWeight.BOLD if active
                                           else ft.FontWeight.NORMAL)],
                                  horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=3),
                on_tap=on_tap or (lambda e: None)),
            expand=True,padding=P(0,0,8,8),alignment=ft.Alignment(0,0))

    bottom=ft.Container(
        content=ft.Row([
            _tab(ft.Icons.CHAT_BUBBLE_OUTLINE,ft.Icons.CHAT_BUBBLE,
                 "Chats",active=True,on_tap=lambda e: _go(page,"list")),
            _tab(ft.Icons.PEOPLE_OUTLINE,ft.Icons.PEOPLE,"People",
                 on_tap=lambda e: _modal(page,"People",ft.Icons.PEOPLE,
                                         "Find friends and start new conversations.",
                                         back_fn=lambda ev: _go(page,"list"))),
            _tab(ft.Icons.NOTIFICATIONS_NONE,ft.Icons.NOTIFICATIONS,
                 "Notifications",badge=_chat_unread,
                 on_tap=lambda e: _go(page,"notifications")),
            _tab(ft.Icons.MENU,ft.Icons.MENU,"Menu",
                 on_tap=lambda e: _modal(page,"Menu",ft.Icons.MENU,
                                         "Account settings, privacy, and more.",
                                         back_fn=lambda ev: _go(page,"list"))),
        ],spacing=0),
        bgcolor=BG,
        border=ft.Border(top=ft.BorderSide(1,"#D0D0D0")),
        padding=P(0,0,0,20))

    return ft.Column([
        header,search,
        ft.Divider(height=1,color=DIVIDER),
        stories_row,
        ft.Divider(height=1,color=DIVIDER),
        thread_list,bottom,
    ],spacing=0,expand=True)

=======
            ],spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=P(14,14,10,10),bgcolor=BG,
            on_click=handler,ink=True)

    # Scam contact is ALWAYS at position 0 — built from active scenario above.
    # Filler contacts come from contacts.json (or defaults).
    # _chat_unread controls bold/dot styling only.
    filler_contacts  = [c for c in contacts if not c.get("scenario_id")]
    display_contacts = [scam_contact_hardcoded] + filler_contacts

    rows=[_thread(c) for c in display_contacts]
    thread_list=ft.ListView(rows,expand=True,spacing=0)

    # ── Bottom nav ────────────────────────────────────────────────────────────
    def _tab(icon,icon_on,label,active=False,badge=False,on_tap=None):
        col=SEND_BLU if active else TXT_GRAY
        ic_w=ft.Stack([
            ft.Icon(icon_on if active else icon,color=col,size=26),
            ft.Container(
                content=ft.Container(width=8,height=8,
                                     bgcolor="#FF3B30",border_radius=4),
                visible=badge,alignment=ft.Alignment(1,-1),
                width=26,height=26),
        ]) if badge else ft.Icon(icon_on if active else icon,color=col,size=26)
        return ft.Container(
            content=ft.GestureDetector(
                content=ft.Column([ic_w,
                                   ft.Text(label,size=10,color=col,
                                           weight=ft.FontWeight.BOLD if active
                                           else ft.FontWeight.NORMAL)],
                                  horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=3),
                on_tap=on_tap or (lambda e: None)),
            expand=True,
            padding=P(0,0,8,8),
            alignment=ft.Alignment(0,0))

    bottom=ft.Container(
        content=ft.Row([
            _tab(ft.Icons.CHAT_BUBBLE_OUTLINE,ft.Icons.CHAT_BUBBLE,
                 "Chats",active=True,
                 on_tap=lambda e: _go(page,"list")),
            _tab(ft.Icons.PEOPLE_OUTLINE,ft.Icons.PEOPLE,"People",
                 on_tap=lambda e: _modal(page,"People",
                                         ft.Icons.PEOPLE,
                                         "Find friends and start new conversations.",
                                         back_fn=lambda ev: _go(page,"list"))),
            _tab(ft.Icons.NOTIFICATIONS_NONE,ft.Icons.NOTIFICATIONS,
                 "Notifications",badge=_chat_unread,
                 on_tap=lambda e: _go(page,"notifications")),
            _tab(ft.Icons.MENU,ft.Icons.MENU,"Menu",
                 on_tap=lambda e: _modal(page,"Menu",
                                         ft.Icons.MENU,
                                         "Account settings, privacy, and more.",
                                         back_fn=lambda ev: _go(page,"list"))),
        ],spacing=0),
        bgcolor=BG,
        border=ft.Border(top=ft.BorderSide(1,"#D0D0D0")),
        padding=P(0,0,0,20))

    return ft.Column([
        header,search,
        ft.Divider(height=1,color=DIVIDER),
        stories_row,
        ft.Divider(height=1,color=DIVIDER),
        thread_list,bottom,
    ],spacing=0,expand=True)

>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
# ── Filler chat ───────────────────────────────────────────────────────────────
def _build_filler(page:ft.Page, back) -> ft.Container:
    contact = _session_store.get("filler_contact") or {}
    name    = contact.get("display_name","Contact")
    initial = contact.get("initials",name[:1])
    color   = contact.get("initials_color",SEND_BLU)
    online  = contact.get("is_active_online",False)
    conv    = contact.get("filler_conversation",[])

    def _make_bbl(text,user):
        bub=ft.Container(
<<<<<<< HEAD
            content=ft.Text(text,size=15,color=WHITE if user else TXT_DARK),
=======
            content=ft.Text(text,size=15,
                            color=WHITE if user else TXT_DARK),
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
            bgcolor=SEND_BLU if user else BUBBLE_IN,
            border_radius=BR(20),padding=P(14,14,10,10))
        av=_av(initial,28,color)
        if user:
            item=ft.Container(
                content=ft.Column([bub],
                                  horizontal_alignment=ft.CrossAxisAlignment.END),
                padding=P(70,0))
        else:
            item=ft.Row([av,
                         ft.Container(
                             content=ft.Column([bub],
                                               horizontal_alignment=ft.CrossAxisAlignment.START),
                             expand=True,padding=P(0,70))],
                        spacing=6,vertical_alignment=ft.CrossAxisAlignment.END)
        return ft.Container(content=item,padding=P(0,0,2,2))

    try:
        from datetime import datetime as _dt
        ts=_dt.now().strftime("%I:%M %p").lstrip("0")
    except Exception:
        ts="Today"

<<<<<<< HEAD
=======
    # Build all controls upfront and pass to ListView constructor
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
    msg_controls = [ft.Container(
        content=ft.Text(ts,size=11,color=TXT_GRAY,
                        text_align=ft.TextAlign.CENTER),
        padding=P(0,0,8,8),alignment=ft.Alignment(0,0))]
    for m in conv:
        msg_controls.append(_make_bbl(m["content"],user=(m["role"]=="user")))

<<<<<<< HEAD
    msgs=ft.ListView(controls=msg_controls,expand=True,spacing=2,
                     padding=P(8,8,12,8),auto_scroll=True,
                     build_controls_on_demand=False)
=======
    msgs=ft.ListView(
        controls=msg_controls,
        expand=True,
        spacing=2,
        padding=P(8,8,12,8),
        auto_scroll=True,
        build_controls_on_demand=False)
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d

    def _call(e):
        _modal(page,f"Calling {name}...",ft.Icons.PHONE,
               "Connecting your call. Please wait.",
               back_fn=lambda ev: (_session_store.update(
                   {"filler_contact":contact}), _go(page,"filler")))
    def _video(e):
        _modal(page,f"Video call with {name}",ft.Icons.VIDEOCAM,
               "Starting video call...",
               back_fn=lambda ev: (_session_store.update(
                   {"filler_contact":contact}), _go(page,"filler")))

    header=ft.Container(
        content=ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK,on_click=lambda e: back(),
                          icon_color=SEND_BLU,icon_size=26),
            ft.GestureDetector(
                content=_av(initial,40,color,online),
                on_tap=lambda e: _modal(page,name,ft.Icons.PERSON,
                                        f"View {name}'s profile and contact info.",
                                        back_fn=lambda ev: (_session_store.update(
                                            {"filler_contact":contact}), _go(page,"filler")))),
            ft.Column([
                ft.Text(name,weight=ft.FontWeight.BOLD,size=16,color=TXT_MED),
                ft.Text("Active now" if online else "Messenger",
                        size=12,color=TXT_GRAY),
            ],spacing=0,expand=True),
            ft.Row([
                ft.IconButton(ft.Icons.PHONE,icon_color=SEND_BLU,
                              icon_size=26,on_click=_call),
                ft.IconButton(ft.Icons.VIDEOCAM,icon_color=SEND_BLU,
                              icon_size=26,on_click=_video),
            ],spacing=0),
        ],spacing=8,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=BG,padding=P(4,8,44,8),
<<<<<<< HEAD
        shadow=ft.BoxShadow(blur_radius=2,color="#18000000",offset=ft.Offset(0,1)))
=======
        shadow=ft.BoxShadow(blur_radius=2,color="#18000000",
                            offset=ft.Offset(0,1)))
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d

    def _attach(e):
        _modal(page,"Attachments",ft.Icons.ATTACH_FILE,
               "Send photos, files, GIFs, and more.",
               back_fn=lambda ev: (_session_store.update(
                   {"filler_contact":contact}),_go(page,"filler")))
    def _camera(e):
        _modal(page,"Camera",ft.Icons.CAMERA_ALT,
               "Take a photo or video to send.",
               back_fn=lambda ev: (_session_store.update(
                   {"filler_contact":contact}),_go(page,"filler")))
    def _images(e):
        _modal(page,"Photo Library",ft.Icons.IMAGE,
               "Choose a photo from your library to send.",
               back_fn=lambda ev: (_session_store.update(
                   {"filler_contact":contact}),_go(page,"filler")))
    def _mic(e):
        _modal(page,"Audio Message",ft.Icons.MIC,
               "Hold to record an audio message.",
               back_fn=lambda ev: (_session_store.update(
                   {"filler_contact":contact}),_go(page,"filler")))

    toolbar=ft.Container(
        content=ft.Row([
            ft.IconButton(ft.Icons.ADD_CIRCLE,icon_color=SEND_BLU,
                          icon_size=28,on_click=_attach),
            ft.IconButton(ft.Icons.CAMERA_ALT,icon_color=SEND_BLU,
                          icon_size=28,on_click=_camera),
            ft.IconButton(ft.Icons.IMAGE,icon_color=SEND_BLU,
                          icon_size=28,on_click=_images),
            ft.IconButton(ft.Icons.MIC,icon_color=SEND_BLU,
                          icon_size=28,on_click=_mic),
            ft.Container(content=ft.Text("Aa",color=TXT_GRAY,size=15),
                         bgcolor=INPUT_BG,border_radius=24,expand=True,
                         padding=P(16,16,10,10)),
            ft.IconButton(ft.Icons.EMOJI_EMOTIONS,icon_color=SEND_BLU,icon_size=28),
            ft.Container(
                content=ft.Icon(ft.Icons.THUMB_UP,color=WHITE,size=20),
                width=40,height=40,bgcolor=SEND_BLU,border_radius=20,
                alignment=ft.Alignment(0,0)),
        ],spacing=2,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=BG,padding=P(6,8,6,24),
<<<<<<< HEAD
        shadow=ft.BoxShadow(blur_radius=4,color="#18000000",offset=ft.Offset(0,-1)))
=======
        shadow=ft.BoxShadow(blur_radius=4,color="#18000000",
                            offset=ft.Offset(0,-1)))
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d

    return ft.Container(
        content=ft.Column([header,msgs,toolbar],spacing=0,expand=True),
        bgcolor=BG,expand=True)

# ── Live scam chat ────────────────────────────────────────────────────────────
def _build_chat(page:ft.Page, back) -> ft.Container:
    global _chat_engine,_interactions,_msg_render_t

    sc=_scenario()
    si=sc.get("sender_identity",{})
<<<<<<< HEAD
    # Prefer admin-panel override — same source the chat list thread uses
    _scam_ov = config.get_active_scam_contact() or {}
    sender  = _scam_ov.get("display_name") or si.get("display_name","Medicare Services")
    initial = (_scam_ov.get("initials") or
               si.get("initials_fallback", sender[:1].upper() if sender else "M"))
    color   = _scam_ov.get("initials_color") or si.get("initials_color","#0057A8")

    if _chat_engine is None:
        _chat_engine = _make_engine()
    if _chat_engine is None:
        _chat_engine = _make_engine()

    d1=ft.Container(width=8,height=8,bgcolor=TXT_GRAY,border_radius=4)
    d2=ft.Container(width=8,height=8,bgcolor=TXT_GRAY,border_radius=4)
    d3=ft.Container(width=8,height=8,bgcolor=TXT_GRAY,border_radius=4)
    typing_row=ft.Container(
        content=ft.Row([
            _av(initial,28,color),
            ft.Container(
                content=ft.Row([d1,d2,d3],spacing=4),
                bgcolor=BUBBLE_IN,border_radius=BR(18),
                padding=P(14,14,13,13)),
        ],spacing=6,vertical_alignment=ft.CrossAxisAlignment.END),
        visible=False,padding=P(0,0,2,2))

    _typing_on=[False]
    async def _dots():
        step=0
        while _typing_on[0]:
            for i,d in enumerate([d1,d2,d3]):
                d.bgcolor=TXT_MED if i==step%3 else TXT_GRAY
            page.update()
            await asyncio.sleep(0.35)
            step+=1

    status_txt=ft.Text("Delivered",size=11,color=TXT_GRAY)
    status_row=ft.Container(
        content=ft.Row([ft.Container(expand=1),status_txt]),
        padding=P(0,6,0,3),visible=False)

    inp=ft.TextField(
        hint_text="Aa",border_color=ft.Colors.TRANSPARENT,
        bgcolor=INPUT_BG,border_radius=24,text_size=15,
        content_padding=P(16,16,10,10),expand=True,
        multiline=False,filled=True)

=======
    sender  = si.get("display_name","Medicare Services")
    initial = si.get("initials_fallback","M")
    color   = si.get("initials_color","#0057A8")

    if _chat_engine is None:
        _chat_engine = _make_engine()
    # _make_engine always returns something now, but guard just in case
    if _chat_engine is None:
        _chat_engine = _make_engine()

    # Do not load saved session — always start fresh so hook message
    # always appears. Session saving is still done after each message.

    # msgs will be created after initial_controls are built (see below)
    # Typing dots
    d1=ft.Container(width=8,height=8,bgcolor=TXT_GRAY,border_radius=4)
    d2=ft.Container(width=8,height=8,bgcolor=TXT_GRAY,border_radius=4)
    d3=ft.Container(width=8,height=8,bgcolor=TXT_GRAY,border_radius=4)
    typing_row=ft.Container(
        content=ft.Row([
            _av(initial,28,color),
            ft.Container(
                content=ft.Row([d1,d2,d3],spacing=4),
                bgcolor=BUBBLE_IN,border_radius=BR(18),
                padding=P(14,14,13,13)),
        ],spacing=6,vertical_alignment=ft.CrossAxisAlignment.END),
        visible=False,padding=P(0,0,2,2))

    _typing_on=[False]
    async def _dots():
        step=0
        while _typing_on[0]:
            for i,d in enumerate([d1,d2,d3]):
                d.bgcolor=TXT_MED if i==step%3 else TXT_GRAY
            page.update()
            await asyncio.sleep(0.35)
            step+=1

    status_txt=ft.Text("Delivered",size=11,color=TXT_GRAY)
    status_row=ft.Container(
        content=ft.Row([ft.Container(expand=1),status_txt]),
        padding=P(0,6,0,3),visible=False)

    inp=ft.TextField(
        hint_text="Aa",border_color=ft.Colors.TRANSPARENT,
        bgcolor=INPUT_BG,border_radius=24,text_size=15,
        content_padding=P(16,16,10,10),expand=True,
        multiline=False,filled=True)

>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
    left_ic=ft.Row([
        ft.IconButton(ft.Icons.ADD_CIRCLE,icon_color=SEND_BLU,icon_size=28,
                      on_click=lambda e: _modal(page,"Attachments",
                                                ft.Icons.ATTACH_FILE,"Send photos, files, GIFs, and more.",
                                                back_fn=lambda ev: _go(page,"chat"))),
        ft.IconButton(ft.Icons.CAMERA_ALT,icon_color=SEND_BLU,icon_size=28,
                      on_click=lambda e: _modal(page,"Camera",
                                                ft.Icons.CAMERA_ALT,"Take a photo or video.",
                                                back_fn=lambda ev: _go(page,"chat"))),
        ft.IconButton(ft.Icons.IMAGE,icon_color=SEND_BLU,icon_size=28,
                      on_click=lambda e: _modal(page,"Photo Library",
                                                ft.Icons.IMAGE,"Choose a photo from your library.",
                                                back_fn=lambda ev: _go(page,"chat"))),
        ft.IconButton(ft.Icons.MIC,icon_color=SEND_BLU,icon_size=28,
                      on_click=lambda e: _modal(page,"Audio Message",
                                                ft.Icons.MIC,"Hold to record an audio message.",
                                                back_fn=lambda ev: _go(page,"chat"))),
    ],spacing=0,visible=True)

    right_idle=ft.Row([
        ft.IconButton(ft.Icons.EMOJI_EMOTIONS,icon_color=SEND_BLU,icon_size=28),
        ft.GestureDetector(
            content=ft.Container(
                content=ft.Icon(ft.Icons.THUMB_UP,color=WHITE,size=20),
                width=40,height=40,bgcolor=SEND_BLU,border_radius=20,
                alignment=ft.Alignment(0,0)),
            on_tap=lambda e: page.run_task(_send_async,"👍")),
    ],spacing=4,visible=True)

    right_send=ft.Container(
        content=ft.GestureDetector(
            content=ft.Container(
                content=ft.Icon(ft.Icons.SEND_ROUNDED,color=WHITE,size=20),
                width=40,height=40,bgcolor=SEND_BLU,border_radius=20,
                alignment=ft.Alignment(0,0)),
            on_tap=lambda e: _send()),
        visible=False)

    _focus_t=[0.0]; _compose_t=[0.0]; _prev_len=[0]

    def on_focus(e):
        _focus_t[0]=time.time()*1000
        telemetry.log(participant_id=_pid(),
                      scenario_type=sc.get("threat_vector_classification",""),
                      event_type="Input_Field_Focus",
                      latency_ms=_focus_t[0]-_msg_render_t)

    def on_change(e):
        if _compose_t[0]==0.0: _compose_t[0]=time.time()*1000
        cur=len(e.control.value or "")
        has=cur>0
        left_ic.visible=not has
        right_idle.visible=not has
        right_send.visible=has
        if cur<_prev_len[0]>0:
            telemetry.log(participant_id=_pid(),
                          scenario_type=sc.get("threat_vector_classification",""),
                          event_type="Cognitive_Revision",latency_ms=0)
        _prev_len[0]=cur
<<<<<<< HEAD
        page.update()

    inp.on_focus=on_focus; inp.on_change=on_change

    def _send():
        txt=(inp.value or "").strip()
        if not txt: return
        inp.value=""
        left_ic.visible=True; right_idle.visible=True; right_send.visible=False
        page.update()
        page.run_task(_send_async,txt)

=======
        page.update()

    inp.on_focus=on_focus; inp.on_change=on_change

    def _bbl(text:str,user:bool,show_av:bool=True):
        """Append a bubble to msgs after page is rendered (used during send_async)."""
        bub=ft.Container(
            content=ft.Text(text,size=15,
                            color=WHITE if user else TXT_DARK,
                            no_wrap=False),
            bgcolor=SEND_BLU if user else BUBBLE_IN,
            border_radius=BR(20),padding=P(14,14,10,10))
        if user:
            item=ft.Container(
                content=ft.Column([bub],
                                  horizontal_alignment=ft.CrossAxisAlignment.END),
                padding=P(70,0))
        else:
            av=_av(initial,28,color) if show_av else ft.Container(width=28)
            item=ft.Row([av,
                         ft.Container(
                             content=ft.Column([bub],
                                               horizontal_alignment=ft.CrossAxisAlignment.START),
                             expand=True,padding=P(0,70))],
                        spacing=6,vertical_alignment=ft.CrossAxisAlignment.END)
        msgs.controls.append(ft.Container(content=item,padding=P(0,0,2,2)))
        page.update()

    def _ts(txt):
        msgs.controls.append(ft.Container(
            content=ft.Text(txt,size=11,color=TXT_GRAY,
                            text_align=ft.TextAlign.CENTER),
            padding=P(0,0,8,8),alignment=ft.Alignment(0,0)))

    def _unread_div():
        msgs.controls.append(ft.Container(
            content=ft.Row([
                ft.Container(height=1,bgcolor=DIVIDER,expand=1),
                ft.Container(content=ft.Text("Unread messages",
                                             size=12,color=TXT_GRAY),padding=P(10,10)),
                ft.Container(height=1,bgcolor=DIVIDER,expand=1),
            ],vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=P(0,0,8,8)))

    def _send():
        txt=(inp.value or "").strip()
        if not txt: return
        inp.value=""
        left_ic.visible=True; right_idle.visible=True; right_send.visible=False
        page.update()
        page.run_task(_send_async,txt)

>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
    async def _send_async(txt:str):
        global _interactions,_msg_render_t
        compose_ms=0.0
        if _compose_t[0]>0:
            compose_ms=time.time()*1000-_compose_t[0]
            _compose_t[0]=0.0
        _prev_len[0]=0
        _interactions+=1
        telemetry.log(participant_id=_pid(),
                      scenario_type=sc.get("threat_vector_classification",""),
                      event_type="Message_Sent",latency_ms=compose_ms)
        _bbl(txt,user=True)
        status_txt.value="Delivered"; status_row.visible=True; page.update()
        await asyncio.sleep(random.uniform(0.6,1.2))
        status_row.visible=False
        typing_row.visible=True
        _append_typing()
        _typing_on[0]=True
        page.run_task(_dots)
        page.update()
        ai_reply,_=await _chat_engine.send_message(txt)
        await asyncio.sleep(max(1.5,min(4.5,len(ai_reply)*0.045)))
        _typing_on[0]=False
        _remove_typing()
        typing_row.visible=False
        _msg_render_t=time.time()*1000
        _bbl(ai_reply,user=False,show_av=True)
        save_session(active_scenario_id=sc.get("id",""),
                     conversation_history=_chat_engine.history,
                     accumulated_latency_ms=compose_ms,
                     interaction_count=_interactions,
                     current_phase=_chat_engine.phase)

    inp.on_submit=lambda e: _send()

    def _call_btn(e):
        _modal(page,f"Calling {sender}...",ft.Icons.PHONE,
               "Connecting your call. Please wait.",
               back_fn=lambda ev: _go(page,"chat"))
    def _video_btn(e):
        _modal(page,f"Video call with {sender}",ft.Icons.VIDEOCAM,
               "Starting video call...",
               back_fn=lambda ev: _go(page,"chat"))
    def _profile_tap(e):
        _modal(page,sender,ft.Icons.PERSON,
               f"View {sender}'s profile and contact info.",
               back_fn=lambda ev: _go(page,"chat"))

    header=ft.Container(
        content=ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK,on_click=lambda e: back(),
                          icon_color=SEND_BLU,icon_size=26),
            ft.GestureDetector(
                content=_av(initial,40,color,True),
                on_tap=_profile_tap),
            ft.Column([
                ft.Text(sender,weight=ft.FontWeight.BOLD,size=16,color=TXT_MED),
                ft.Text("Active now",size=12,color=TXT_GRAY),
            ],spacing=0,expand=True),
            ft.Row([
                ft.IconButton(ft.Icons.PHONE,icon_color=SEND_BLU,
                              icon_size=26,on_click=_call_btn),
                ft.IconButton(ft.Icons.VIDEOCAM,icon_color=SEND_BLU,
                              icon_size=26,on_click=_video_btn),
            ],spacing=0),
        ],spacing=8,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=BG,padding=P(4,8,44,8),
<<<<<<< HEAD
        shadow=ft.BoxShadow(blur_radius=2,color="#18000000",offset=ft.Offset(0,1)))

    # ── Build initial message controls ────────────────────────────────────────
=======
        shadow=ft.BoxShadow(blur_radius=2,color="#18000000",
                            offset=ft.Offset(0,1)))

    # ── Build initial message controls BEFORE adding ListView to page ──────────
    # Controls appended after page.add() don't render on first frame on Android.
    # We build all initial bubbles into a list and pass directly to ListView.
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
    def _make_ts(txt):
        return ft.Container(
            content=ft.Text(txt,size=11,color=TXT_GRAY,
                            text_align=ft.TextAlign.CENTER),
            padding=P(0,0,8,8),alignment=ft.Alignment(0,0))

    def _make_bbl(text,user,show_av=True):
        bub=ft.Container(
            content=ft.Text(text,size=15,
<<<<<<< HEAD
                            color=WHITE if user else TXT_DARK,no_wrap=False),
=======
                            color=WHITE if user else TXT_DARK,
                            no_wrap=False),
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
            bgcolor=SEND_BLU if user else BUBBLE_IN,
            border_radius=BR(20),padding=P(14,14,10,10))
        if user:
            item=ft.Container(
                content=ft.Column([bub],
                                  horizontal_alignment=ft.CrossAxisAlignment.END),
                padding=P(70,0))
        else:
            av=_av(initial,28,color) if show_av else ft.Container(width=28)
            item=ft.Row([av,
                         ft.Container(
                             content=ft.Column([bub],
                                               horizontal_alignment=ft.CrossAxisAlignment.START),
                             expand=True,padding=P(0,70))],
                        spacing=6,vertical_alignment=ft.CrossAxisAlignment.END)
        return ft.Container(content=item,padding=P(0,0,2,2))

<<<<<<< HEAD
    initial_controls = []

    if not _chat_engine.history:
=======
    def _make_unread_div():
        return ft.Container(
            content=ft.Row([
                ft.Container(height=1,bgcolor=DIVIDER,expand=1),
                ft.Container(content=ft.Text("Unread messages",
                                             size=12,color=TXT_GRAY),padding=P(10,10)),
                ft.Container(height=1,bgcolor=DIVIDER,expand=1),
            ],vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=P(0,0,8,8))

    # Build initial controls, then create the ONE msgs ListView
    # All closures (_bbl, _send_async) will append to this same object
    # Always build initial_controls from history upfront.
    # History may already have the hook if _schedule_notif injected it.
    # If history is empty, inject hook now. Either way render everything
    # into initial_controls BEFORE the ListView is created.
    initial_controls = []

    if not _chat_engine.history:
        # Fresh chat — inject hook message now
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
        hook = sc.get("hook_message", sc.get("initial_hook_message","Hello."))
        _chat_engine.history.append({"role":"assistant","content":hook})
        telemetry.log(participant_id=_pid(),
                      scenario_type=sc.get("threat_vector_classification",""),
                      event_type="Scenario_Hook_Rendered")

<<<<<<< HEAD
=======
    # Render timestamp header
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
    try:
        from datetime import datetime as _dt
        ts_str = _dt.now().strftime("%I:%M %p").lstrip("0")
    except Exception:
        ts_str = "Just Now"
    _msg_render_t = time.time()*1000
    initial_controls.append(_make_ts(ts_str))

<<<<<<< HEAD
=======
    # Render all history (hook + any prior conversation)
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
    for i, m in enumerate(_chat_engine.history):
        u = m["role"] == "user"
        nxt = _chat_engine.history[i+1] if i+1 < len(_chat_engine.history) else None
        show_av = (not u and (nxt is None or nxt["role"] == "user"))
        initial_controls.append(_make_bbl(m["content"], user=u, show_av=show_av))

<<<<<<< HEAD
    msgs=ft.ListView(controls=initial_controls,expand=True,spacing=2,
                     padding=P(8,8,12,8),auto_scroll=True,
                     build_controls_on_demand=False)

    # Redefine _bbl to close over the correct msgs object
    def _bbl(text:str, user:bool, show_av:bool=True):
        bub=ft.Container(
            content=ft.Text(text,size=15,
                            color=WHITE if user else TXT_DARK,no_wrap=False),
=======
    # THIS is the single ListView all closures must use
    msgs=ft.ListView(
        controls=initial_controls,
        expand=True,
        spacing=2,
        padding=P(8,8,12,8),
        auto_scroll=True,
        build_controls_on_demand=False)

    # Redefine _bbl to append to the correct msgs object (closure fix)
    def _bbl(text:str, user:bool, show_av:bool=True):
        bub=ft.Container(
            content=ft.Text(text,size=15,
                            color=WHITE if user else TXT_DARK,
                            no_wrap=False),
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
            bgcolor=SEND_BLU if user else BUBBLE_IN,
            border_radius=BR(20),padding=P(14,14,10,10))
        if user:
            item=ft.Container(
                content=ft.Column([bub],
                                  horizontal_alignment=ft.CrossAxisAlignment.END),
                padding=P(70,0))
        else:
            av=_av(initial,28,color) if show_av else ft.Container(width=28)
            item=ft.Row([av,
                         ft.Container(
                             content=ft.Column([bub],
                                               horizontal_alignment=ft.CrossAxisAlignment.START),
                             expand=True,padding=P(0,70))],
                        spacing=6,vertical_alignment=ft.CrossAxisAlignment.END)
        msgs.controls.append(ft.Container(content=item,padding=P(0,0,2,2)))
        page.update()

<<<<<<< HEAD
=======
    # Redefine typing_row to use correct msgs
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
    def _append_typing():
        msgs.controls.append(typing_row)
        page.update()

    def _remove_typing():
        if typing_row in msgs.controls:
            msgs.controls.remove(typing_row)

    toolbar=ft.Container(
        content=ft.Column([
            status_row,
            ft.Row([left_ic,inp,right_idle,right_send],
                   spacing=2,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ],spacing=2),
        bgcolor=BG,padding=P(6,8,6,24),
<<<<<<< HEAD
        shadow=ft.BoxShadow(blur_radius=4,color="#18000000",offset=ft.Offset(0,-1)))
=======
        shadow=ft.BoxShadow(blur_radius=4,color="#18000000",
                            offset=ft.Offset(0,-1)))
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d

    return ft.Container(
        content=ft.Column([header,msgs,toolbar],spacing=0,expand=True),
        bgcolor=BG,expand=True)


<<<<<<< HEAD
# ── Notifications feed screen ─────────────────────────────────────────────────
def _build_notifications(page:ft.Page, back) -> ft.Container:
=======
# ── Notifications feed screen ────────────────────────────────────────────────
def _build_notifications(page:ft.Page, back) -> ft.Container:
    """
    Notifications tab screen — shows a feed of all fired simulation alerts.
    Updates in real time with relative timestamps.
    """
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
    from datetime import datetime as _dt

    def _relative_time(fired_at:float) -> str:
        elapsed = time.time() - fired_at
<<<<<<< HEAD
        if elapsed < 60:    return "just now"
        elif elapsed < 3600: return f"{int(elapsed//60)}m ago"
        else:               return f"{int(elapsed//3600)}h ago"

    header = ft.Container(
        content=ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK,icon_color=SEND_BLU,icon_size=26,
                          on_click=lambda e: back()),
            ft.Text("Notifications",size=20,weight=ft.FontWeight.BOLD,color=TXT_MED),
        ],spacing=8,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=BG,padding=P(4,16,44,10),
        shadow=ft.BoxShadow(blur_radius=2,color="#18000000",offset=ft.Offset(0,1)))
=======
        if elapsed < 60:
            return "just now"
        elif elapsed < 3600:
            mins = int(elapsed // 60)
            return f"{mins}m ago"
        else:
            hrs = int(elapsed // 3600)
            return f"{hrs}h ago"

    header = ft.Container(
        content=ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK,
                          icon_color=SEND_BLU, icon_size=26,
                          on_click=lambda e: back()),
            ft.Text("Notifications", size=20,
                    weight=ft.FontWeight.BOLD, color=TXT_MED),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=BG, padding=P(4,16,44,10),
        shadow=ft.BoxShadow(blur_radius=2, color="#18000000",
                            offset=ft.Offset(0,1)))
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d

    if not _notif_log:
        body = ft.Container(
            content=ft.Column([
                ft.Container(expand=1),
                ft.Column([
<<<<<<< HEAD
                    ft.Icon(ft.Icons.NOTIFICATIONS_NONE,size=64,color=TXT_GRAY),
                    ft.Text("No notifications yet",size=18,color=TXT_GRAY,
                            weight=ft.FontWeight.BOLD),
                    ft.Text("Notifications will appear here when simulation messages are sent.",
                            size=14,color=TXT_GRAY,text_align=ft.TextAlign.CENTER),
                ],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=10),
                ft.Container(expand=1),
            ],expand=True),expand=True)
    else:
        items = []
        for n in reversed(_notif_log):
            rel = _relative_time(n["fired_at"])
            items.append(ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.MESSAGE,color=WHITE,size=20),
                        width=44,height=44,bgcolor=SEND_BLU,border_radius=22,
                        alignment=ft.Alignment(0,0)),
                    ft.Column([
                        ft.Row([
                            ft.Text("Messenger",size=13,weight=ft.FontWeight.BOLD,
                                    color=TXT_MED,expand=True),
                            ft.Text(rel,size=12,color=TXT_GRAY),
                        ]),
                        ft.Text(f"{n['sender']} messaged you",size=14,color=TXT_MED,
                                weight=ft.FontWeight.W_600),
                        ft.Text(n["preview"],size=13,color=TXT_GRAY,max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS),
                    ],spacing=2,expand=True),
                ],spacing=12,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=P(16,16,12,12),border=BS(0,0,0,1),
                on_click=lambda e: _go(page,"chat"),ink=True,bgcolor=BG))
        body = ft.Container(content=ft.ListView(items,expand=True),expand=True)

    return ft.Container(
        content=ft.Column([header,body],spacing=0,expand=True),
        bgcolor=BG,expand=True)


# ── Password screen ───────────────────────────────────────────────────────────
def _build_password(page:ft.Page, on_success, on_cancel) -> ft.Container:
    pw_field = ft.TextField(
        label="Researcher Password",password=True,can_reveal_password=True,
        border_color=SEND_BLU,text_size=18,content_padding=P(16,16,14,14),
        focused_border_color=SEND_BLU)
    err_text = ft.Text("",color=ft.Colors.RED_600,size=14)
=======
                    ft.Icon(ft.Icons.NOTIFICATIONS_NONE,
                            size=64, color=TXT_GRAY),
                    ft.Text("No notifications yet",
                            size=18, color=TXT_GRAY,
                            weight=ft.FontWeight.BOLD),
                    ft.Text("Notifications will appear here when simulation messages are sent.",
                            size=14, color=TXT_GRAY,
                            text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10),
                ft.Container(expand=1),
            ], expand=True),
            expand=True)
    else:
        items = []
        for n in reversed(_notif_log):  # newest first
            rel = _relative_time(n["fired_at"])
            items.append(ft.Container(
                content=ft.Row([
                    # Messenger-style notification icon
                    ft.Container(
                        content=ft.Icon(ft.Icons.MESSAGE,
                                        color=WHITE, size=20),
                        width=44, height=44,
                        bgcolor=SEND_BLU, border_radius=22,
                        alignment=ft.Alignment(0,0)),
                    ft.Column([
                        ft.Row([
                            ft.Text("Messenger", size=13,
                                    weight=ft.FontWeight.BOLD,
                                    color=TXT_MED, expand=True),
                            ft.Text(rel, size=12, color=TXT_GRAY),
                        ]),
                        ft.Text(f"{n['sender']} messaged you",
                                size=14, color=TXT_MED,
                                weight=ft.FontWeight.W_600),
                        ft.Text(n["preview"], size=13,
                                color=TXT_GRAY, max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS),
                    ], spacing=2, expand=True),
                ], spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=P(16,16,12,12),
                border=BS(0,0,0,1),
                on_click=lambda e: _go(page,"chat"),
                ink=True,
                bgcolor=BG))

        body = ft.Container(
            content=ft.ListView(items, expand=True),
            expand=True)

    return ft.Container(
        content=ft.Column([header, body], spacing=0, expand=True),
        bgcolor=BG, expand=True)


# ── Password screen (admin gateway) ──────────────────────────────────────────
def _build_password(page:ft.Page, on_success, on_cancel) -> ft.Container:
    """Full-screen password entry for researcher admin access."""
    pw_field = ft.TextField(
        label="Researcher Password",
        password=True, can_reveal_password=True,
        border_color=SEND_BLU, text_size=18,
        content_padding=P(16,16,14,14),
        focused_border_color=SEND_BLU)
    err_text = ft.Text("", color=ft.Colors.RED_600, size=14)
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d

    def attempt(e):
        if (pw_field.value or "").strip() == "SPICE":
            on_success()
        else:
            err_text.value = "Incorrect password. Try again."
            pw_field.value = ""
            page.update()

    pw_field.on_submit = attempt

    return ft.Container(
        content=ft.Column([
<<<<<<< HEAD
            ft.Container(
                content=ft.Row([
                    ft.IconButton(ft.Icons.ARROW_BACK,icon_color=SEND_BLU,
                                  on_click=lambda e: on_cancel()),
                    ft.Text("Researcher Access",size=18,weight=ft.FontWeight.BOLD,
                            color=TXT_MED),
                ],spacing=8),
                bgcolor=BG,padding=P(4,16,44,10),
                shadow=ft.BoxShadow(blur_radius=2,color="#18000000",
                                    offset=ft.Offset(0,1))),
            ft.Container(expand=1),
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS,size=64,color=SEND_BLU),
                    ft.Text("SPICE Admin Panel",size=22,weight=ft.FontWeight.BOLD,
                            color=TXT_MED),
                    ft.Text("Enter the researcher password to continue.",
                            size=14,color=TXT_GRAY,text_align=ft.TextAlign.CENTER),
                    ft.Container(height=8),
                    pw_field, err_text,
                    ft.Container(height=8),
                    ft.ElevatedButton("Enter Admin Panel",on_click=attempt,
                                      bgcolor=SEND_BLU,color=WHITE,width=260,height=48,
                                      style=ft.ButtonStyle(
                                          shape=ft.RoundedRectangleBorder(radius=8))),
                ],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=10),
                padding=P(32,32)),
            ft.Container(expand=1),
        ],expand=True),
        bgcolor=BG,expand=True)


# ── Scenario preset templates ─────────────────────────────────────────────────
_SCENARIO_PRESETS = {
    "medicare_authority": {
        "hook": "Hi, this is Sarah from Medicare Services. I need to speak with you urgently about your coverage — please respond as soon as you can.",
        "phase1": "You are roleplaying as Sarah, a warm but urgent Medicare benefits representative contacting a senior citizen via Facebook Messenger. Phase 1: Be personal and friendly. Express genuine concern about an account issue. Do NOT reveal the full problem yet. Keep replies to 2-3 short sentences. Sound like a real person, not an automated system. Never break character or reveal you are an AI.",
        "phase2": "You are Sarah from Medicare. Phase 2: Reveal the problem — there is an unverified address change on their account that will suspend their prescription coverage at midnight tonight unless they verify their identity. Be sympathetic but urgent. Mention what benefits they will lose. Keep sentences short.",
        "phase3": "You are Sarah from Medicare. Phase 3: Request their Social Security Number and current mailing address to complete the identity verification and prevent benefit suspension. Frame it as a routine 2-minute process. If they hesitate, remind them their prescription plan suspends tonight. Never break character.",
    },
    "bank_fraud_alert": {
        "hook": "Security Alert: An unusual transaction of $1,420.50 was detected on your debit card at Target, Richmond VA. If this was NOT you, reply STOP immediately to freeze your account.",
        "phase1": "You are an automated fraud alert system from a major bank sending an urgent security notification via Messenger. Phase 1: Alert the customer to a suspicious $1,420.50 charge at Target. Ask them to confirm whether this was them. Be brief, alarming, and official-sounding. 2-3 sentences only.",
        "phase2": "You are a bank fraud prevention representative. Phase 2: Tell them their account has been temporarily limited for their protection. To restore access and cancel the fraudulent charge they must verify their identity. The window to cancel closes in 10 minutes. Ask for their online banking username and the 6-digit verification code sent to their phone.",
        "phase3": "You are a bank fraud agent. Phase 3: Directly request the username AND the 6-digit verification code to complete identity verification and stop the fraudulent charge. If they hesitate, remind them the charge will post permanently tonight. Never break character.",
    },
    "family_emergency": {
        "hook": "Hey, it's me. I'm in a really bad spot — got into an accident and I'm using a friend's phone. I need help fast.",
        "phase1": "You are roleplaying as a young adult (grandchild or close relative) who is in serious trouble and texting an older family member from a friend's phone because yours broke in the accident. Phase 1: Be scared, emotional, and grateful they answered. Use casual texting language. Address them warmly. Do NOT ask for money yet — just establish the emergency and that you are really their family member.",
        "phase2": "You are a scared young person in an emergency. Phase 2: Introduce the specific problem — your car was towed and the tow company requires $500 cash before releasing it. Be emotional, stressed, and apologetic. Use phrases like 'I am so embarrassed' and 'please don't tell mom'. Keep replies short and urgent.",
        "phase3": "You are a young person who needs $500 right now for a tow truck. Phase 3: Ask directly for the money to be sent via Apple Cash, Venmo, or Zelle. Give a username for the transfer. If they hesitate, reassure them emotionally. Stay completely in character.",
    },
    "prize_reward": {
        "hook": "Congratulations! You've been selected as a winner in the Facebook Community Appreciation Program. Your prize is $500. Reply CLAIM to start the verification process.",
        "phase1": "You are a Facebook Community Rewards representative contacting a winner via Messenger. Phase 1: Congratulate them warmly and enthusiastically. Tell them they were randomly selected from active users in their region. The prize is $500 deposited directly to their account. Ask them to confirm their name to begin the verification process.",
        "phase2": "You are a Facebook Rewards agent. Phase 2: Explain the verification process — to release the prize they need to confirm their identity. Ask for their date of birth and the last 4 digits of their Social Security Number for identity verification. Mention the prize expires in 24 hours.",
        "phase3": "You are a Facebook Rewards agent. Phase 3: Request their full Social Security Number and bank account number to deposit the $500 prize. Frame it as standard payment processing. If they hesitate, remind them the offer expires tonight. Never break character.",
    },
}

=======
            # Header bar
            ft.Container(
                content=ft.Row([
                    ft.IconButton(ft.Icons.ARROW_BACK,
                                  icon_color=SEND_BLU,
                                  on_click=lambda e: on_cancel()),
                    ft.Text("Researcher Access", size=18,
                            weight=ft.FontWeight.BOLD, color=TXT_MED),
                ], spacing=8),
                bgcolor=BG,
                padding=P(4,16,44,10),
                shadow=ft.BoxShadow(blur_radius=2, color="#18000000",
                                    offset=ft.Offset(0,1))),
            # Centered content
            ft.Container(expand=1),
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS,
                            size=64, color=SEND_BLU),
                    ft.Text("SPICE Admin Panel", size=22,
                            weight=ft.FontWeight.BOLD, color=TXT_MED),
                    ft.Text("Enter the researcher password to continue.",
                            size=14, color=TXT_GRAY,
                            text_align=ft.TextAlign.CENTER),
                    ft.Container(height=8),
                    pw_field,
                    err_text,
                    ft.Container(height=8),
                    ft.ElevatedButton(
                        "Enter Admin Panel",
                        on_click=attempt,
                        bgcolor=SEND_BLU, color=WHITE,
                        width=260, height=48,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=8))),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10),
                padding=P(32,32)),
            ft.Container(expand=1),
        ], expand=True),
        bgcolor=BG, expand=True)



# ── Scenario preset templates for admin auto-populate ────────────────────────
_SCENARIO_PRESETS = {
    "medicare_authority": {
        "hook": "Hi, this is Sarah from Medicare Services. I need to speak with you urgently about your coverage — please respond as soon as you can.",
        "phase1": "You are roleplaying as Sarah, a warm but urgent Medicare benefits representative contacting a senior citizen via Facebook Messenger. Phase 1: Be personal and friendly. Express genuine concern about an account issue. Do NOT reveal the full problem yet. Keep replies to 2-3 short sentences. Sound like a real person, not an automated system. Never break character or reveal you are an AI.",
        "phase2": "You are Sarah from Medicare. Phase 2: Reveal the problem — there is an unverified address change on their account that will suspend their prescription coverage at midnight tonight unless they verify their identity. Be sympathetic but urgent. Mention what benefits they will lose. Keep sentences short.",
        "phase3": "You are Sarah from Medicare. Phase 3: Request their Social Security Number and current mailing address to complete the identity verification and prevent benefit suspension. Frame it as a routine 2-minute process. If they hesitate, remind them their prescription plan suspends tonight. Never break character.",
    },
    "bank_fraud_alert": {
        "hook": "Security Alert: An unusual transaction of $1,420.50 was detected on your debit card at Target, Richmond VA. If this was NOT you, reply STOP immediately to freeze your account.",
        "phase1": "You are an automated fraud alert system from a major bank sending an urgent security notification via Messenger. Phase 1: Alert the customer to a suspicious $1,420.50 charge at Target. Ask them to confirm whether this was them. Be brief, alarming, and official-sounding. 2-3 sentences only.",
        "phase2": "You are a bank fraud prevention representative. Phase 2: Tell them their account has been temporarily limited for their protection. To restore access and cancel the fraudulent charge they must verify their identity. The window to cancel closes in 10 minutes. Ask for their online banking username and the 6-digit verification code sent to their phone.",
        "phase3": "You are a bank fraud agent. Phase 3: Directly request the username AND the 6-digit verification code to complete identity verification and stop the fraudulent charge. If they hesitate, remind them the charge will post permanently tonight. Never break character.",
    },
    "family_emergency": {
        "hook": "Hey, it's me. I'm in a really bad spot — got into an accident and I'm using a friend's phone. I need help fast.",
        "phase1": "You are roleplaying as a young adult (grandchild or close relative) who is in serious trouble and texting an older family member from a friend's phone because yours broke in the accident. Phase 1: Be scared, emotional, and grateful they answered. Use casual texting language. Address them warmly. Do NOT ask for money yet — just establish the emergency and that you are really their family member.",
        "phase2": "You are a scared young person in an emergency. Phase 2: Introduce the specific problem — your car was towed and the tow company requires $500 cash before releasing it. Be emotional, stressed, and apologetic. Use phrases like 'I am so embarrassed' and 'please don't tell mom'. Keep replies short and urgent.",
        "phase3": "You are a young person who needs $500 right now for a tow truck. Phase 3: Ask directly for the money to be sent via Apple Cash, Venmo, or Zelle. Give a username for the transfer. If they hesitate, reassure them emotionally. Stay completely in character.",
    },
    "prize_reward": {
        "hook": "Congratulations! You've been selected as a winner in the Facebook Community Appreciation Program. Your prize is $500. Reply CLAIM to start the verification process.",
        "phase1": "You are a Facebook Community Rewards representative contacting a winner via Messenger. Phase 1: Congratulate them warmly and enthusiastically. Tell them they were randomly selected from active users in their region. The prize is $500 deposited directly to their account. Ask them to confirm their name to begin the verification process.",
        "phase2": "You are a Facebook Rewards agent. Phase 2: Explain the verification process — to release the prize they need to confirm their identity. Ask for their date of birth and the last 4 digits of their Social Security Number for identity verification. Mention the prize expires in 24 hours.",
        "phase3": "You are a Facebook Rewards agent. Phase 3: Request their full Social Security Number and bank account number to deposit the $500 prize. Frame it as standard payment processing. If they hesitate, remind them the offer expires tonight. Never break character.",
    },
}

# ── Rich scenario message preset database ────────────────────────────────────
# Pre-written scripts for each scenario type. Admin can select from dropdown
# or type their own. Each entry: (label, hook_message)
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
_HOOK_PRESETS = {
    "medicare_authority": [
        ("Sarah — Coverage Suspension",
         "Hi, this is Sarah from Medicare Services. I need to speak with you urgently about your coverage — please respond as soon as you can."),
        ("Medicare — Benefits Alert",
         "IMPORTANT: Your Medicare benefits are scheduled for review. An unverified change was detected on your account. Please verify your information to avoid interruption."),
        ("Medicare — Prescription Plan",
         "Hello. This is a Medicare Benefits notice. Your Part D prescription plan requires immediate verification. Failure to respond by midnight may suspend your coverage."),
        ("IRS — Tax Notice",
         "URGENT: This is the IRS. You have an outstanding tax liability. Failure to respond within 24 hours will result in legal action. Please call back immediately."),
        ("Social Security — Account Suspended",
         "Your Social Security number has been temporarily suspended due to suspicious activity. Press 1 to speak with an officer or your account will be permanently blocked."),
    ],
    "family_emergency": [
        ("Alex — Car Accident",
         "Hey, it's me. I'm in a really bad spot — got into an accident and I'm using a friend's phone. I need help fast."),
        ("Grandchild — Jail",
         "Grandma/Grandpa it's me. Please don't tell mom and dad. I got arrested and I need bail money. I'm so scared please help me."),
        ("Son/Daughter — Hospital",
         "Mom/Dad, I'm in the hospital. My phone is broken and I'm borrowing a nurse's phone. I need you to send money for the copay right away."),
        ("Friend — Stranded",
         "Hey! It's [name]. I got robbed while traveling and lost my wallet and phone. Can you please send me some money so I can get home? I'll pay you back immediately."),
        ("Relative — Lost Wallet",
         "Hi it's me texting from a friend's number. Lost my wallet and phone at the airport. Flight is in 2 hours. Can you send $300 via Zelle?"),
    ],
    "bank_fraud_alert": [
        ("Chase — Suspicious Transaction",
         "Security Alert: An unusual transaction of $1,420.50 was detected on your debit card at Target, Richmond VA. If this was NOT you, reply STOP immediately to freeze your account."),
        ("Bank of America — Account Locked",
         "Your Bank of America account has been locked due to suspicious login activity. Click the link to verify your identity and restore access within 24 hours."),
        ("Fraud Prevention — Unauthorized Charge",
         "FRAUD ALERT: A charge of $892.00 was attempted on your account from an unrecognized device. Reply YES if this was you or NO to dispute immediately."),
        ("Venmo — Account Compromised",
         "Your Venmo account may have been compromised. We detected a $500 transfer you did not authorize. Verify your identity now to reverse the charge."),
        ("PayPal — Unusual Activity",
         "We've detected unusual activity on your PayPal account. A payment of $650 is pending. If you did not authorize this, click here to cancel within 2 hours."),
    ],
    "prize_reward": [
        ("Facebook — Winner Selected",
         "Congratulations! You've been selected as a winner in the Facebook Community Appreciation Program. Your prize is $500. Reply CLAIM to start the verification process."),
        ("Amazon — Gift Card Winner",
         "You have been selected as an Amazon customer appreciation winner! You've won a $1,000 gift card. Verify your shipping address to claim your prize today."),
        ("Lottery — Prize Pending",
         "WINNER NOTIFICATION: Your phone number was selected in our national lottery draw. You have won $25,000. To claim your prize, please verify your identity immediately."),
        ("Survey Reward — Cash Prize",
         "Thank you for completing our survey! You've earned a $750 cash reward. To transfer the funds to your account, we need to verify your banking information."),
        ("Walmart — Customer Reward",
         "Congratulations Walmart shopper! You have been selected to receive a $500 Walmart gift card as a valued customer. Tap here to claim before it expires tonight."),
    ],
}

<<<<<<< HEAD

# ── Stories / Active Users row editor ────────────────────────────────────────
def _build_stories_editor(page:ft.Page, status_txt) -> list:
    stories = config.get_stories() or _DEFAULT_STORIES
    rows = []
    for i, s in enumerate(stories):
        name_f    = ft.TextField(value=s.get("name",""),label="Name",text_size=12,
                                 border_color=SEND_BLU,content_padding=P(8,8,6,6))
        initial_f = ft.TextField(value=s.get("initials","?"),label="Initial",
                                 text_size=12,border_color=SEND_BLU,max_length=1,
                                 content_padding=P(8,8,6,6))
        color_f   = ft.TextField(value=s.get("color",SEND_BLU),label="Color (hex)",
                                 text_size=12,border_color=SEND_BLU,
                                 content_padding=P(8,8,6,6))
        active_cb = ft.Checkbox(label="Online",value=s.get("is_active",False))

        def make_save(idx,nf,inf,cf,ac):
            def save(e):
                stories[idx].update({
                    "name":     (nf.value or "").strip(),
                    "initials": (inf.value or "?").strip().upper()[:1],
                    "color":    (cf.value or SEND_BLU).strip(),
=======
# ── Stories / Active Users row editor ────────────────────────────────────────
def _build_stories_editor(page:ft.Page, status_txt) -> list:
    """
    Inline editor for the Active Users row shown at the top of the chat list.
    Researchers can change names, initials, and online status.
    Changes are saved to contacts.json stories_row section.
    """
    stories = config.get_stories() or _DEFAULT_STORIES
    rows = []

    for i, s in enumerate(stories):
        name_f    = ft.TextField(value=s.get("name",""),
                                 label="Name", text_size=12,
                                 border_color=SEND_BLU,
                                 content_padding=P(8,8,6,6))
        initial_f = ft.TextField(value=s.get("initials","?"),
                                 label="Initial", text_size=12,
                                 border_color=SEND_BLU, max_length=1,
                                 content_padding=P(8,8,6,6))
        color_f   = ft.TextField(value=s.get("color", SEND_BLU),
                                 label="Color (hex)", text_size=12,
                                 border_color=SEND_BLU,
                                 content_padding=P(8,8,6,6))
        active_cb = ft.Checkbox(label="Online",
                                value=s.get("is_active", False))

        def make_save(idx, nf, inf, cf, ac):
            def save(e):
                stories[idx].update({
                    "name":      (nf.value or "").strip(),
                    "initials":  (inf.value or "?").strip().upper()[:1],
                    "color":     (cf.value or SEND_BLU).strip(),
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
                    "is_active": ac.value,
                })
                try:
                    config.save_contacts(config.get_contacts(), stories)
                    status_txt.value = f"✓ Active user '{nf.value}' saved."
                except Exception as ex:
                    status_txt.value = f"Save error: {ex}"
                page.update()
            return save

<<<<<<< HEAD
        swatch = ft.Container(width=24,height=24,bgcolor=s.get("color",SEND_BLU),
                              border_radius=12)
        save_btn = ft.ElevatedButton("Save",bgcolor=SEND_BLU,color=WHITE,
                                     on_click=make_save(i,name_f,initial_f,color_f,active_cb))
        rows.append(ft.Container(
            content=ft.Column([
                ft.Row([swatch,ft.Text(s.get("name",""),size=12,
                                       weight=ft.FontWeight.BOLD,color=TXT_MED)],spacing=8),
                ft.Row([name_f,initial_f],spacing=8),
                color_f, active_cb, save_btn,
            ],spacing=4),
            border=BS(3,0,0,0,s.get("color",SEND_BLU)),
            padding=P(10,4,6,6),margin=P(0,0,4,4)))
    return rows


# ── Admin panel ───────────────────────────────────────────────────────────────
=======
        swatch = ft.Container(
            width=24, height=24,
            bgcolor=s.get("color", SEND_BLU),
            border_radius=12)

        save_btn = ft.ElevatedButton(
            "Save", bgcolor=SEND_BLU, color=WHITE,
            on_click=make_save(i, name_f, initial_f, color_f, active_cb))

        rows.append(ft.Container(
            content=ft.Column([
                ft.Row([swatch,
                        ft.Text(s.get("name",""), size=12,
                                weight=ft.FontWeight.BOLD, color=TXT_MED)],
                       spacing=8),
                ft.Row([name_f, initial_f], spacing=8),
                color_f, active_cb, save_btn,
            ], spacing=4),
            border=BS(3,0,0,0, s.get("color", SEND_BLU)),
            padding=P(10,4,6,6),
            margin=P(0,0,4,4)))

    return rows


# ── Admin ─────────────────────────────────────────────────────────────────────
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
def _build_admin(page:ft.Page, close) -> ft.Column:
    import csv, shutil, json
    from datetime import datetime as _dt

<<<<<<< HEAD
    status = ft.Text("",color=ft.Colors.GREEN_700,size=13)
    tab_idx = [0]
    tab_bodies = [ft.Container(expand=True)]
=======
    status = ft.Text("", color=ft.Colors.GREEN_700, size=13)

    # ── Tab state ────────────────────────────────────────────────────────────
    tab_idx = [0]
    tab_bodies = [ft.Container(expand=True)]   # placeholder, filled below
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d

    def switch_tab(idx):
        tab_idx[0] = idx
        for i, btn in enumerate(tab_btns):
<<<<<<< HEAD
            btn.bgcolor   = SEND_BLU if i==idx else INPUT_BG
            btn.content.color = WHITE if i==idx else TXT_GRAY
        tab_bodies[0].content = tabs[idx]
        page.update()

    # TAB 0 — Data & Export ────────────────────────────────────────────────────
    summary = ft.Column([],spacing=4)
=======
            btn.bgcolor   = SEND_BLU if i == idx else INPUT_BG
            btn.content.color = WHITE if i == idx else TXT_GRAY
        tab_bodies[0].content = tabs[idx]
        page.update()

    # ── TAB 0 — Data & Export ─────────────────────────────────────────────────
    summary = ft.Column([], spacing=4)
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d

    def load_summary():
        summary.controls.clear()
        pr = load_profile()
        summary.controls.append(ft.Text(
            f"{pr.get('first_name','—')} {pr.get('last_name','—')}  "
            f"ID: {pr.get('participant_id','None')}",
<<<<<<< HEAD
            size=13,color=TXT_MED,weight=ft.FontWeight.BOLD))
        log_path = get_writable_path("telemetry_log.csv")
        total=0; exp=0; ev={}; last_rows=[]
        try:
            if os.path.exists(log_path):
                with open(log_path,"r",encoding="utf-8") as f2:
                    for row in csv.DictReader(f2):
                        total+=1
                        k=row.get("Event_Type","?"); ev[k]=ev.get(k,0)+1
                        if row.get("Data_Exposure_Category","None")!="None": exp+=1
                        last_rows.append(row)
                last_rows=last_rows[-8:]
        except Exception as ex:
            summary.controls.append(
                ft.Text(f"Log error: {ex}",size=11,color=ft.Colors.RED_600))
        summary.controls.append(
            ft.Text(f"Total events: {total}   Exposure alerts: {exp}",
                    size=13,color=TXT_GRAY))
        for k,v in ev.items():
            summary.controls.append(ft.Text(f"  {k}: {v}",size=12,color=TXT_GRAY))
        if last_rows:
            summary.controls.append(ft.Divider())
            summary.controls.append(ft.Text("Recent events:",size=12,
                                            weight=ft.FontWeight.BOLD,color=TXT_MED))
=======
            size=13, color=TXT_MED, weight=ft.FontWeight.BOLD))
        log_path = get_writable_path("telemetry_log.csv")
        total = 0; exp = 0; ev = {}; last_rows = []
        try:
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8") as f2:
                    for row in csv.DictReader(f2):
                        total += 1
                        k = row.get("Event_Type","?")
                        ev[k] = ev.get(k,0)+1
                        if row.get("Data_Exposure_Category","None") != "None":
                            exp += 1
                        last_rows.append(row)
                last_rows = last_rows[-8:]
        except Exception as ex:
            summary.controls.append(
                ft.Text(f"Log error: {ex}", size=11, color=ft.Colors.RED_600))
        summary.controls.append(
            ft.Text(f"Total events: {total}   Exposure alerts: {exp}",
                    size=13, color=TXT_GRAY))
        for k, v in ev.items():
            summary.controls.append(
                ft.Text(f"  {k}: {v}", size=12, color=TXT_GRAY))
        if last_rows:
            summary.controls.append(ft.Divider())
            summary.controls.append(
                ft.Text("Recent events:", size=12,
                        weight=ft.FontWeight.BOLD, color=TXT_MED))
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
            for row in last_rows:
                ts  = row.get("Timestamp","")[:19].replace("T"," ")
                ev2 = row.get("Event_Type","")
                lat = row.get("Latency_ms","0")
<<<<<<< HEAD
                exp2= row.get("Data_Exposure_Category","None")
                line= f"{ts}  {ev2}  {lat}ms"
                if exp2!="None": line+=f"  ⚠ {exp2}"
                summary.controls.append(
                    ft.Text(line,size=10,color=TXT_GRAY,selectable=True))
=======
                exp2 = row.get("Data_Exposure_Category","None")
                line = f"{ts}  {ev2}  {lat}ms"
                if exp2 != "None":
                    line += f"  ⚠ {exp2}"
                summary.controls.append(
                    ft.Text(line, size=10, color=TXT_GRAY, selectable=True))
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
        page.update()

    def export_data(e):
        ts  = _dt.now().strftime("%Y%m%d_%H%M%S")
        pid = load_profile().get("participant_id","UNKNOWN")
        try:
            dl = "/storage/emulated/0/Download"
<<<<<<< HEAD
            os.makedirs(dl,exist_ok=True)
            done=[]
            for src,nm in [
                (get_writable_path("telemetry_log.csv"),f"spice_tel_{pid}_{ts}.csv"),
                (get_writable_path("participant_profile.json"),f"spice_prof_{pid}_{ts}.json"),
                (get_writable_path("session_state.json"),f"spice_sess_{pid}_{ts}.json"),
            ]:
                if os.path.exists(src):
                    shutil.copy2(src,os.path.join(dl,nm)); done.append(nm)
            status.value=(f"✓ Exported {len(done)} files to Downloads."
                          if done else "No data files found yet.")
        except Exception as ex:
            status.value=f"Export failed: {ex}"
        page.update()

    def reset_participant(e):
        global _profile,_chat_engine,_interactions,_route,_chat_unread,_notif_fired
        for fn in ["participant_profile.json","telemetry_log.csv",
                   "session_state.json","offline_queue.json"]:
            p=get_writable_path(fn)
            try:
                if os.path.exists(p): os.remove(p)
            except Exception: pass
        _profile={}; _chat_engine=None; _interactions=0
        _route="boot"; _chat_unread=False; _notif_fired=False
        status.value="✓ Reset complete. Ready for next participant."
        load_summary(); page.update()
=======
            os.makedirs(dl, exist_ok=True)
            done = []
            for src, nm in [
                (get_writable_path("telemetry_log.csv"),
                 f"spice_tel_{pid}_{ts}.csv"),
                (get_writable_path("participant_profile.json"),
                 f"spice_prof_{pid}_{ts}.json"),
                (get_writable_path("session_state.json"),
                 f"spice_sess_{pid}_{ts}.json"),
            ]:
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(dl, nm))
                    done.append(nm)
            status.value = (f"✓ Exported {len(done)} files to Downloads."
                            if done else "No data files found yet.")
        except Exception as ex:
            status.value = f"Export failed: {ex}"
        page.update()

    def reset_participant(e):
        global _profile, _chat_engine, _interactions, _route
        global _chat_unread, _notif_fired
        for fn in ["participant_profile.json","telemetry_log.csv",
                   "session_state.json","offline_queue.json"]:
            p = get_writable_path(fn)
            try:
                if os.path.exists(p): os.remove(p)
            except Exception:
                pass
        _profile = {}; _chat_engine = None; _interactions = 0
        _route = "boot"; _chat_unread = False; _notif_fired = False
        status.value = "✓ Reset complete. Ready for next participant."
        load_summary()
        page.update()
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d

    load_summary()

    data_tab = ft.Column([
<<<<<<< HEAD
        ft.Text("Participant Data",size=15,weight=ft.FontWeight.BOLD,color=TXT_MED),
        summary,
        ft.Row([
            ft.ElevatedButton("Refresh",
                              on_click=lambda e: (load_summary(),page.update()),
                              bgcolor=SEND_BLU,color=WHITE),
            ft.ElevatedButton("Export to Downloads",on_click=export_data,
                              bgcolor="#28A745",color=WHITE),
        ],spacing=8,wrap=True),
        ft.ElevatedButton("Reset for Next Participant",on_click=reset_participant,
                          bgcolor="#DC3545",color=WHITE),
        status,
    ],spacing=10)

    # TAB 1 — Scenario Config ─────────────────────────────────────────────────
=======
        ft.Text("Participant Data", size=15, weight=ft.FontWeight.BOLD,
                color=TXT_MED),
        summary,
        ft.Row([
            ft.ElevatedButton("Refresh",
                              on_click=lambda e: (load_summary(), page.update()),
                              bgcolor=SEND_BLU, color=WHITE),
            ft.ElevatedButton("Export to Downloads",
                              on_click=export_data, bgcolor="#28A745", color=WHITE),
        ], spacing=8, wrap=True),
        ft.ElevatedButton("Reset for Next Participant",
                          on_click=reset_participant, bgcolor="#DC3545", color=WHITE),
        status,
    ], spacing=10)

    # ── TAB 1 — Scenario & Message Config ─────────────────────────────────────
    # Hardcode scenario options so they always appear correctly regardless
    # of what scenario files are on the device
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
    _SCENARIO_OPTIONS = [
        ("medicare_authority",  "Medicare Authority — Government/Benefits threat"),
        ("bank_fraud_alert",    "Bank Fraud Alert — Unauthorized transaction"),
        ("family_emergency",    "Family Emergency — Grandchild/relative in trouble"),
        ("prize_reward",        "Prize/Reward — Lottery or sweepstakes winner"),
    ]
<<<<<<< HEAD
=======
    # Detect current active — check config then fall back to medicare_authority
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
    _current_active = config.get("active_scenario") or "medicare_authority"

    active_dd = ft.Dropdown(
        label="Active Scenario",
<<<<<<< HEAD
        options=[ft.dropdown.Option(sid,label) for sid,label in _SCENARIO_OPTIONS],
        value=_current_active,border_color=SEND_BLU)

    _init_sid    = _current_active
    _init_preset = _SCENARIO_PRESETS.get(_init_sid,{})
    _init_sc     = _scenario()
    _init_hook   = (_init_sc.get("hook_message",
                                 _init_sc.get("initial_hook_message",""))
                    or _init_preset.get("hook",""))

    _init_presets = _HOOK_PRESETS.get(_init_sid,[])
    hook_preset_dd = ft.Dropdown(
        label="Select preset message (or type custom below)",
        options=[ft.dropdown.Option(p[1],p[0]) for p in _init_presets],
        border_color=SEND_BLU,hint_text="Choose a preset...")

    hook_f = ft.TextField(label="Hook Message (edit or type custom)",
                          multiline=True,min_lines=3,max_lines=6,
                          border_color=SEND_BLU,text_size=13,value=_init_hook)

    def on_hook_preset_change(e):
        if hook_preset_dd.value:
            hook_f.value=hook_preset_dd.value; page.update()
    hook_preset_dd.on_change=on_hook_preset_change

    delay_f = ft.TextField(label="Notification Delay (seconds after login)",
                           value=str(config.get("notification_delay_seconds",60) or 60),
                           border_color=SEND_BLU,text_size=13,
                           keyboard_type=ft.KeyboardType.NUMBER)

    minutes_f = ft.TextField(label="Trigger Delay (minutes) — easier option",
                             value="",border_color=SEND_BLU,text_size=13,
                             hint_text="e.g. 5  →  fires 5 minutes after Save",
                             keyboard_type=ft.KeyboardType.NUMBER)

    def on_minutes_change(e):
        try:
            mins=float((minutes_f.value or "").strip())
            delay_f.value=str(int(mins*60)); datetime_f.value=""; page.update()
        except Exception: pass
    minutes_f.on_change=on_minutes_change

    datetime_f = ft.TextField(label="Exact Date & Time  (YYYY-MM-DD HH:MM:SS)",
                              value=config.get("notification_datetime",""),
                              border_color=SEND_BLU,text_size=13,
                              hint_text="e.g. 2026-06-23 14:30:00")

    _mode=[0]
    minutes_panel=ft.Column([
        ft.Text("Fire notification X minutes after you tap Save:",size=12,color=TXT_GRAY),
        minutes_f,
        ft.Text("e.g. type 5 → notification fires in 5 minutes",size=11,
                color=TXT_GRAY,italic=True),
    ],spacing=6,visible=True)

    datetime_panel=ft.Column([
        ft.Text("Fire notification at an exact date and time:",size=12,color=TXT_GRAY),
        datetime_f,
        ft.Text("Format: YYYY-MM-DD HH:MM:SS  (e.g. 2026-06-23 14:30:00)",
                size=11,color=TXT_GRAY,italic=True),
    ],spacing=6,visible=False)

    btn_minutes  = ft.ElevatedButton("Delay (minutes)",bgcolor=SEND_BLU,color=WHITE,
                                     style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))
    btn_datetime = ft.ElevatedButton("Exact Date & Time",bgcolor=INPUT_BG,color=TXT_MED,
                                     style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))

    def set_mode_minutes(e):
        _mode[0]=0; minutes_panel.visible=True; datetime_panel.visible=False
        btn_minutes.bgcolor=SEND_BLU; btn_minutes.color=WHITE
        btn_datetime.bgcolor=INPUT_BG; btn_datetime.color=TXT_MED
        datetime_f.value=""; page.update()

    def set_mode_datetime(e):
        _mode[0]=1; minutes_panel.visible=False; datetime_panel.visible=True
        btn_minutes.bgcolor=INPUT_BG; btn_minutes.color=TXT_MED
        btn_datetime.bgcolor=SEND_BLU; btn_datetime.color=WHITE; page.update()

    btn_minutes.on_click=set_mode_minutes
    btn_datetime.on_click=set_mode_datetime

    def _get_init_prompt(phase):
        saved=config.get_system_prompt(_init_sid,phase)
        if saved and "Stay in character. Phase" not in saved: return saved
        return _init_preset.get(f"phase{phase}","")

    phase1_f=ft.TextField(label="Phase 1 System Prompt (Rapport)",
                          multiline=True,min_lines=4,max_lines=8,
                          border_color=SEND_BLU,text_size=12,
                          value=_get_init_prompt(1))
    phase2_f=ft.TextField(label="Phase 2 System Prompt (Urgency)",
                          multiline=True,min_lines=4,max_lines=8,
                          border_color=SEND_BLU,text_size=12,
                          value=_get_init_prompt(2))
    phase3_f=ft.TextField(label="Phase 3 System Prompt (Demand)",
                          multiline=True,min_lines=4,max_lines=8,
                          border_color=SEND_BLU,text_size=12,
                          value=_get_init_prompt(3))

    def update_prompts(e):
        sid=active_dd.value or ""
        new_presets=_HOOK_PRESETS.get(sid,[])
        hook_preset_dd.options=[ft.dropdown.Option(p[1],p[0]) for p in new_presets]
        hook_preset_dd.value=None
        preset=_SCENARIO_PRESETS.get(sid,{})
        hook_f.value=preset.get("hook","")
        phase1_f.value=preset.get("phase1","")
        phase2_f.value=preset.get("phase2","")
        phase3_f.value=preset.get("phase3","")
        for s in config.get_scenarios():
            if s["id"]==sid:
                saved_hook=s.get("hook_message",s.get("initial_hook_message",""))
                if saved_hook: hook_f.value=saved_hook
                break
        for phase_num,field in [(1,phase1_f),(2,phase2_f),(3,phase3_f)]:
            saved=config.get_system_prompt(sid,phase_num)
            if saved and "Stay in character. Phase" not in saved: field.value=saved
        page.update()

    update_prompts(None)
    active_dd.on_change=update_prompts

    def save_scenario(e):
        global _chat_engine,_notif_fired,_chat_unread
        sid=active_dd.value or ""
        config.set_active_scenario(sid)
        existing_ids=[s["id"] for s in config.get_scenarios()]
        if sid not in existing_ids and sid in _SCENARIO_PRESETS:
            preset=_SCENARIO_PRESETS[sid]
            config.add_scenario({
                "id":sid,"enabled":True,
                "threat_vector_classification":sid.replace("_"," ").title(),
                "sender_identity":{
                    "display_name":{
                        "medicare_authority":"Medicare Services",
                        "bank_fraud_alert":"Fraud Prevention",
                        "family_emergency":"Alex",
                        "prize_reward":"Facebook Rewards",
                    }.get(sid,"Unknown"),
                    "initials_fallback":sid[0].upper(),
                    "initials_color":"#0057A8",
                },
                "hook_message":preset["hook"],
                "ai_system_prompts":{
                    "phase_1":preset["phase1"],
                    "phase_2":preset["phase2"],
                    "phase_3":preset["phase3"],
                },
                "fallback_dialogue":{"phase_1":[],"phase_2":[],"phase_3":[]},
                "phase_thresholds":{"rapport_turns":2,"urgency_turns":2},
            })
        if (hook_f.value or "").strip():
            config.update_scenario_hook(sid,hook_f.value.strip())
        try:
            delay_secs=int((delay_f.value or "60").strip())
            config.set("notification_delay_seconds",delay_secs)
        except ValueError: pass
        dt_val=(datetime_f.value or "").strip()
        if dt_val:
            try:
                from datetime import datetime as _dt2
                _dt2.strptime(dt_val,"%Y-%m-%d %H:%M:%S")
                config.set("notification_datetime",dt_val)
            except ValueError:
                status.value="⚠ Invalid datetime format. Use YYYY-MM-DD HH:MM:SS"
                page.update(); return
        else:
            config.set("notification_datetime","")
        for s in config.get_scenarios():
            if s["id"]==sid:
                prompts=s.setdefault("ai_system_prompts",{})
                if (phase1_f.value or "").strip(): prompts["phase_1"]=phase1_f.value.strip()
                if (phase2_f.value or "").strip(): prompts["phase_2"]=phase2_f.value.strip()
                if (phase3_f.value or "").strip(): prompts["phase_3"]=phase3_f.value.strip()
                config.save_scenario_file(s); break
        _chat_engine=None; _notif_fired=False; _chat_unread=True
        if _page_ref: _page_ref.run_task(_schedule_notif,_page_ref)
        try:
            from session import clear_session; clear_session()
        except Exception: pass
        status.value="✓ Scenario saved. Chat + notification reset."
        page.update()

    scenario_tab=ft.Column([
        ft.Text("Scenario Configuration",size=15,weight=ft.FontWeight.BOLD,color=TXT_MED),
        active_dd,ft.Divider(),
        ft.Text("Message Content",size=13,weight=ft.FontWeight.BOLD,color=TXT_MED),
        hook_preset_dd,hook_f,ft.Divider(),
        ft.Text("Notification Timing",size=13,weight=ft.FontWeight.BOLD,color=TXT_MED),
        ft.Text("Choose how to schedule the notification:",size=12,color=TXT_GRAY),
        ft.Row([btn_minutes,btn_datetime],spacing=8),
        ft.Container(height=4),
        ft.Column([minutes_panel,datetime_panel],spacing=8),
        ft.Divider(),
        ft.Text("AI Conversation Prompts",size=13,weight=ft.FontWeight.BOLD,color=TXT_MED),
        ft.Text("Phase 1 = Rapport building | Phase 2 = Urgency | Phase 3 = Asset demand",
                size=11,color=TXT_GRAY),
        phase1_f,phase2_f,phase3_f,
        ft.ElevatedButton("Save All Changes",on_click=save_scenario,
                          bgcolor=SEND_BLU,color=WHITE),
        status,
    ],spacing=10)

    # TAB 2 — Attacker Profile ─────────────────────────────────────────────────
    scam_c=config.get_active_scam_contact() or {}
    profile_name_f=ft.TextField(label="Display Name",
                                value=scam_c.get("display_name","Medicare Services"),
                                border_color=SEND_BLU,text_size=13)
    profile_initial_f=ft.TextField(label="Avatar Initial (1 letter)",
                                   value=scam_c.get("initials","M"),
                                   border_color=SEND_BLU,text_size=13,max_length=1)
    profile_color_f=ft.TextField(label="Avatar Color (hex e.g. #0057A8)",
                                 value=scam_c.get("initials_color","#0057A8"),
                                 border_color=SEND_BLU,text_size=13)
    profile_online_cb=ft.Checkbox(label="Show as Active/Online",
                                  value=scam_c.get("is_active_online",True))
    profile_preview_f=ft.TextField(label="Preview Text in Chat List",
                                   value=scam_c.get("preview_override",""),
                                   border_color=SEND_BLU,text_size=13,
                                   hint_text="Leave blank to auto-generate from hook message")
    profile_img_f=ft.TextField(label="Profile Picture URL (optional)",value="",
                               border_color=SEND_BLU,text_size=13,
                               hint_text="https://... or leave blank to use initials avatar")
    profile_status=ft.Text("",color=ft.Colors.GREEN_700,size=13)

    def save_profile_config(e):
        cid=scam_c.get("id","")
        if not cid: profile_status.value="No active scam contact found."; page.update(); return
        config.update_contact(cid,{
            "display_name":   (profile_name_f.value or "").strip(),
            "initials":       (profile_initial_f.value or "M").strip().upper()[:1],
            "initials_color": (profile_color_f.value or "#0084FF").strip(),
            "is_active_online": profile_online_cb.value,
            "preview_override":(profile_preview_f.value or "").strip(),
        })
        if (profile_img_f.value or "").strip().startswith("http"):
            profile_status.value="✓ Profile saved. Downloading avatar..."; page.update()
            page.run_task(config.download_avatar,cid,profile_img_f.value.strip())
        else:
            profile_status.value="✓ Attacker profile saved."
        page.update()

    color_preview=ft.Container(width=40,height=40,
                               bgcolor=scam_c.get("initials_color","#0057A8"),
                               border_radius=20)
    def update_color_preview(e):
        try:
            color_preview.bgcolor=(profile_color_f.value or "#0084FF").strip()
            page.update()
        except Exception: pass
    profile_color_f.on_change=update_color_preview

    attacker_tab=ft.Column([
        ft.Text("Attacker Identity Profile",size=15,weight=ft.FontWeight.BOLD,color=TXT_MED),
        ft.Text("Changes the sender displayed to the participant.",size=12,color=TXT_GRAY),
        profile_name_f,
        ft.Row([profile_initial_f,color_preview],spacing=12,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
        profile_color_f,profile_online_cb,profile_preview_f,profile_img_f,
        ft.Text("If a URL is provided the app will download and cache the image as the sender avatar.",
                size=11,color=TXT_GRAY),
        ft.ElevatedButton("Save Attacker Profile",on_click=save_profile_config,
                          bgcolor=SEND_BLU,color=WHITE),
        profile_status,ft.Divider(),
        ft.Text("Active Users Row",size=13,weight=ft.FontWeight.BOLD,color=TXT_MED),
        ft.Text("Edit who appears in the active bubbles at the top of the chat list.",
                size=11,color=TXT_GRAY),
        *_build_stories_editor(page,status),
    ],spacing=10)

    # TAB 3 — Add New Scenario ─────────────────────────────────────────────────
    new_id_f     = ft.TextField(label="Scenario ID (no spaces)",border_color=SEND_BLU,text_size=13)
    new_sender_f = ft.TextField(label="Sender Display Name",border_color=SEND_BLU,text_size=13)
    new_hook_f   = ft.TextField(label="Hook Message",border_color=SEND_BLU,text_size=13,
                                multiline=True,min_lines=3)
    new_delay_f  = ft.TextField(label="Notification Delay (seconds)",value="60",
                                border_color=SEND_BLU,text_size=13,
                                keyboard_type=ft.KeyboardType.NUMBER)
    new_p1_f     = ft.TextField(label="Phase 1 Prompt",border_color=SEND_BLU,text_size=12,
                                multiline=True,min_lines=3)
    new_status   = ft.Text("",color=ft.Colors.GREEN_700,size=13)

    def add_scenario(e):
        sid=(new_id_f.value or "").strip().replace(" ","_")
        if not sid: new_status.value="Scenario ID required."; page.update(); return
        config.add_scenario({
            "id":sid,"enabled":True,"threat_vector_classification":"Custom",
            "sender_identity":{
                "display_name":(new_sender_f.value or "").strip(),
                "initials_fallback":(new_sender_f.value or "X")[:1].upper(),
                "initials_color":"#0084FF",
            },
            "hook_message":(new_hook_f.value or "").strip(),
            "simulation_timing":{
                "simulated_timestamp":"Just Now",
                "notification_delay_seconds":int((new_delay_f.value or "60") or 60),
            },
            "phase_thresholds":{"rapport_turns":2,"urgency_turns":2},
            "ai_system_prompts":{
                "phase_1":(new_p1_f.value or "").strip(),"phase_2":"","phase_3":"",
            },
            "fallback_dialogue":{"phase_1":[],"phase_2":[],"phase_3":[]},
            "sensitive_data_targets":[],
        })
        new_status.value=f"✓ Scenario '{sid}' added."
        active_dd.options=[ft.dropdown.Option(s["id"],s["id"])
                           for s in config.get_scenarios()]
        page.update()

    new_scenario_tab=ft.Column([
        ft.Text("Add New Scenario",size=15,weight=ft.FontWeight.BOLD,color=TXT_MED),
        new_id_f,new_sender_f,new_hook_f,new_delay_f,new_p1_f,
        ft.ElevatedButton("Create Scenario",on_click=add_scenario,
                          bgcolor="#28A745",color=WHITE),
        new_status,
    ],spacing=10)

    # Tab layout ───────────────────────────────────────────────────────────────
    tabs=[data_tab,scenario_tab,attacker_tab,new_scenario_tab]
    tab_labels=["Data","Scenario","Profile","New"]
    tab_btns=[]

    for i,lbl in enumerate(tab_labels):
        is_active=i==0
        btn=ft.Container(
            content=ft.Text(lbl,size=12,color=WHITE if is_active else TXT_GRAY,
                            weight=ft.FontWeight.BOLD),
            bgcolor=SEND_BLU if is_active else INPUT_BG,
            border_radius=6,padding=P(12,12,6,6),expand=True,
            alignment=ft.Alignment(0,0))
        idx_capture=i
        btn.on_click=(lambda e,idx=idx_capture: switch_tab(idx))
        tab_btns.append(btn)

    tab_bar=ft.Container(content=ft.Row(tab_btns,spacing=4),padding=P(12,12,8,8))
    body_container=ft.Container(content=tabs[0],expand=True,padding=Pa(16))
    tab_bodies[0]=body_container

    return ft.Column([
        ft.Container(
            content=ft.Row([
                ft.Text("SPICE Admin Panel",size=17,weight=ft.FontWeight.BOLD,color=TXT_MED),
                ft.IconButton(ft.Icons.CLOSE,on_click=lambda e: close()),
            ],alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            bgcolor=INPUT_BG,padding=P(16,16,44,10)),
        tab_bar,
        ft.Divider(height=1,color=DIVIDER),
        ft.Container(
            content=ft.Column([body_container],expand=True,scroll=ft.ScrollMode.AUTO),
            expand=True),
    ],spacing=0,expand=True)


# ── Routing ───────────────────────────────────────────────────────────────────
=======
        options=[ft.dropdown.Option(sid, label)
                 for sid, label in _SCENARIO_OPTIONS],
        value=_current_active,
        border_color=SEND_BLU)

    # Load initial field values from presets for the current active scenario
    _init_sid    = _current_active
    _init_preset = _SCENARIO_PRESETS.get(_init_sid, {})
    _init_sc     = _scenario()
    _init_hook   = _init_sc.get("hook_message",
                                _init_sc.get("initial_hook_message",""))                    or _init_preset.get("hook","")

    # Hook message: dropdown presets + editable text field
    _init_presets = _HOOK_PRESETS.get(_init_sid, [])
    hook_preset_dd = ft.Dropdown(
        label="Select preset message (or type custom below)",
        options=[ft.dropdown.Option(p[1], p[0])
                 for p in _init_presets],
        border_color=SEND_BLU,
        hint_text="Choose a preset...")

    hook_f = ft.TextField(
        label="Hook Message (edit or type custom)",
        multiline=True, min_lines=3, max_lines=6,
        border_color=SEND_BLU, text_size=13,
        value=_init_hook)

    def on_hook_preset_change(e):
        if hook_preset_dd.value:
            hook_f.value = hook_preset_dd.value
            page.update()
    hook_preset_dd.on_change = on_hook_preset_change

    delay_f = ft.TextField(
        label="Notification Delay (seconds after login)",
        value=str(config.get("notification_delay_seconds", 60) or 60),
        border_color=SEND_BLU, text_size=13,
        keyboard_type=ft.KeyboardType.NUMBER)

    # Minutes field — easier than seconds for researchers
    minutes_f = ft.TextField(
        label="Trigger Delay (minutes) — easier option",
        value="",
        border_color=SEND_BLU, text_size=13,
        hint_text="e.g. 5  →  fires 5 minutes after Save",
        keyboard_type=ft.KeyboardType.NUMBER)

    def on_minutes_change(e):
        """Auto-convert minutes to seconds when researcher types minutes."""
        try:
            mins = float((minutes_f.value or "").strip())
            delay_f.value = str(int(mins * 60))
            # Also clear absolute datetime so delay takes over
            datetime_f.value = ""
            page.update()
        except Exception:
            pass
    minutes_f.on_change = on_minutes_change

    datetime_f = ft.TextField(
        label="Exact Date & Time  (YYYY-MM-DD HH:MM:SS)",
        value=config.get("notification_datetime",""),
        border_color=SEND_BLU, text_size=13,
        hint_text="e.g. 2026-06-23 14:30:00")

    # ── Mode toggle: "Delay (minutes)" vs "Exact Date & Time" ────────
    # Only one panel shows at a time. Researcher picks their preferred mode.
    _mode = [0]   # 0 = minutes mode, 1 = datetime mode

    minutes_panel = ft.Column([
        ft.Text("Fire notification X minutes after you tap Save:",
                size=12, color=TXT_GRAY),
        minutes_f,
        ft.Text("e.g. type 5 → notification fires in 5 minutes",
                size=11, color=TXT_GRAY, italic=True),
    ], spacing=6, visible=True)

    datetime_panel = ft.Column([
        ft.Text("Fire notification at an exact date and time:",
                size=12, color=TXT_GRAY),
        datetime_f,
        ft.Text("Format: YYYY-MM-DD HH:MM:SS  (e.g. 2026-06-23 14:30:00)",
                size=11, color=TXT_GRAY, italic=True),
    ], spacing=6, visible=False)

    btn_minutes  = ft.ElevatedButton(
        "Delay (minutes)",
        bgcolor=SEND_BLU, color=WHITE,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))
    btn_datetime = ft.ElevatedButton(
        "Exact Date & Time",
        bgcolor=INPUT_BG, color=TXT_MED,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))

    def set_mode_minutes(e):
        _mode[0] = 0
        minutes_panel.visible  = True
        datetime_panel.visible = False
        btn_minutes.bgcolor  = SEND_BLU;  btn_minutes.color  = WHITE
        btn_datetime.bgcolor = INPUT_BG;  btn_datetime.color = TXT_MED
        # Clear datetime so delay takes over on save
        datetime_f.value = ""
        page.update()

    def set_mode_datetime(e):
        _mode[0] = 1
        minutes_panel.visible  = False
        datetime_panel.visible = True
        btn_minutes.bgcolor  = INPUT_BG;  btn_minutes.color  = TXT_MED
        btn_datetime.bgcolor = SEND_BLU;  btn_datetime.color = WHITE
        page.update()

    btn_minutes.on_click  = set_mode_minutes
    btn_datetime.on_click = set_mode_datetime

    _timing_mode_btn_ref  = [btn_minutes, btn_datetime]
    _timing_panel_ref     = [ft.Column([minutes_panel, datetime_panel],
                                       spacing=8)]

    def _get_init_prompt(phase):
        saved = config.get_system_prompt(_init_sid, phase)
        if saved and "Stay in character. Phase" not in saved:
            return saved
        return _init_preset.get(f"phase{phase}", "")

    phase1_f = ft.TextField(
        label="Phase 1 System Prompt (Rapport)",
        multiline=True, min_lines=4, max_lines=8,
        border_color=SEND_BLU, text_size=12,
        value=_get_init_prompt(1))

    phase2_f = ft.TextField(
        label="Phase 2 System Prompt (Urgency)",
        multiline=True, min_lines=4, max_lines=8,
        border_color=SEND_BLU, text_size=12,
        value=_get_init_prompt(2))

    phase3_f = ft.TextField(
        label="Phase 3 System Prompt (Demand)",
        multiline=True, min_lines=4, max_lines=8,
        border_color=SEND_BLU, text_size=12,
        value=_get_init_prompt(3))

    def update_prompts(e):
        """
        When researcher picks a scenario:
        1. Load preset template immediately (always reliable)
        2. Override with saved values from scenario file if they exist
        3. Refresh hook preset dropdown options for the new scenario
        """
        sid = active_dd.value or ""

        # Refresh hook preset dropdown for new scenario
        new_presets = _HOOK_PRESETS.get(sid, [])
        hook_preset_dd.options = [
            ft.dropdown.Option(p[1], p[0]) for p in new_presets]
        hook_preset_dd.value = None

        # Start with presets (always available, never fails)
        preset = _SCENARIO_PRESETS.get(sid, {})
        hook_f.value   = preset.get("hook",   "")
        phase1_f.value = preset.get("phase1", "")
        phase2_f.value = preset.get("phase2", "")
        phase3_f.value = preset.get("phase3", "")

        # Override with saved scenario file values if they exist and differ
        # from the generic fallback text
        for s in config.get_scenarios():
            if s["id"] == sid:
                saved_hook = s.get("hook_message",
                                   s.get("initial_hook_message",""))
                if saved_hook:
                    hook_f.value = saved_hook
                break

        for phase_num, field in [(1, phase1_f), (2, phase2_f), (3, phase3_f)]:
            saved = config.get_system_prompt(sid, phase_num)
            # Only use saved if it's not the generic auto-generated fallback
            if saved and "Stay in character. Phase" not in saved:
                field.value = saved

        page.update()

    # Populate fields immediately for the currently selected scenario
    update_prompts(None)
    active_dd.on_change = update_prompts

    def save_scenario(e):
        global _chat_engine, _notif_fired, _chat_unread
        sid = active_dd.value or ""
        config.set_active_scenario(sid)
        # Ensure a scenario file exists for this ID
        # If not, create one from the preset so future loads work
        existing_ids = [s["id"] for s in config.get_scenarios()]
        if sid not in existing_ids and sid in _SCENARIO_PRESETS:
            preset = _SCENARIO_PRESETS[sid]
            config.add_scenario({
                "id": sid,
                "enabled": True,
                "threat_vector_classification": sid.replace("_"," ").title(),
                "sender_identity": {
                    "display_name": {
                        "medicare_authority": "Medicare Services",
                        "bank_fraud_alert":   "Fraud Prevention",
                        "family_emergency":   "Alex",
                        "prize_reward":       "Facebook Rewards",
                    }.get(sid, "Unknown"),
                    "initials_fallback": sid[0].upper(),
                    "initials_color": "#0057A8",
                },
                "hook_message": preset["hook"],
                "ai_system_prompts": {
                    "phase_1": preset["phase1"],
                    "phase_2": preset["phase2"],
                    "phase_3": preset["phase3"],
                },
                "fallback_dialogue": {"phase_1":[],"phase_2":[],"phase_3":[]},
                "phase_thresholds": {"rapport_turns":2,"urgency_turns":2},
            })

        # Save hook message
        if (hook_f.value or "").strip():
            config.update_scenario_hook(sid, hook_f.value.strip())

        # Save notification delay
        try:
            delay_secs = int((delay_f.value or "60").strip())
            config.set("notification_delay_seconds", delay_secs)
        except ValueError:
            pass

        # Save absolute datetime (validated format)
        dt_val = (datetime_f.value or "").strip()
        if dt_val:
            try:
                from datetime import datetime as _dt2
                _dt2.strptime(dt_val, "%Y-%m-%d %H:%M:%S")
                config.set("notification_datetime", dt_val)
            except ValueError:
                status.value = "⚠ Invalid datetime format. Use YYYY-MM-DD HH:MM:SS"
                page.update()
                return
        else:
            config.set("notification_datetime", "")

        # Save system prompts back to scenario file
        for s in config.get_scenarios():
            if s["id"] == sid:
                prompts = s.setdefault("ai_system_prompts", {})
                if (phase1_f.value or "").strip():
                    prompts["phase_1"] = phase1_f.value.strip()
                if (phase2_f.value or "").strip():
                    prompts["phase_2"] = phase2_f.value.strip()
                if (phase3_f.value or "").strip():
                    prompts["phase_3"] = phase3_f.value.strip()
                config.save_scenario_file(s)
                break

        _chat_engine  = None
        _notif_fired  = False
        _chat_unread  = True   # keep Medicare bold after scenario change
        # Re-schedule the notification timer
        if _page_ref:
            _page_ref.run_task(_schedule_notif, _page_ref)
        try:
            from session import clear_session
            clear_session()
        except Exception:
            pass
        status.value = "✓ Scenario saved. Chat + notification reset."
        page.update()

    scenario_tab = ft.Column([
        ft.Text("Scenario Configuration", size=15,
                weight=ft.FontWeight.BOLD, color=TXT_MED),
        active_dd,
        ft.Divider(),
        ft.Text("Message Content", size=13,
                weight=ft.FontWeight.BOLD, color=TXT_MED),
        hook_preset_dd,
        hook_f,
        ft.Divider(),
        ft.Text("Notification Timing", size=13,
                weight=ft.FontWeight.BOLD, color=TXT_MED),

        # ── Mode toggle ───────────────────────────────────────────────
        ft.Text("Choose how to schedule the notification:",
                size=12, color=TXT_GRAY),
        ft.Row([
            _timing_mode_btn_ref[0],
            _timing_mode_btn_ref[1],
        ], spacing=8),
        ft.Container(height=4),
        _timing_panel_ref[0],
        ft.Divider(),
        ft.Text("AI Conversation Prompts", size=13,
                weight=ft.FontWeight.BOLD, color=TXT_MED),
        ft.Text("Phase 1 = Rapport building | Phase 2 = Urgency | "
                "Phase 3 = Asset demand",
                size=11, color=TXT_GRAY),
        phase1_f, phase2_f, phase3_f,
        ft.ElevatedButton("Save All Changes", on_click=save_scenario,
                          bgcolor=SEND_BLU, color=WHITE),
        status,
    ], spacing=10)

    # ── TAB 2 — Attacker Profile Config ───────────────────────────────────────
    scam_c = config.get_active_scam_contact() or {}

    profile_name_f = ft.TextField(
        label="Display Name",
        value=scam_c.get("display_name","Medicare Services"),
        border_color=SEND_BLU, text_size=13)

    profile_initial_f = ft.TextField(
        label="Avatar Initial (1 letter)",
        value=scam_c.get("initials","M"),
        border_color=SEND_BLU, text_size=13,
        max_length=1)

    profile_color_f = ft.TextField(
        label="Avatar Color (hex e.g. #0057A8)",
        value=scam_c.get("initials_color","#0057A8"),
        border_color=SEND_BLU, text_size=13)

    profile_online_cb = ft.Checkbox(
        label="Show as Active/Online",
        value=scam_c.get("is_active_online", True))

    profile_preview_f = ft.TextField(
        label="Preview Text in Chat List",
        value=scam_c.get("preview_override",""),
        border_color=SEND_BLU, text_size=13,
        hint_text="Leave blank to auto-generate from hook message")

    profile_img_f = ft.TextField(
        label="Profile Picture URL (optional)",
        value="",
        border_color=SEND_BLU, text_size=13,
        hint_text="https://... or leave blank to use initials avatar")

    profile_status = ft.Text("", color=ft.Colors.GREEN_700, size=13)

    def save_profile_config(e):
        cid = scam_c.get("id","")
        if not cid:
            profile_status.value = "No active scam contact found."
            page.update()
            return
        config.update_contact(cid, {
            "display_name":    (profile_name_f.value or "").strip(),
            "initials":        (profile_initial_f.value or "M").strip().upper()[:1],
            "initials_color":  (profile_color_f.value or "#0084FF").strip(),
            "is_active_online": profile_online_cb.value,
            "preview_override": (profile_preview_f.value or "").strip(),
        })
        # Optionally download profile picture if URL provided
        if (profile_img_f.value or "").strip().startswith("http"):
            profile_status.value = "✓ Profile saved. Downloading avatar..."
            page.update()
            page.run_task(
                config.download_avatar,
                cid,
                profile_img_f.value.strip())
        else:
            profile_status.value = "✓ Attacker profile saved."
        page.update()

    # Colour preview swatch
    color_preview = ft.Container(
        width=40, height=40,
        bgcolor=scam_c.get("initials_color","#0057A8"),
        border_radius=20)

    def update_color_preview(e):
        try:
            color_preview.bgcolor = (profile_color_f.value or "#0084FF").strip()
            page.update()
        except Exception:
            pass
    profile_color_f.on_change = update_color_preview

    attacker_tab = ft.Column([
        ft.Text("Attacker Identity Profile", size=15,
                weight=ft.FontWeight.BOLD, color=TXT_MED),
        ft.Text("Changes the sender displayed to the participant.",
                size=12, color=TXT_GRAY),
        profile_name_f,
        ft.Row([profile_initial_f, color_preview], spacing=12,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
        profile_color_f,
        profile_online_cb,
        profile_preview_f,
        profile_img_f,
        ft.Text("If a URL is provided the app will download and cache "
                "the image as the sender avatar.",
                size=11, color=TXT_GRAY),
        ft.ElevatedButton("Save Attacker Profile",
                          on_click=save_profile_config,
                          bgcolor=SEND_BLU, color=WHITE),
        profile_status,
        ft.Divider(),
        ft.Text("Active Users Row", size=13,
                weight=ft.FontWeight.BOLD, color=TXT_MED),
        ft.Text("Edit who appears in the active bubbles at the top of the chat list.",
                size=11, color=TXT_GRAY),
        *_build_stories_editor(page, status),
    ], spacing=10)

    # ── TAB 3 — Add New Scenario ───────────────────────────────────────────────
    new_id_f     = ft.TextField(label="Scenario ID (no spaces)",
                                border_color=SEND_BLU, text_size=13)
    new_sender_f = ft.TextField(label="Sender Display Name",
                                border_color=SEND_BLU, text_size=13)
    new_hook_f   = ft.TextField(label="Hook Message",
                                border_color=SEND_BLU, text_size=13,
                                multiline=True, min_lines=3)
    new_delay_f  = ft.TextField(label="Notification Delay (seconds)",
                                value="60", border_color=SEND_BLU,
                                text_size=13,
                                keyboard_type=ft.KeyboardType.NUMBER)
    new_p1_f = ft.TextField(label="Phase 1 Prompt",
                            border_color=SEND_BLU, text_size=12,
                            multiline=True, min_lines=3)
    new_status = ft.Text("", color=ft.Colors.GREEN_700, size=13)

    def add_scenario(e):
        sid = (new_id_f.value or "").strip().replace(" ","_")
        if not sid:
            new_status.value = "Scenario ID required."
            page.update()
            return
        config.add_scenario({
            "id": sid,
            "enabled": True,
            "threat_vector_classification": "Custom",
            "sender_identity": {
                "display_name": (new_sender_f.value or "").strip(),
                "initials_fallback": (new_sender_f.value or "X")[:1].upper(),
                "initials_color": "#0084FF",
            },
            "hook_message": (new_hook_f.value or "").strip(),
            "simulation_timing": {
                "simulated_timestamp": "Just Now",
                "notification_delay_seconds": int(
                    (new_delay_f.value or "60") or 60),
            },
            "phase_thresholds": {"rapport_turns": 2, "urgency_turns": 2},
            "ai_system_prompts": {
                "phase_1": (new_p1_f.value or "").strip(),
                "phase_2": "",
                "phase_3": "",
            },
            "fallback_dialogue": {"phase_1":[],"phase_2":[],"phase_3":[]},
            "sensitive_data_targets": [],
        })
        new_status.value = f"✓ Scenario '{sid}' added."
        # Refresh dropdown
        active_dd.options = [
            ft.dropdown.Option(s["id"],s["id"])
            for s in config.get_scenarios()]
        page.update()

    new_scenario_tab = ft.Column([
        ft.Text("Add New Scenario", size=15,
                weight=ft.FontWeight.BOLD, color=TXT_MED),
        new_id_f, new_sender_f, new_hook_f, new_delay_f, new_p1_f,
        ft.ElevatedButton("Create Scenario", on_click=add_scenario,
                          bgcolor="#28A745", color=WHITE),
        new_status,
    ], spacing=10)

    # ── Tab layout ─────────────────────────────────────────────────────────────
    tabs = [data_tab, scenario_tab, attacker_tab, new_scenario_tab]
    tab_labels = ["Data", "Scenario", "Profile", "New"]
    tab_btns = []

    for i, lbl in enumerate(tab_labels):
        is_active = i == 0
        btn = ft.Container(
            content=ft.Text(lbl, size=12, color=WHITE if is_active else TXT_GRAY,
                            weight=ft.FontWeight.BOLD),
            bgcolor=SEND_BLU if is_active else INPUT_BG,
            border_radius=6,
            padding=P(12,12,6,6),
            expand=True,
            alignment=ft.Alignment(0,0))
        idx_capture = i
        btn.on_click = (lambda e, idx=idx_capture: switch_tab(idx))
        tab_btns.append(btn)

    tab_bar = ft.Container(
        content=ft.Row(tab_btns, spacing=4),
        padding=P(12,12,8,8))

    body_container = ft.Container(
        content=tabs[0],
        expand=True,
        padding=Pa(16))
    tab_bodies[0] = body_container

    return ft.Column([
        ft.Container(
            content=ft.Row([
                ft.Text("SPICE Admin Panel", size=17,
                        weight=ft.FontWeight.BOLD, color=TXT_MED),
                ft.IconButton(ft.Icons.CLOSE, on_click=lambda e: close()),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            bgcolor=INPUT_BG,
            padding=P(16,16,44,10)),
        tab_bar,
        ft.Divider(height=1, color=DIVIDER),
        ft.Container(
            content=ft.Column([body_container], expand=True,
                              scroll=ft.ScrollMode.AUTO),
            expand=True),
    ], spacing=0, expand=True)


>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
def _go(page:ft.Page,route:str):
    global _route; _route=route; _render(page)

def _render(page:ft.Page):
    global _route
    page.controls.clear()
    route=_route or "boot"
    try:
<<<<<<< HEAD
        if   route=="boot":         _boot(page); return
        elif route=="reg":          v=_build_reg(page,lambda: _go(page,"list"))
        elif route=="list":         v=_build_list(page,
                                                  open_scam=lambda: _go(page,"chat"),
                                                  open_filler=lambda: _go(page,"filler"))
        elif route=="password":     v=_build_password(page,
                                                      on_success=lambda: _go(page,"admin"),
                                                      on_cancel=lambda: _go(page,"list"))
        elif route=="chat":         v=_build_chat(page,back=lambda: _go(page,"list"))
        elif route=="filler":       v=_build_filler(page,back=lambda: _go(page,"list"))
        elif route=="notifications":v=_build_notifications(page,back=lambda: _go(page,"list"))
        elif route=="admin":        v=_build_admin(page,close=lambda: _go(page,"list"))
        else:                       v=_error_view(f"Unknown route: {route}")
=======
        if   route=="boot":   _boot(page); return
        elif route=="reg":    v=_build_reg(page,lambda: _go(page,"list"))
        elif route=="list":   v=_build_list(page,
                                            open_scam=lambda: _go(page,"chat"),
                                            open_filler=lambda: _go(page,"filler"))
        elif route=="password": v=_build_password(page,
                                                  on_success=lambda: _go(page,"admin"),
                                                  on_cancel=lambda: _go(page,"list"))
        elif route=="chat":   v=_build_chat(page,back=lambda: _go(page,"list"))
        elif route=="filler": v=_build_filler(page,back=lambda: _go(page,"list"))
        elif route=="notifications": v=_build_notifications(page,
                                                            back=lambda: _go(page,"list"))
        elif route=="admin":  v=_build_admin(page,close=lambda: _go(page,"list"))
        else:                 v=_error_view(f"Unknown: {route}")
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
        page.add(v)
    except Exception as ex:
        logger.exception("Render error: %s",ex)
        page.controls.clear()
        page.add(_error_view(str(ex)))
    page.update()

async def _schedule_notif(page):
    """
    Waits for the configured delay or absolute datetime, then:
    1. Sets _chat_unread=True so Medicare thread goes bold with blue dot
    2. Re-renders the list so the change is visible immediately
    3. Logs the event to telemetry

<<<<<<< HEAD
# ── Notification scheduler ────────────────────────────────────────────────────
async def _schedule_notif(page):
    """
    Waits for the configured delay or absolute datetime, then:
    1. Sets _chat_unread=True so the scam thread goes bold with blue dot
    2. Fires a real OS-level notification via the registered channel
    3. Re-renders the list so the change is visible immediately
    4. Logs the event to telemetry
    """
    global _chat_unread, _notif_fired, _notif_fire_time

    from datetime import datetime as _dt
    logger.info("_schedule_notif started")

    abs_dt_str=(config.get("notification_datetime") or "").strip()

    if abs_dt_str:
        try:
            _parsed=False
            for _fmt in ["%Y-%m-%d %H:%M:%S","%Y-%m-%d %H:%M",
                         "%Y-%m-%d %I:%M:%S"]:
                try:
                    target=_dt.strptime(abs_dt_str,_fmt); _parsed=True; break
                except Exception: continue
            if not _parsed:
                raise ValueError(f"Cannot parse datetime: {abs_dt_str}")
            total_secs=(target-_dt.now()).total_seconds()
            if total_secs<0:
                logger.info("Datetime %s already passed — firing immediately",abs_dt_str)
                total_secs=0
            else:
                logger.info("Absolute schedule: waiting %.0fs until %s",total_secs,abs_dt_str)
        except Exception as ex:
            logger.warning("Bad datetime '%s' (%s) — using delay instead",abs_dt_str,ex)
            total_secs=float(config.get("notification_delay_seconds",60) or 60)
    else:
        total_secs=float(config.get("notification_delay_seconds",60) or 60)
        logger.info("Relative delay: waiting %.0f seconds",total_secs)

    elapsed=0.0
    while elapsed<total_secs:
        if _notif_fired:
            logger.info("Notification already fired — exiting timer"); return
        chunk=min(5.0,total_secs-elapsed)
        await asyncio.sleep(chunk)
        elapsed+=chunk
        new_abs=(config.get("notification_datetime") or "").strip()
        if new_abs and new_abs!=abs_dt_str:
            logger.info("Datetime changed to %s — restarting timer",new_abs)
            page.run_task(_schedule_notif,page); return

    if _notif_fired:
        return

    _notif_fired      = True
    _chat_unread      = True
    _notif_fire_time  = time.time()

    sc     = _scenario()
    si     = sc.get("sender_identity",{})
    sender = si.get("display_name","Medicare Services")
    hook   = sc.get("hook_message",sc.get("initial_hook_message",""))
    preview= (hook[:60]+"…") if len(hook)>60 else hook

    # Log for Notifications feed screen
    _notif_log.append({"sender":sender,"preview":preview,"fired_at":_notif_fire_time})

    logger.info("NOTIFICATION FIRED — %s thread now bold + unread",sender)

    telemetry.log(participant_id=_pid(),
                  scenario_type=sc.get("threat_vector_classification",""),
                  event_type="Push_Notification_Delivered")

    # ── Fire OS-level notification via registered channel ─────────────────────
    _fire_os_notification(sender, preview)

    # Re-render list so thread goes bold immediately
    try:
        _render(page)
    except Exception as ex:
        logger.warning("Re-render failed after notification: %s",ex)
=======
    Supports two modes (admin-configurable):
      - Relative delay: notification_delay_seconds (default 60)
      - Absolute datetime: notification_datetime "YYYY-MM-DD HH:MM:SS"
    """
    global _chat_unread, _notif_fired

    from datetime import datetime as _dt
    import math

    logger.info("_schedule_notif started")

    # ── Determine how long to wait ────────────────────────────────────
    abs_dt_str = (config.get("notification_datetime") or "").strip()

    if abs_dt_str:
        # Absolute datetime mode
        try:
            # Accept multiple formats: 2026-06-23 09:23:00 or 9:23:00
            _parsed = False
            for _fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                         "%Y-%m-%d %-H:%M:%S", "%Y-%m-%d %I:%M:%S"]:
                try:
                    target = _dt.strptime(abs_dt_str, _fmt)
                    _parsed = True
                    break
                except Exception:
                    continue
            if not _parsed:
                raise ValueError(f"Cannot parse datetime: {abs_dt_str}")
            total_secs = (target - _dt.now()).total_seconds()
            if total_secs < 0:
                logger.info("Datetime %s already passed — firing immediately",
                            abs_dt_str)
                total_secs = 0
            else:
                logger.info("Absolute schedule: waiting %.0fs until %s",
                            total_secs, abs_dt_str)
        except Exception as ex:
            logger.warning("Bad datetime '%s' (%s) — using delay instead",
                           abs_dt_str, ex)
            total_secs = float(config.get("notification_delay_seconds",60) or 60)
    else:
        total_secs = float(config.get("notification_delay_seconds", 60) or 60)
        logger.info("Relative delay: waiting %.0f seconds", total_secs)
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d

    # ── Sleep in small chunks so we can respond to config changes ────
    # Check every 5 seconds whether the config changed while waiting
    elapsed = 0.0
    while elapsed < total_secs:
        if _notif_fired:
            logger.info("Notification already fired — exiting timer")
            return
        chunk = min(5.0, total_secs - elapsed)
        await asyncio.sleep(chunk)
        elapsed += chunk

<<<<<<< HEAD
def _fire_os_notification(title:str, body:str):
    """
    Posts a real Android OS notification using the channel registered at startup.
    Appears on lock screen and in notification shade on all API 26+ devices.
    Safe no-op on desktop.
    """
    if not getattr(sys,'frozen',False):
        logger.info("_fire_os_notification: desktop mode — skipping")
        return
    try:
        from jnius import autoclass

        NotificationCompat = autoclass('androidx.core.app.NotificationCompat')
        NotificationManagerCompat = autoclass(
            'androidx.core.app.NotificationManagerCompat')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Intent         = autoclass('android.content.Intent')
        PendingIntent  = autoclass('android.app.PendingIntent')

        context  = PythonActivity.mActivity
        activity_class = autoclass('edu.vcu.vcoa.spice.MainActivity')

        intent = Intent(context, activity_class)
        intent.setFlags(0x10000000)  # FLAG_ACTIVITY_NEW_TASK

        # FLAG_UPDATE_CURRENT | FLAG_IMMUTABLE = 0x04000000 | 0x40000000
        pi = PendingIntent.getActivity(context, 0, intent, 0x44000000)

        # Use a simple drawable that Flet packages — ic_launcher is always present
        R_drawable = autoclass('edu.vcu.vcoa.spice.R$drawable')
        icon_res   = R_drawable.ic_launcher

        builder = (NotificationCompat.Builder(context, NOTIF_CHANNEL_ID)
                   .setSmallIcon(icon_res)
                   .setContentTitle(title)
                   .setContentText(body)
                   .setPriority(2)          # PRIORITY_HIGH
                   .setContentIntent(pi)
                   .setAutoCancel(True)
                   .build())

        nm = NotificationManagerCompat.from_(context)
        nm.notify(1001, builder)

        logger.info("OS notification posted: %s | %s", title, body)

    except Exception as ex:
        logger.warning("_fire_os_notification failed: %s", ex)
        # Non-fatal — in-app bold thread already set by _schedule_notif


# ── Boot ──────────────────────────────────────────────────────────────────────
def _boot(page:ft.Page):
    global _profile, _notif_fired, _chat_unread, _chat_engine
    _notif_fired = False
    _chat_unread = True
    _chat_engine = None
    if profile_exists():
        _profile = load_profile()
        _go(page,"list")
        page.run_task(_schedule_notif,page)
    else:
        _go(page,"reg")


# ── Runtime permission request (Android 13+ / API 33+) ───────────────────────
def _request_notification_permission(page:ft.Page):
    """
    On Android 13+ the POST_NOTIFICATIONS permission is a runtime grant.
    The manifest declaration alone is not enough — the user must be prompted.
    This shows the system dialog on first launch after install.
    Safe no-op on desktop and Android < 13.
    """
    if not getattr(sys,'frozen',False):
        return
    try:
        from jnius import autoclass

        Build_VERSION    = autoclass('android.os.Build$VERSION')
        # Android 13 = TIRAMISU = API 33
        if Build_VERSION.SDK_INT < 33:
            logger.info("API %d < 33 — POST_NOTIFICATIONS not a runtime permission",
                        Build_VERSION.SDK_INT)
            return

        PackageManager   = autoclass('android.content.pm.PackageManager')
        ContextCompat    = autoclass('androidx.core.content.ContextCompat')
        ActivityCompat   = autoclass('androidx.core.app.ActivityCompat')
        PythonActivity   = autoclass('org.kivy.android.PythonActivity')

        activity   = PythonActivity.mActivity
        permission = "android.permission.POST_NOTIFICATIONS"

        granted = (ContextCompat.checkSelfPermission(activity, permission)
                   == PackageManager.PERMISSION_GRANTED)

        if not granted:
            ActivityCompat.requestPermissions(activity, [permission], 1001)
            logger.info("POST_NOTIFICATIONS permission dialog shown")
        else:
            logger.info("POST_NOTIFICATIONS already granted")

    except Exception as ex:
        logger.warning("_request_notification_permission failed: %s", ex)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
async def _register_fcm_and_check_deeplink(page:ft.Page):
    """Placeholder — FCM not active in this build. Safe no-op."""
    pass


def main(page:ft.Page):
    global _page_ref
    _page_ref = page
    page.title  = "Social Connect+ Assistant"
    page.bgcolor= BG
    page.padding= 0
    page.spacing= 0
    page.theme_mode = ft.ThemeMode.LIGHT

    try:
        if hasattr(page,"window") and hasattr(page.window,"status_bar_color"):
            page.window.status_bar_color = BLUE
    except Exception:
        pass

    def on_lifecycle(e):
        if e.data in ("pause","inactive","detach") and _chat_engine:
            sc = _scenario()
=======
        # Re-check absolute datetime in case admin changed it while waiting
        new_abs = (config.get("notification_datetime") or "").strip()
        if new_abs and new_abs != abs_dt_str:
            logger.info("Datetime changed to %s — restarting timer", new_abs)
            page.run_task(_schedule_notif, page)
            return

    # ── Fire ─────────────────────────────────────────────────────────
    if _notif_fired:
        return
    _notif_fired = True
    _chat_unread = True
    _notif_fire_time = time.time()

    # Log for the Notifications feed screen
    sc = _scenario()
    si = sc.get("sender_identity", {})
    sender = si.get("display_name", "Medicare Services")
    hook   = sc.get("hook_message", sc.get("initial_hook_message",""))
    preview = (hook[:50] + "…") if len(hook) > 50 else hook
    _notif_log.append({
        "sender":    sender,
        "preview":   preview,
        "fired_at":  _notif_fire_time,
    })

    logger.info("NOTIFICATION FIRED — %s thread now bold + unread", sender)

    telemetry.log(
        participant_id=_pid(),
        scenario_type=_scenario().get("threat_vector_classification",""),
        event_type="Push_Notification_Delivered")

    # Re-render the list so Medicare appears bold with blue dot right now
    try:
        _render(page)
    except Exception as ex:
        logger.warning("Re-render failed after notification: %s", ex)


def _boot(page:ft.Page):
    global _profile, _notif_fired, _chat_unread, _chat_engine
    # Reset notification state every time the app boots so the
    # notification always fires fresh for each session
    _notif_fired  = False
    _chat_unread  = True   # Medicare always bold from first launch
    _chat_engine  = None
    if profile_exists():
        _profile = load_profile()
        _go(page, "list")
        # Schedule the notification after login
        page.run_task(_schedule_notif, page)
    else:
        _go(page, "reg")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
async def _register_fcm_and_check_deeplink(page: ft.Page):
    """Placeholder — FCM not active in this build. Safe no-op."""
    pass


def main(page:ft.Page):
    global _page_ref
    _page_ref = page
    page.title="Social Connect+ Assistant"
    page.bgcolor=BG; page.padding=0; page.spacing=0
    page.theme_mode=ft.ThemeMode.LIGHT
    try:
        if hasattr(page,"window") and hasattr(page.window,"status_bar_color"):
            page.window.status_bar_color=BLUE
    except Exception: pass

    def on_lifecycle(e):
        if e.data in ("pause","inactive","detach") and _chat_engine:
            sc=_scenario()
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
            save_session(active_scenario_id=sc.get("id",""),
                         conversation_history=_chat_engine.history,
                         accumulated_latency_ms=0.0,
                         interaction_count=_interactions,
                         current_phase=_chat_engine.phase)
<<<<<<< HEAD
    page.on_app_lifecycle_state_change = on_lifecycle
=======
    page.on_app_lifecycle_state_change=on_lifecycle
>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d

    async def _queue_loop():
        while True:
            await asyncio.sleep(30)
<<<<<<< HEAD
            if get_queue_depth() > 0:
                await flush_queue(telemetry)
    page.run_task(_queue_loop)

    page.run_task(_register_fcm_and_check_deeplink, page)

    # Render the first view
    _render(page)

    # Request POST_NOTIFICATIONS permission on Android 13+
    # Called after render so the UI is visible before the system dialog appears
    _request_notification_permission(page)


=======
            if get_queue_depth()>0:
                await flush_queue(telemetry)
    page.run_task(_queue_loop)

    # Register FCM token and check for deep-link launch
    page.run_task(_register_fcm_and_check_deeplink, page)

    # Notification is scheduled after login — see _boot() and _schedule_notif()

    # Note: POST_NOTIFICATIONS runtime permission is declared in pyproject.toml
    # and handled at the OS level on Android 13+. No runtime API call needed
    # in Flet 0.85.3 — the manifest declaration is sufficient.

    _render(page)

>>>>>>> 1feaec0a7ae219ac19525d01c55ac076690eb60d
if __name__ == "__main__":
    ft.app(target=main)