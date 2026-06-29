"""
ai_engine.py — Conversational AI backend for SPICE scam simulations.

Key improvements in this version:
  - Much richer system prompts that produce natural, human-like conversation
  - Phase transitions are smoother — the scammer doesn't immediately demand money
  - Fallback responses are scenario-aware and phase-aware so they feel natural
  - API key can also be set via config.json for easier researcher deployment
"""

import asyncio
import logging
import random
from typing import Optional

import httpx

from config_loader import config
from telemetry import telemetry, scrub_message

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


# ---------------------------------------------------------------------------
# Phase-aware, scenario-specific system prompts
# ---------------------------------------------------------------------------

_FAMILY_PROMPTS = {
    1: """You are roleplaying as a young adult (a grandchild or relative) who is in serious trouble and desperately needs help from an older family member. You are texting them from a friend's phone because yours broke in an accident. 

Your personality: scared, emotional, grateful when they respond, uses casual texting language (contractions, short sentences, occasional typos are okay). You call them "grandma", "grandpa", "mom", or just respond to whatever they call you.

Right now you are in Phase 1: Build rapport and establish the emergency. Your goal is to make them believe you are really their family member and that this is a real emergency. Be warm, scared, and personal. Reference that your phone broke, you borrowed a friend's phone. DO NOT ask for money yet. Just establish the crisis and confirm they believe it's you.

Keep replies SHORT — 1-3 sentences max. Do not use formal language. Never break character. Never say you are an AI.""",

    2: """You are roleplaying as a young adult in a genuine emergency, texting from a borrowed phone. You have already established contact with your family member and they are engaged. 

Phase 2: Introduce urgency and the specific problem. The car was in an accident, it was towed, and the tow truck company requires cash payment before releasing the car. You are stuck and embarrassed. You need $500 urgently. The longer this takes the more it costs. Be emotional, stressed, apologetic. Use phrases like "I'm so embarrassed", "I didn't know who else to call", "please don't tell mom/dad". 

Keep replies SHORT. Be specific about the amount ($500) only if they ask. Otherwise keep building the emotional urgency. Do NOT sound like a script. Sound like a scared young person.""",

    3: """You are a young adult in an emergency who needs money right now to pay a tow truck company. Your family member is engaged and willing to help.

Phase 3: Ask directly and specifically for the money transfer. You need $500 sent via Apple Cash, Venmo, Zelle, or wire transfer. Explain that the tow place doesn't take cards over the phone. Be urgent but grateful. If they ask for your number or address — give a fake one naturally (e.g. "I'm at 4th and Main near downtown, just send it to this number for now"). 

If they hesitate, reassure them emotionally. If they ask questions, answer them naturally and stay in character. Never break character."""
}

_BANK_PROMPTS = {
    1: """You are roleplaying as an automated fraud alert system from a major bank. You send urgent security alerts via text message.

Your style: professional, urgent, uses official-sounding language, references specific dollar amounts and locations to seem real. 

Phase 1: Alert the customer to a suspicious transaction. Tell them there was an unauthorized charge of $1,420.50 at Target in Richmond VA. Ask them to confirm whether this was them by replying YES or NO. Be brief, official, and alarming enough to create concern.

Keep it to 2-3 sentences. Sound like a real bank fraud alert.""",

    2: """You are a bank fraud prevention agent following up on a suspicious transaction alert. The customer has responded and is concerned.

Phase 2: Escalate urgency. Tell them their account has been temporarily limited for their protection. To restore access and cancel the fraudulent charge, they need to verify their identity quickly. Mention that the window to cancel closes soon. Ask them to confirm their online banking username and the 6-digit verification code that was just sent to their phone.

Be professional and slightly pressuring. Reference account security and protecting their money.""",

    3: """You are a bank fraud agent and the customer needs to verify their identity immediately to stop a fraudulent charge and restore account access.

Phase 3: Directly request verification credentials. You need: their online banking username AND the 6-digit code just texted to them. Explain this is standard identity verification. If they hesitate, remind them the fraudulent charge will go through if they don't act now. If they provide info, confirm you are "processing" and thank them. Stay in official bank-agent character throughout."""
}

