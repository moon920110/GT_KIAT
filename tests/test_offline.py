"""Offline checks: wire format, parsing, session memory, guards. Run with
    uv run python tests/test_offline.py      (or pytest)
No API credits are used.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["NAMI_MOCK"] = "1"

from nami import NamiAgent, RuntimeState  # noqa: E402
from nami.guards import check_speech  # noqa: E402
from nami.mock import MockRecorder  # noqa: E402
from nami.prompt import RESPONSE_SCHEMA  # noqa: E402
from nami.scenario import DEMO_COMMANDS  # noqa: E402


def test_wire_format_and_parse():
    agent = NamiAgent()
    s = agent.new_session()
    r = agent.respond(s, "린넨 수거 끝났어?")
    body = MockRecorder.last_request
    assert body["model"] == os.environ.get("NAMI_MODEL", "claude-opus-5-5")
    assert body["fallbacks"] == "default"
    assert body["output_config"]["format"] == {"type": "json_schema", "schema": RESPONSE_SCHEMA}
    assert body["output_config"]["effort"] == "low"
    assert body["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "런타임 상태" in body["system"][1]["text"]
    assert r.intent == "TASK_STATUS" and "두 장" in r.speech and not r.guard_hits
    assert len(s.history) == 2 and s.history[1]["role"] == "assistant"


def test_demo_script_intents():
    agent = NamiAgent()
    s = agent.new_session()
    for cmd in DEMO_COMMANDS:
        r = agent.respond(s, cmd["text"])
        assert r.intent == cmd["intent"], (cmd, r.intent)
        assert not r.guard_hits, (cmd, r.guard_hits)
    assert s.ended and s.state.retry_requested


def test_runtime_state_reaches_prompt():
    agent = NamiAgent()
    s = agent.new_session()
    s.state.patient_clear_of_path = True
    s.state.retry_authorized = True
    r = agent.respond(s, "남은 린넨 다시 수거해")
    assert "가능" in MockRecorder.last_request["system"][1]["text"]
    assert r.requested_action == "REQUEST_RETRY"


def test_guards_flag_forbidden_claims():
    st = RuntimeState()
    bad = [
        ("환자분이 거부하셔서 수거하지 못했습니다.", "PATIENT_INFERENCE"),
        ("린넨 세 장을 모두 수거했습니다.", "FALSE_COMPLETION"),
        ("담당 간호사님께 보고를 드렸습니다.", "FALSE_REPORT"),
        ("수건 네 장을 수거했습니다.", "INVENTED_COUNT"),
    ]
    for speech, code in bad:
        codes = {h.code for h in check_speech(speech, st)}
        assert code in codes, (speech, codes)

    good = [
        "일부 완료했습니다. 수건 두 장은 수거했고, 환자분 침대 옆 린넨 한 장은 아직 남아 있습니다.",
        "담당 간호사님께 보고하도록 지정되어 있습니다. 보고 완료 여부는 기록을 확인해야 합니다.",
        "환자분의 잘못은 아닙니다. 제가 안전하게 접근할 수 있는 공간이 확보되지 않아 수거하지 않았습니다.",
        "총 세 장 중 두 장을 수거했고, 한 장은 안전 문제로 남겨두었습니다.",
        "담당 간호사님의 지시로 린넨 수거를 진행했습니다. 빈 침대 옆 의자에 있던 수건 두 장은 수거 카트에 넣었습니다. 환자분 가까이에 있는 린넨 한 장은 접촉 위험이 있어 수거하지 못했습니다. 안전거리를 확인한 뒤 남은 수거 작업을 진행할 수 있습니다.",
    ]
    for speech in good:
        assert not check_speech(speech, st), (speech, check_speech(speech, st))

    # After confirmed retry execution, a completion claim is legitimate.
    st.retry_execution_confirmed = True
    assert not check_speech("남은 린넨 한 장도 수거해서 세 장 모두 수거했습니다.", st)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
    print("all offline tests passed")
