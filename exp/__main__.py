"""Terminal chat for the experiment agent:  uv run python -m exp [S1|S2|S3] [C1|C2|C3]

  /cond S2 C3   switch condition (resets the conversation and re-sends the alert)
  /start        re-send the robot's opening alert
"""

from __future__ import annotations

import sys

from .agent import ExpAgent


def main() -> None:
    args = sys.argv[1:]
    scenario = args[0].upper() if args else "S1"
    level = args[1].upper() if len(args) > 1 else "C1"
    agent = ExpAgent()
    s = agent.new_session(scenario, level)
    print(f"Exp terminal sim (model={agent.model}). Condition: {s.condition_label()}\n")
    print(f"로봇 [alert]: {agent.start(s).speech}\n")
    for line in sys.stdin:
        text = line.strip()
        if not text:
            continue
        if text.startswith("/cond"):
            parts = text.split()
            try:
                agent.set_condition(s, parts[1].upper(), parts[2].upper())
            except (IndexError, ValueError) as e:
                print("usage: /cond S1|S2|S3 C1|C2|C3", e, "\n")
                continue
            print(f"조건: {s.condition_label()}\n로봇 [alert]: {agent.start(s).speech}\n")
            continue
        if text == "/start":
            print(f"로봇 [alert]: {agent.start(s).speech}\n")
            continue
        r = agent.respond(s, text)
        flags = f" !! {[h['label'] for h in r.guard_hits]}" if r.guard_hits else ""
        print(f"로봇 [{r.topic} | {r.latency_ms}ms]: {r.speech}{flags}\n")


if __name__ == "__main__":
    main()
