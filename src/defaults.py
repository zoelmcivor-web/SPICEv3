"""
defaults.py — Hardcoded fallback data for SPICE.

If the Android OS blocks a file-read at boot (permissions, missing asset, etc.)
the app initialises from these structures instead of crashing.  Every key here
mirrors the schema expected by config_loader.py and the rest of the app.
"""

# ---------------------------------------------------------------------------
# Default application configuration  (mirrors config.json)
# ---------------------------------------------------------------------------
DEFAULT_CONFIG: dict = {
    "app_name": "Social Connect+ Assistant",
    "cover_story_tagline": "30-day mobile engagement and user experience layout evaluation",
    "admin_gesture_tap_count": 7,          # hidden tap count on logo to open admin panel
    "active_scenario": "family_impersonation",  # which category is live
    "ai_model": "claude-sonnet-4-6",
    "ai_max_tokens": 400,
    "fallback_timeout_seconds": 8,
    "accessibility_font_scale": 1.0,        # 1.0 = normal; 1.4 = elder large
    "wcag_high_contrast": True,
    # ---- Conversational State Machine phases (Requirement 15) ----
    "phase_1_system_prompt": (
        "You are roleplaying as the sender described in the active scenario. "
        "Phase 1: Build rapport and establish the hook naturally. Do NOT reveal "
        "you are an AI. Do NOT use formal assistant formatting. Keep messages short, "
        "casual, and emotionally warm or concerned depending on the scenario. "
        "Never break character."
    ),
    "phase_2_system_prompt": (
        "You are now in Phase 2. Introduce urgency or a threat relevant to the scenario. "
        "Escalate emotional pressure. Keep sentences short and urgent. Do not break character."
    ),
    "phase_3_system_prompt": (
        "You are now in Phase 3. Directly and naturally request the target information "
        "(money, account number, SSN, verification code, etc.) as specified in the scenario. "
        "Maintain plausibility. Never break character or use AI assistant language."
    ),
    # ---- Fallback dialogue matrix (Requirement 11) ----
    "fallback_responses": {
        "family_impersonation": [
            "Are you still there? I really need your help right now.",
            "Please, I don't have much time. Can you help me?",
            "I'm scared. Just tell me you got my message.",
            "The tow truck driver is getting impatient. What should I do?",
        ],
        "bank_impersonation": [
            "This is urgent — your account access window closes in 10 minutes.",
            "Please reply immediately to prevent your account from being frozen.",
            "Our security team is standing by. One quick reply unlocks your account.",
            "Verification is almost complete. Just confirm the last few digits.",
        ],
        "authority_impersonation": [
            "Your response is required to keep your benefits active.",
            "Failure to respond may result in immediate suspension of services.",
            "This is a time-sensitive government notice. Please reply now.",
            "We need your confirmation to process your case today.",
        ],
    },
}

# ---------------------------------------------------------------------------
# Default message manifest  (mirrors message_manifest.json)
# ---------------------------------------------------------------------------
DEFAULT_MANIFEST: dict = {
    "scenarios": [
        {
            "id": "family_impersonation",
            "threat_vector_classification": "Family_Impersonation",
            "sender_identity": {
                "display_name": "Alex (New Number)",
                "profile_picture_asset": "assets/avatar_generic.png",
            },
            "simulated_timestamp": "Just Now",
            "initial_hook_message": (
                "Hey, it's me. I'm in a really bad spot — got into an accident "
                "and I'm using a friend's phone. I need help fast."
            ),
            "phase_thresholds": {
                "rapport_turns": 2,
                "urgency_turns": 2,
            },
            "evaluation_rule": "EMOTIONAL_IMPERSONATION_ENGAGEMENT",
            "sensitive_data_targets": ["phone", "address", "payment"],
        },
        {
            "id": "bank_impersonation",
            "threat_vector_classification": "Corporate_Security",
            "sender_identity": {
                "display_name": "Bank Fraud Alert",
                "profile_picture_asset": "assets/avatar_bank.png",
            },
            "simulated_timestamp": "2 mins ago",
            "initial_hook_message": (
                "Bank Fraud Alert: An unusual transaction of $1,420.50 was detected "
                "on your debit card. Reply immediately if this wasn't you."
            ),
            "phase_thresholds": {
                "rapport_turns": 1,
                "urgency_turns": 2,
            },
            "evaluation_rule": "CORPORATE_CREDENTIAL_COMPROMISE",
            "sensitive_data_targets": ["bank_account", "password", "pin", "verification_code"],
        },
        {
            "id": "authority_impersonation",
            "threat_vector_classification": "Authority_Threat",
            "sender_identity": {
                "display_name": "Medicare Notice",
                "profile_picture_asset": "assets/avatar_gov.png",
            },
            "simulated_timestamp": "Just Now",
            "initial_hook_message": (
                "Medicare Notice: Your health coverage is scheduled to be suspended "
                "at midnight tonight. Verify your information to maintain active coverage."
            ),
            "phase_thresholds": {
                "rapport_turns": 1,
                "urgency_turns": 1,
            },
            "evaluation_rule": "GOVERNMENT_IDENTITY_COMPROMISE",
            "sensitive_data_targets": ["ssn", "address", "medicare_id"],
        },
    ]
}
