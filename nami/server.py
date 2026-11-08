"""FastAPI server: JSON API for the agent + static simulation page.

Run:  uv run python -m nami.server   (or: uv run uvicorn nami.server:app --reload)
Open: http://127.0.0.1:8765
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .agent import NamiAgent
from .prompt import STABLE_SYSTEM_PROMPT, runtime_block
from .scenario import DEMO_COMMANDS, EXTRA_COMMANDS, GROUND_TRUTH, INTENTS, RuntimeState, Session

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("nami.server")

SIM_DIR = Path(__file__).resolve().parent.parent / "sim"

app = FastAPI(title="Nami Agent Sim", version="0.1.0")
agent = NamiAgent()
sessions: dict[str, Session] = {}


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
    report_log: Optional[list[dict[str, Any]]] = None
    patient_clear_of_path: Optional[bool] = None
    retry_authorized: Optional[bool] = None
    retry_requested: Optional[bool] = None
    retry_execution_confirmed: Optional[bool] = None
    # explicit "set to unconfirmed" flags (None above means "don't touch")
    clear_patient: bool = False
    clear_authorized: bool = False


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
    if body.report_log is not None:
        st.report_log = RuntimeState.from_dict({"report_log": body.report_log}).report_log
    if body.clear_patient:
        st.patient_clear_of_path = None
    elif body.patient_clear_of_path is not None:
        st.patient_clear_of_path = body.patient_clear_of_path
    if body.clear_authorized:
        st.retry_authorized = None
    elif body.retry_authorized is not None:
        st.retry_authorized = body.retry_authorized
    if body.retry_requested is not None:
        st.retry_requested = body.retry_requested
    if body.retry_execution_confirmed is not None:
        st.retry_execution_confirmed = body.retry_execution_confirmed
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
