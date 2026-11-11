"""FastAPI server for the completeness experiment (separate from nami.server).

Run:  uv run python -m exp.server        -> http://127.0.0.1:8766
Port: NAMI_EXP_PORT (default 8766)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .agent import ExpAgent
from .prompt import PROMPTS, runtime_block
from .scenario import LEVEL_INFO, LEVELS, SCENARIO_IDS, SCENARIOS, TOPICS, ExpSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("exp.server")

SIM_DIR = Path(__file__).resolve().parent.parent / "sim"

app = FastAPI(title="Completeness Experiment Sim", version="0.1.0")
agent = ExpAgent()
sessions: dict[str, ExpSession] = {}


def _get(session_id: str) -> ExpSession:
    s = sessions.get(session_id)
    if s is None:
        raise HTTPException(404, f"unknown session {session_id}")
    return s


def _view(s: ExpSession) -> dict:
    return {"session_id": s.id, "scenario": s.scenario, "level": s.level, "participant": s.participant,
            "condition": s.condition_label(), "alerted": s.alerted, "ended": s.ended, "turns": len(s.transcript)}


class SessionIn(BaseModel):
    scenario: str = "S1"
    level: str = "C1"
    participant: str = ""


class ConditionIn(BaseModel):
    scenario: Optional[str] = None
    level: Optional[str] = None
    participant: Optional[str] = None


class ChatIn(BaseModel):
    session_id: str
    text: str


@app.get("/")
def index():
    return FileResponse(SIM_DIR / "exp.html")


@app.get("/api/health")
def health():
    return {"ok": True, "provider": agent.provider.name, "model": agent.model, "effort": agent.effort, "mock": agent.mock,
            "api_key_present": bool(os.environ.get("OPENAI_API_KEY" if agent.provider.name == "openai" else "ANTHROPIC_API_KEY")),
            "sessions": len(sessions)}


@app.get("/api/conditions")
def conditions():
    return {"scenarios": {k: {kk: vv for kk, vv in v.items() if kk != "script"} | {"script": v["script"]} for k, v in SCENARIOS.items()},
            "scenario_ids": SCENARIO_IDS, "levels": LEVELS, "level_info": LEVEL_INFO, "topics": TOPICS}


@app.get("/api/prompt")
def prompt(scenario: str = "S1", level: str = "C1", session_id: Optional[str] = None):
    if session_id:
        s = _get(session_id)
        return {"stable": PROMPTS[(s.scenario, s.level)], "runtime": runtime_block(s)}
    if (scenario, level) not in PROMPTS:
        raise HTTPException(422, "unknown condition")
    return {"stable": PROMPTS[(scenario, level)], "runtime": runtime_block(ExpSession(scenario=scenario, level=level))}


@app.post("/api/sessions")
def create_session(body: SessionIn):
    try:
        s = agent.new_session(body.scenario, body.level, body.participant)
    except ValueError as e:
        raise HTTPException(422, str(e))
    sessions[s.id] = s
    return _view(s)


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    s = _get(session_id)
    return _view(s) | {"transcript": s.transcript}


@app.put("/api/sessions/{session_id}/condition")
def set_condition(session_id: str, body: ConditionIn):
    """Researcher switches scenario/level. Resets the conversation; call /start next."""
    s = _get(session_id)
    if body.participant is not None:
        s.participant = body.participant
    try:
        s.set_condition(body.scenario or s.scenario, body.level or s.level)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return _view(s)


@app.post("/api/sessions/{session_id}/start")
def start(session_id: str):
    """Robot sends its fixed opening alert (resets any prior conversation)."""
    s = _get(session_id)
    r = agent.start(s)
    log.info("[%s] %s ALERT | %s", s.id, s.condition_label(), r.speech)
    return r.to_dict() | {"session": _view(s)}


@app.post("/api/chat")
def chat(body: ChatIn):
    s = _get(body.session_id)
    r = agent.respond(s, body.text)
    log.info("[%s] %s | %s -> %s | %s", s.id, s.condition_label(), body.text, r.topic, r.speech)
    return r.to_dict() | {"session": _view(s)}


def main() -> None:
    import uvicorn

    port = int(os.environ.get("NAMI_EXP_PORT", "8766"))
    uvicorn.run("exp.server:app", host="127.0.0.1", port=port, reload=False)


if __name__ == "__main__":
    main()
