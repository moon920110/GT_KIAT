"""FastAPI server: JSON API for the agent + static simulation page.

Run:  uv run python -m nami.server   (or: uv run uvicorn nami.server:app --reload)
Open: http://127.0.0.1:8765
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .agent import NamiAgent
from .prompt import STABLE_SYSTEM_PROMPT, runtime_block
from .scenario import DEMO_COMMANDS, EXTRA_COMMANDS, GROUND_TRUTH, INTENTS, PREFERENCE_LABELS, PREFERENCES, RuntimeState, Session

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("nami.server")

SIM_DIR = Path(__file__).resolve().parent.parent / "sim"

app = FastAPI(title="Nami Agent Sim", version="0.2.0")
agent = NamiAgent()
sessions: dict[str, Session] = {}

TRI_FIELDS = ("phone_removed_verified", "collection_safe", "retry_authorized")


def _get(session_id: str) -> Session:
    s = sessions.get(session_id)
    if s is None:
        raise HTTPException(404, f"unknown session {session_id}")
    return s


# ----------------------------------------------------------------- schemas
class ChatIn(BaseModel):
    session_id: str
    text: str
    expected_intent: Optional[str] = None


class StateIn(BaseModel):
    """Partial update: None means "don't touch". Put a tri-state field name in
    ``unset`` to reset it to unconfirmed."""

    phone_removed_verified: Optional[bool] = None
    collection_safe: Optional[bool] = None
    retry_authorized: Optional[bool] = None
    retry_requested: Optional[bool] = None
    retry_execution_confirmed: Optional[bool] = None
    future_preference: Optional[str] = None
    fall_minutes_ago: Optional[int] = None
    unset: list[str] = []


# ------------------------------------------------------------------ routes
@app.get("/")
def index():
    return FileResponse(SIM_DIR / "index.html")


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "provider": agent.provider.name,
        "model": agent.model,
        "effort": agent.effort,
        "mock": agent.mock,
        "api_key_present": bool(os.environ.get("OPENAI_API_KEY" if agent.provider.name == "openai" else "ANTHROPIC_API_KEY")),
        "sessions": len(sessions),
    }


@app.get("/api/scenario")
def scenario():
    return {
        "ground_truth": GROUND_TRUTH,
        "intents": INTENTS,
        "preferences": PREFERENCES,
        "preference_labels": PREFERENCE_LABELS,
        "demo_commands": DEMO_COMMANDS,
        "extra_commands": EXTRA_COMMANDS,
    }


@app.get("/api/prompt")
def prompt(session_id: Optional[str] = None):
    state = _get(session_id).state if session_id else RuntimeState()
    return {"stable": STABLE_SYSTEM_PROMPT, "runtime": runtime_block(state)}


@app.post("/api/sessions")
def create_session():
    s = agent.new_session()
    sessions[s.id] = s
    return {"session_id": s.id, "state": s.state.to_dict()}


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    s = _get(session_id)
    return {"session_id": s.id, "state": s.state.to_dict(), "transcript": s.transcript, "ended": s.ended}


@app.post("/api/sessions/{session_id}/reset")
def reset_session(session_id: str, keep_state: bool = True):
    s = _get(session_id)
    s.reset(keep_state=keep_state)
    return {"session_id": s.id, "state": s.state.to_dict()}


@app.put("/api/sessions/{session_id}/state")
def put_state(session_id: str, body: StateIn):
    s = _get(session_id)
    st = s.state
    for name in TRI_FIELDS:
        if name in body.unset:
            setattr(st, name, None)
        elif getattr(body, name) is not None:
            setattr(st, name, getattr(body, name))
    if body.retry_requested is not None:
        st.retry_requested = body.retry_requested
    if body.retry_execution_confirmed is not None:
        st.retry_execution_confirmed = body.retry_execution_confirmed
    if body.future_preference is not None:
        if body.future_preference not in PREFERENCES:
            raise HTTPException(422, f"future_preference must be one of {PREFERENCES}")
        st.future_preference = body.future_preference
    if body.fall_minutes_ago is not None:
        st.fall_minutes_ago = max(0, body.fall_minutes_ago)
    return {"session_id": s.id, "state": st.to_dict(), "runtime_block": runtime_block(st)}


@app.post("/api/chat")
def chat(body: ChatIn):
    s = _get(body.session_id)
    reply = agent.respond(s, body.text)
    out = reply.to_dict()
    out["session_id"] = s.id
    out["state"] = s.state.to_dict()
    if body.expected_intent:
        out["expected_intent"] = body.expected_intent
        out["intent_match"] = body.expected_intent == reply.intent
    log.info("[%s] %s -> %s | %s", s.id, body.text, reply.intent, reply.speech)
    return out


def main() -> None:
    import uvicorn

    port = int(os.environ.get("NAMI_PORT", "8765"))
    uvicorn.run("nami.server:app", host="127.0.0.1", port=port, reload=False)


if __name__ == "__main__":
    main()
