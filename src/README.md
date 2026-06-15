# SPICE — Software Platform for Investigating Cyber Experiences
### Android App (Flet/Python) — HEAR the Message Project, VCU/VCoA

---

## Project Structure

```
spice_app/
├── pyproject.toml          # Flet build config + dependencies
└── src/
    ├── main.py             # Entry point — router + all Flet views
    ├── path_utils.py       # Android-safe path resolution
    ├── defaults.py         # Hardcoded fallback data (prevents white-screen crash)
    ├── config_loader.py    # Loads config.json + message_manifest.json with fallback
    ├── participant.py      # Registration, profile persistence
    ├── telemetry.py        # IRB-compliant PII scrubber + CSV telemetry logger
    ├── session.py          # Session serialization (resume after minimize)
    ├── ai_engine.py        # Anthropic API chat engine + 3-phase state machine
    ├── network_queue.py    # Offline event queue + async flush
    ├── config.json         # Default configuration (deployed as asset)
    └── message_manifest.json  # Scenario definitions (deployed as asset)
```

---

## Android White-Screen Fix — What Changed

| Problem | Fix |
|---|---|
| `Path(__file__).parent` fails in APK sandbox | `path_utils.get_secure_path()` / `get_writable_path()` — uses `sys.frozen` detection |
| File reads crash on boot with no fallback | Every `_load_json()` call returns `DEFAULT_CONFIG` / `DEFAULT_MANIFEST` on failure |
| Long loops blocking UI thread → ANR freeze | All AI calls and telemetry writes are `async` or `threading.Thread(daemon=True)` |
| Global state not initialised before `main()` | All `_participant_profile`, `_chat_engine`, etc. declared at module level |
| No error boundary → silent white screen | Top-level `try/except` in `_render_view()` routes to an admin error screen |
| Module import failures cascade | Each import wrapped in `try/except` with inline stub fallback |

---

## Build & Run

### Desktop development
```bash
cd spice_app
pip install flet httpx
ANTHROPIC_API_KEY=sk-ant-... python src/main.py
```

### Android APK
```bash
cd spice_app
flet build apk src --org edu.vcu.vcoa.spice
# Output: build/apk/spice.apk
```

Set `ANTHROPIC_API_KEY` as an environment secret in your CI pipeline or
inject it at build time via `flet build --env ANTHROPIC_API_KEY=...`.

---

## Requirements Coverage

| Req | Module | Notes |
|-----|--------|-------|
| 1 — Admin panel | `main.py::build_admin_view` | 7-tap logo gesture |
| 2 — External manifest | `config_loader.py`, `message_manifest.json` | JSON schema with all required fields |
| 3 — Telemetry engine | `telemetry.py` | Thread-safe CSV; all micro-interactions |
| 4 — FB lookalike UI | `main.py::build_feed_view` | Facebook colour palette, nav bar |
| 5 — Messenger + AI | `main.py::build_chat_view`, `ai_engine.py` | Infinite conversation |
| 6 — PII scrubber | `telemetry.py::scrub_message` | Regex destroy + category label only |
| 7 — Click/latency | `telemetry.py`, `main.py` | Notification click, focus, compose |
| 8 — Threat matrix | `message_manifest.json`, `ai_engine.py` | 3 categories, configurable |
| 9 — Session state | `session.py` | Auto-save on pause; resume on boot |
| 10 — Offline queue | `network_queue.py` | Async flush with retry |
| 11 — Fallback dialogue | `ai_engine.py::_fallback_reply` | Config-driven canned responses |
| 12 — Registration | `main.py::build_registration_view`, `participant.py` | Cover-story branding |
| 13 — Accessibility | `main.py::build_accessibility_overlay` | WCAG AA, font scale slider |
| 14 — Keystroke timing | `main.py::on_input_focus`, `on_text_change` | Focus latency + Cognitive_Revision |
| 15 — State machine | `ai_engine.py` | 3 phases with configurable system prompts |
| 16 — Telemetry schema | `telemetry.py` | Absolute 7-column CSV schema |

---

## IRB Compliance Notes

- **No raw PII is ever stored.** `scrub_message()` detects and destroys personal
  data before it reaches any log or AI call; only the category label is written.
- Participant profile stores only first name, last name, and a generated UUID.
- The registration screen never uses the words "simulation", "scam", "research test", or "fraud".
- The app **never** triggers a scam scenario on a manual launch; the simulation
  hook is only shown when the researcher activates a scenario via push notification
  (external trigger — not implemented in this codebase; handled by study protocol).
- Debrief and trauma-informed protocols are handled by the research team per the
  PCTI Care Lab design; the app surfaces no distressing content outside a live session.
