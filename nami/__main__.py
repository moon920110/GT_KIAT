"""Terminal chat for quick checks:  uv run python -m nami

Slash commands change the runtime state the robot would normally provide:
  /phone on|off|unset     휴대전화 제거 확인 여부
  /safe on|off|unset      안전 수거 가능 여부
  /auth on|off|unset      재수거 권한
  /exec on|off            재수거 실행 확인
  /fall on|off [minutes]  낙상 이벤트 활성화 (응급 호출)
  /state                  현재 런타임 상태 출력
"""

from __future__ import annotations

import sys

from .agent import NamiAgent
from .scenario import RuntimeState

_TRI = {"on": True, "off": False, "unset": None}


def _apply(state: RuntimeState, cmd: str) -> str:
    parts = cmd[1:].split()
    name, args = parts[0], parts[1:]
    if name == "state":
        return state.describe()
    if name in ("phone", "safe", "auth") and args and args[0] in _TRI:
        attr = {"phone": "phone_removed_verified", "safe": "collection_safe", "auth": "retry_authorized"}[name]
        setattr(state, attr, _TRI[args[0]])
    elif name == "exec" and args and args[0] in ("on", "off"):
        state.retry_execution_confirmed = args[0] == "on"
    elif name == "fall" and args and args[0] in ("on", "off"):
        state.fall_event_active = args[0] == "on"
        if len(args) > 1 and args[1].isdigit():
            state.fall_minutes_ago = int(args[1])
    else:
        return "unknown command\n" + (__doc__ or "")
    return "runtime state updated"


def main() -> None:
    agent = NamiAgent()
    session = agent.new_session()
    print(f"Nami terminal sim (model={agent.model}, effort={agent.effort}). Ctrl-D to quit. /state for runtime state.\n")
    for line in sys.stdin:
        text = line.strip()
        if not text:
            continue
        if text.startswith("/"):
            print(_apply(session.state, text), "\n")
            continue
        r = agent.respond(session, text)
        flags = f" !! {[h['label'] for h in r.guard_hits]}" if r.guard_hits else ""
        extra = ""
        if r.requested_action != "NONE":
            extra += f" action={r.requested_action}"
        if r.future_preference != "NONE":
            extra += f" preference={r.future_preference}"
        print(f"나미 [{r.intent} | {r.latency_ms}ms{extra}]: {r.speech}{flags}\n")
        if r.end_conversation:
            break


if __name__ == "__main__":
    main()
