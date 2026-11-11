"""ExpAgent - robot reporter for the completeness experiment.

    agent = ExpAgent()
    s = agent.new_session("S2", "C3", participant="P07")
    alert = agent.start(s)             # fixed opening alert (scripted, no LLM call)
    reply = agent.respond(s, "넘어지기 전후에 어떤 일이 있었어?")

Switching the condition resets the conversation (``agent.set_condition``).
"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from nami.providers import Provider, ProviderResult, make_provider  # noqa: E402

from .guards import check_speech  # noqa: E402
from .prompt import PROMPTS, RESPONSE_SCHEMA, runtime_block  # noqa: E402
from .scenario import SCENARIOS, ExpSession  # noqa: E402

log = logging.getLogger("exp")

MAX_HISTORY_TURNS = 24
# Nurse text whose normalized similarity to a scripted question is at least this
# gets the scripted answer verbatim, with no model call (stimulus stays fixed per condition).
SCRIPT_MATCH_THRESHOLD = 0.8
FALLBACK_SPEECH = "죄송합니다, 간호사님. 지금 응답을 생성하지 못했습니다. 다시 한 번 말씀해 주시겠어요?"


@dataclass
class ExpReply:
    speech: str
    topic: str = "OTHER"
    end_conversation: bool = False
    scripted: bool = False  # True for the fixed opening alert and for scripted nurse questions
    provider: str = ""
    model: str = ""
    latency_ms: int = 0
    usage: dict[str, Any] = field(default_factory=dict)
    stop_reason: Optional[str] = None
    fallback_used: bool = False
    guard_hits: list[dict[str, str]] = field(default_factory=list)
    raw: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "speech": self.speech, "topic": self.topic, "end_conversation": self.end_conversation,
            "scripted": self.scripted, "provider": self.provider, "model": self.model,
            "latency_ms": self.latency_ms, "usage": self.usage, "stop_reason": self.stop_reason,
            "fallback_used": self.fallback_used, "guard_hits": self.guard_hits, "error": self.error,
        }


class ExpAgent:
    def __init__(self, provider: Optional[Provider] = None, provider_name: Optional[str] = None,
                 model: Optional[str] = None, effort: Optional[str] = None, timeout: float = 60.0) -> None:
        if provider is None:
            from .mock import mock_client

            provider = make_provider(provider_name, model, effort, timeout, schema=RESPONSE_SCHEMA, mock_client_factory=mock_client)
        self.provider = provider
        self.mock = os.environ.get("NAMI_MOCK") == "1"

    @property
    def model(self) -> str:
        return self.provider.model

    @property
    def effort(self) -> str:
        return getattr(self.provider, "effort", "")

    # ------------------------------------------------------------------ API
    def new_session(self, scenario: str = "S1", level: str = "C1", participant: str = "") -> ExpSession:
        s = ExpSession(participant=participant)
        s.set_condition(scenario, level)
        return s

    def set_condition(self, session: ExpSession, scenario: str, level: str) -> None:
        session.set_condition(scenario, level)

    def start(self, session: ExpSession) -> ExpReply:
        """Deliver the robot's fixed opening alert for the current scenario."""
        session.reset()
        alert = SCENARIOS[session.scenario]["alert"]
        reply = ExpReply(speech=alert, topic="STATUS", scripted=True, provider="script")
        payload = json.dumps({"speech": alert, "topic": "STATUS", "end_conversation": False}, ensure_ascii=False)
        # The alert is the first assistant turn; a user turn is required before it for the APIs.
        session.history.append({"role": "user", "content": "(로봇이 간호사님께 알림을 보냄)"})
        session.history.append({"role": "assistant", "content": payload})
        session.alerted = True
        session.transcript.append({"role": "robot", "ts": time.time(), **reply.to_dict()})
        return reply

    def respond(self, session: ExpSession, user_text: str) -> ExpReply:
        user_text = user_text.strip()
        if not user_text:
            return ExpReply(speech="네, 간호사님. 말씀해 주세요.", provider=self.provider.name)
        if not session.alerted:
            self.start(session)

        scripted = self._match_script(session, user_text)
        if scripted is not None:
            return self._scripted_reply(session, user_text, *scripted)

        stable = PROMPTS[(session.scenario, session.level)]
        history = self._trim(session.history)
        t0 = time.perf_counter()
        try:
            result = self.provider.complete(stable, runtime_block(session), history, user_text)
        except Exception as e:
            log.exception("LLM call failed")
            return ExpReply(speech=FALLBACK_SPEECH, provider=self.provider.name, model=self.model,
                            latency_ms=int((time.perf_counter() - t0) * 1000), error=f"{type(e).__name__}: {e}")
        latency_ms = int((time.perf_counter() - t0) * 1000)

        reply = self._parse(result)
        reply.provider, reply.model, reply.latency_ms = self.provider.name, result.model, latency_ms
        reply.usage, reply.stop_reason, reply.fallback_used = result.usage, result.stop_reason, result.fallback_used
        reply.guard_hits = [h.to_dict() for h in check_speech(reply.speech, session.scenario, session.level, user_text)]

        if reply.end_conversation:
            session.ended = True
        session.history.append({"role": "user", "content": user_text})
        session.history.append(result.assistant_message or {"role": "assistant", "content": result.text})
        session.transcript.append({"role": "nurse", "text": user_text, "ts": time.time()})
        session.transcript.append({"role": "robot", "ts": time.time(), **reply.to_dict()})
        return reply

    # ------------------------------------------------------------ internals
    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"[\s\W_]+", "", text).lower()

    def _match_script(self, session: ExpSession, user_text: str) -> Optional[tuple[str, str, str]]:
        """Return (question_key, topic, answer) when the nurse's text is one of the condition's
        scripted questions (ignoring spacing/punctuation, allowing minor STT variation)."""
        sc = SCENARIOS[session.scenario]
        script = sc["script"][session.level]
        norm = self._normalize(user_text)
        if not norm:
            return None
        best: Optional[tuple[float, str, str, str]] = None
        for q in sc["questions"]:
            if q["key"] not in script:
                continue
            ratio = SequenceMatcher(None, norm, self._normalize(q["text"])).ratio()
            if best is None or ratio > best[0]:
                best = (ratio, q["key"], q["topic"], script[q["key"]])
        if best and best[0] >= SCRIPT_MATCH_THRESHOLD:
            return best[1:]
        return None

    def _scripted_reply(self, session: ExpSession, user_text: str, key: str, topic: str, answer: str) -> ExpReply:
        reply = ExpReply(speech=answer, topic=topic, scripted=True, provider="script")
        payload = json.dumps({"speech": answer, "topic": topic, "end_conversation": False}, ensure_ascii=False)
        session.history.append({"role": "user", "content": user_text})
        session.history.append({"role": "assistant", "content": payload})
        session.transcript.append({"role": "nurse", "text": user_text, "ts": time.time()})
        session.transcript.append({"role": "robot", "ts": time.time(), "script_key": key, **reply.to_dict()})
        log.info("scripted answer %s/%s %s for %r", session.scenario, session.level, key, user_text)
        return reply

    def _parse(self, result: ProviderResult) -> ExpReply:
        if result.refusal:
            return ExpReply(speech=FALLBACK_SPEECH, error=f"refusal: {result.refusal}")
        try:
            data = json.loads(result.text)
            return ExpReply(speech=str(data.get("speech", "")).strip() or FALLBACK_SPEECH,
                            topic=str(data.get("topic", "OTHER")),
                            end_conversation=bool(data.get("end_conversation", False)), raw=result.text)
        except json.JSONDecodeError:
            log.warning("Non-JSON model output: %r", result.text[:200])
            return ExpReply(speech=result.text.strip() or FALLBACK_SPEECH, raw=result.text, error="invalid_json")

    @staticmethod
    def _trim(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(history) <= MAX_HISTORY_TURNS:
            return list(history)
        trimmed = history[-MAX_HISTORY_TURNS:]
        while trimmed and trimmed[0]["role"] != "user":
            trimmed = trimmed[1:]
        return trimmed
