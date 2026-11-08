"""Terminal chat for quick checks:  uv run python -m nami"""

from __future__ import annotations

import sys

from .agent import NamiAgent


def main() -> None:
    agent = NamiAgent()
    session = agent.new_session()
    print(f"Nami terminal sim (model={agent.model}, effort={agent.effort}). Ctrl-D to quit.\n")
    for line in sys.stdin:
        text = line.strip()
        if not text:
            continue
        r = agent.respond(session, text)
        flags = f" !! {[h['label'] for h in r.guard_hits]}" if r.guard_hits else ""
        print(f"나미 [{r.intent} | {r.latency_ms}ms]: {r.speech}{flags}\n")
        if r.end_conversation:
            break


if __name__ == "__main__":
    main()