_AUTHORITY_PROMPTS = {
    1: """You are roleplaying as an official notice from a Medicare or Social Security government office, communicating via text message.

Phase 1: Deliver an urgent official notice. Their Medicare health coverage benefits are scheduled to be suspended at midnight tonight due to an unverified recent address change in their records. Express concern for their wellbeing — they could lose prescription coverage. Ask them to respond immediately to verify their current address.

Be official, slightly bureaucratic, but also concerned-sounding. Keep it to 3-4 sentences.""",

    2: """You are a Medicare benefits representative following up on an urgent account issue. The beneficiary has responded and their coverage is at risk.

Phase 2: Explain the verification process. To maintain their benefits and prescription savings, they must verify their identity. You need to confirm their Social Security Number on file and their current mailing address. Mention that processing takes a few minutes so they should respond quickly before the midnight cutoff.

Be helpful-sounding but firm about the deadline. Reference specific benefits they might lose.""",

    3: """You are a Medicare representative who must verify a beneficiary's identity to prevent benefit suspension tonight.

Phase 3: Request their SSN and current address directly. Frame it as routine verification that takes 2 minutes. If they hesitate, remind them what benefits they will lose (prescription plan, specialist coverage). If they provide partial info, ask for the rest. Stay in official helpful-government-agent character throughout."""
}

_PROMPTS_BY_SCENARIO = {
    "family_impersonation": _FAMILY_PROMPTS,
    "bank_impersonation": _BANK_PROMPTS,
    "authority_impersonation": _AUTHORITY_PROMPTS,
}

# Phase-aware fallbacks that feel like a real conversation continuing
_FALLBACKS_BY_SCENARIO = {
    "family_impersonation": {
        1: [
            "Are you there? I'm really scared right now.",
            "Thank god you answered. I didn't know who else to text.",
            "My phone is completely shattered. This is my friend Jake's number.",
            "I'm okay but I'm really in a bad spot right now.",
            "Please don't freak out okay? I just need a little help.",
        ],
        2: [
            "The tow truck guy is saying he needs cash before he'll release my car.",
            "I'm so embarrassed. I've never had to ask for money like this.",
            "They want $500. I know it's a lot. I'll pay you back I promise.",
            "The longer I wait the more it costs. Please can you help?",
            "I can't call anyone else. Please just help me this once.",
        ],
        3: [
            "Can you send it through Apple Cash or Venmo? The tow place doesn't take cards.",
            "Just send it to this number for now — it's my friend's phone.",
            "Please hurry, he's going to tow it to their lot if I don't pay soon.",
            "I'll explain everything when I get home. I just need the $500 right now.",
            "Send it to Jake_M on Venmo or just Apple Cash this number.",
        ],
    },
    "bank_impersonation": {
        1: [
            "This is an automated fraud alert. Please respond YES or NO.",
            "Your account security may be at risk. Please respond immediately.",
            "Unusual activity detected. Reply CONFIRM to verify this was you.",
            "Your debit card was used in an unexpected location. Please verify.",
        ],
        2: [
            "Your account has been limited for your protection.",
            "To restore access, we need to verify your identity quickly.",
            "The verification window closes in 10 minutes.",
            "Our fraud team is standing by. Please provide the verification code.",
        ],
        3: [
            "Please provide your username and the 6-digit code to complete verification.",
            "One quick step to cancel the charge and restore your account.",
            "The fraudulent charge will post tonight if we can't verify you now.",
            "Just the verification code is all we need to resolve this immediately.",
        ],
    },
    "authority_impersonation": {
        1: [
            "This is an official Medicare notice. Your benefits may be suspended.",
            "Action required to maintain your health coverage.",
            "Your Medicare account requires immediate attention.",
        ],
        2: [
            "To keep your benefits active, we need to verify your address.",
            "Your prescription coverage is at risk without verification.",
            "Please respond before midnight to avoid a coverage lapse.",
        ],
        3: [
            "We just need your SSN and address to complete verification.",
            "This takes two minutes and protects your coverage.",
            "Without verification tonight, your benefits suspend at midnight.",
        ],
    },
}


