"""NamiAgent - provider-agnostic, scenario-locked conversational agent.

Usage (robot integration):

    agent = NamiAgent()                       # provider/model from .env
    session = agent.new_session()
    reply = agent.respond(session, "린넨 수거 끝났어?")
    tts.say(reply.speech)
    if reply.requested_action == "REQUEST_RETRY": control.request_collection(...)
    if reply.end_conversation: ...

Runtime facts (report log, retry conditions) live on ``session.state`` and are
owned by the robot runtime. Update them there and the next reply reflects them.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

# .env wins over already-exported shell variables, so a stale key in ~/.zshrc cannot shadow it.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from .guards import check_speech  # noqa: E402
from .prompt import STABLE_SYSTEM_PROMPT, runtime_block  # noqa: E402
from .providers import Provider, ProviderResult, make_provider  # noqa: E402
from .scenario import Session  # noqa: E402

log = logging.getLogger("nami")

MAX_HISTORY_TURNS = 24  # user+assistant messages kept in context
FALLBACK_SPEECH = "죄송합니다, 간호사님. 지금 응답을 생성하지 못했습니다. 다시 한 번 말씀해 주시겠어요?"


@dataclass
class AgentReply:
    intent: str
    speech: str
    end_conversation: bool = False
    requested_action: str = "NONE"
    # diagnostics for the sim page
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
            "intent": self.intent,
            "speech": self.speech,
            "end_conversation": self.end_conversation,
            "requested_action": self.requested_action,
            "provider": self.provider,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "usage": self.usage,
            "stop_reason": self.stop_reason,
            "fallback_used": self.fallback_used,
            "guard_hits": self.guard_hits,
            "error": self.error,
        }


class NamiAgent:
    def __init__(
        self,
        provider: Optional[Provider] = None,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        effort: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        self.provider = provider or make_provider(provider_name, model, effort, timeout)
        self.mock = os.environ.get("NAMI_MOCK") == "1"

    @property
    def model(self) -> str:
        return self.provider.model

    @property
    def effort(self) -> str:
        return getattr(self.provider, "effort", "")

    # ------------------------------------------------------------------ API
    def new_session(self) -> Session:
        return Session()

    def respond(self, session: Session, user_text: str) -> AgentReply:
        user_text = user_text.strip()
        if not user_text:
            return AgentReply(intent="OUT_OF_SCOPE", speech="네, 간호사님. 말씀해 주세요.", provider=self.provider.name)

        history = self._trim(session.history)
        t0 = time.perf_counter()
        try:
            result = self.provider.complete(STABLE_SYSTEM_PROMPT, runtime_block(session.state), history, user_text)
        except Exception as e:  # SDK-specific error classes differ per provider
            log.exception("LLM call failed")
            return AgentReply(
                intent="OUT_OF_SCOPE", speech=FALLBACK_SPEECH, provider=self.provider.name, model=self.model,
                latency_ms=int((time.perf_counter() - t0) * 1000), error=f"{type(e).__name__}: {e}",
            )
        latency_ms = int((time.perf_counter() - t0) * 1000)

        reply = self._parse(result)
        reply.provider = self.provider.name
        reply.model = result.model
        reply.latency_ms = latency_ms
        reply.usage = result.usage
        reply.stop_reason = result.stop_reason
        reply.fallback_used = result.fallback_used
        reply.guard_hits = [h.to_dict() for h in check_speech(reply.speech, session.state)]

        # Update session memory
        if reply.intent == "RETRY_REQUEST":
            session.state.retry_requested = True
        if reply.end_conversation:
            session.ended = True
        session.history.append({"role": "user", "content": user_text})
        session.history.append(result.assistant_message or {"role": "assistant", "content": result.text})
        session.transcript.append({"role": "nurse", "text": user_text, "ts": time.time()})
        session.transcript.append({"role": "nami", "ts": time.time(), **reply.to_dict()})
        return reply

    # ------------------------------------------------------------ internals
    def _parse(self, result: ProviderResult) -> AgentReply:
        if result.refusal:
            return AgentReply(intent="OUT_OF_SCOPE", speech=FALLBACK_SPEECH, error=f"refusal: {result.refusal}")
        try:
            data = json.loads(result.text)
            return AgentReply(
                intent=str(data.get("intent", "OUT_OF_SCOPE")),
                speech=str(data.get("speech", "")).strip() or FALLBACK_SPEECH,
                end_conversation=bool(data.get("end_conversation", False)),
                requested_action=str(data.get("requested_action", "NONE")),
                raw=result.text,
            )
        except json.JSONDecodeError:
            log.warning("Non-JSON model output: %r", result.text[:200])
            return AgentReply(intent="OUT_OF_SCOPE", speech=result.text.strip() or FALLBACK_SPEECH, raw=result.text, error="invalid_json")

    @staticmethod
    def _trim(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(history) <= MAX_HISTORY_TURNS:
            return list(history)
        trimmed = history[-MAX_HISTORY_TURNS:]
        while trimmed and trimmed[0]["role"] != "user":
            trimmed = trimmed[1:]
        return trimmed