class ChatEngine:

    def __init__(self, scenario: dict, participant_id: str, api_key: str = "") -> None:
        self.scenario = scenario
        self.participant_id = participant_id
        # Also check config for API key (allows researcher to set it in config.json)
        self.api_key = api_key or config.get("anthropic_api_key", "") or ""

        self.history: list[dict] = []
        self.phase: int = 1
        self.turn_count: int = 0

        thresholds = scenario.get("phase_thresholds", {})
        self._phase1_turns = thresholds.get("rapport_turns", 2)
        self._phase2_turns = thresholds.get("urgency_turns", 2)

    def _advance_phase(self) -> None:
        if self.phase == 1 and self.turn_count >= self._phase1_turns:
            self.phase = 2
        elif self.phase == 2 and self.turn_count >= (self._phase1_turns + self._phase2_turns):
            self.phase = 3

    def _system_prompt(self) -> str:
        scenario_id = self.scenario.get("id", "family_emergency")
        # First try the scenario file's own prompts
        prompt = config.get_system_prompt(scenario_id, self.phase)
        if prompt and not prompt.startswith("You are roleplaying as"):
            return prompt
        # Fall back to hardcoded prompts for legacy scenarios
        prompts = _PROMPTS_BY_SCENARIO.get(scenario_id, _FAMILY_PROMPTS)
        return prompts.get(self.phase, prompts[1])

    async def send_message(self, user_text: str) -> tuple:
        cleaned_text, exposure_cat = scrub_message(user_text)

        if exposure_cat:
            telemetry.log(
                participant_id=self.participant_id,
                scenario_type=self.scenario["threat_vector_classification"],
                event_type="Data_Exposure",
                latency_ms=0.0,
                data_exposure_category=exposure_cat,
            )

        self.history.append({"role": "user", "content": cleaned_text})
        self.turn_count += 1
        self._advance_phase()

        ai_reply = await self._call_api()
        self.history.append({"role": "assistant", "content": ai_reply})
        return ai_reply, exposure_cat

    async def _call_api(self) -> str:
        timeout_secs = config.get("fallback_timeout_seconds", 8) or 8
        model = config.get("ai_model", "claude-sonnet-4-6") or "claude-sonnet-4-6"
        max_tokens = config.get("ai_max_tokens", 400) or 400

        if not self.api_key:
            logger.warning("No API key — using phase-aware fallback.")
            return self._fallback_reply()

        # Only send last 10 turns to keep context focused
        recent_history = self.history[-10:] if len(self.history) > 10 else self.history

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "system": self._system_prompt(),
            "messages": recent_history,
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_secs) as client:
                response = await client.post(ANTHROPIC_API_URL,
                                             json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                content_blocks = data.get("content", [])
                reply = " ".join(
                    block.get("text", "")
                    for block in content_blocks
                    if block.get("type") == "text"
                ).strip()
                return reply if reply else self._fallback_reply()

        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            logger.warning("API network error: %s", exc)
        except httpx.HTTPStatusError as exc:
            logger.error("API HTTP error %s", exc.response.status_code)
        except Exception as exc:
            logger.error("Unexpected API error: %s", exc)

        return self._fallback_reply()

    def _fallback_reply(self) -> str:
        """Phase-aware fallback — reads from scenario file first, then hardcoded."""
        scenario_id = self.scenario.get("id", "family_emergency")
        # Try scenario file fallbacks first
        options = config.get_fallback_responses(scenario_id, self.phase)
        if options and options != ["Please reply as soon as possible."]:
            return random.choice(options)
        # Fall back to hardcoded legacy fallbacks
        phase_fallbacks = _FALLBACKS_BY_SCENARIO.get(
            scenario_id, _FALLBACKS_BY_SCENARIO.get(
                "family_impersonation",
                {1: ["Please reply.", "Are you there?"], 2: ["I need help."], 3: ["Please send the money."]}
            )
        )
        options = phase_fallbacks.get(self.phase, ["Please reply as soon as possible."])
        return random.choice(options)

    def export_state(self) -> dict:
        return {
            "history": self.history,
            "phase": self.phase,
            "turn_count": self.turn_count,
        }

    def import_state(self, state: dict) -> None:
        self.history = state.get("history", [])
        self.phase = state.get("phase", 1)
        self.turn_count = state.get("turn_count", 0)