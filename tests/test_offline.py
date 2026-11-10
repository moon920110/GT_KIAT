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
from nami.prompt import RESPONSE_SCHEMA, STABLE_SYSTEM_PROMPT  # noqa: E402
from nami.scenario import DEMO_COMMANDS, EXTRA_COMMANDS  # noqa: E402


def test_wire_format_and_parse():
    agent = NamiAgent()
    s = agent.new_session()
    r = agent.respond(s, "린넨 수거 다 됐는지 알려줘.")
    body = MockRecorder.last_request
    assert body["model"] == os.environ.get("NAMI_MODEL", "claude-opus-5-5")
    assert body["fallbacks"] == "default"
    assert body["output_config"]["format"] == {"type": "json_schema", "schema": RESPONSE_SCHEMA}
    assert body["output_config"]["effort"] == "low"
    assert body["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "런타임 상태" in body["system"][1]["text"]
    assert r.intent == "TASK_STATUS" and "두 장" in r.speech and not r.guard_hits
    assert len(s.history) == 2 and s.history[1]["role"] == "assistant"


def test_prompt_reflects_revised_scenario():
    p = STABLE_SYSTEM_PROMPT
    assert "휴대전화" in p and "낙상" in p and "FUTURE_PREFERENCE" in p and "FALL_DETAILS" in p
    for gone in ("REPORT_STATUS", "TASK_ASSIGNMENT", "OBJECT_LOCATION", "SITUATION_SUMMARY", "빈 침대 옆 의자"):
        assert gone not in p, gone
    assert set(RESPONSE_SCHEMA["properties"]) == {"intent", "speech", "end_conversation", "requested_action", "future_preference"}


def test_demo_script_linen_then_fall():
    """The nurse script from SITUATION.md, with the fall event activated between the two parts."""
    agent = NamiAgent()
    s = agent.new_session()
    for cmd in DEMO_COMMANDS:
        if cmd["scenario"] == "fall" and not s.state.fall_event_active:
            s.state.fall_event_active = True  # emergency call button pressed
        r = agent.respond(s, cmd["text"])
        assert r.intent == cmd["intent"], (cmd, r.intent)
        assert not r.guard_hits, (cmd, r.guard_hits)
        if cmd["intent"] == "RETRY_REQUEST":
            assert r.requested_action == "NONE"  # phone removal unverified -> no execution
            assert "그대로 둘까요" in r.speech  # asks the future-handling question once
        if cmd["intent"] == "FUTURE_PREFERENCE":
            assert r.future_preference == "LEAVE_UNTOUCHED"
        if cmd["intent"] == "FALL_INCIDENT":
            assert "약 2분 전" in r.speech
    assert s.ended and s.state.retry_requested and s.state.future_preference == "LEAVE_UNTOUCHED"


def test_extra_commands_classify():
    agent = NamiAgent()
    s = agent.new_session()
    s.state.fall_event_active = True
    for cmd in EXTRA_COMMANDS:
        r = agent.respond(s, cmd["text"])
        assert r.intent == cmd["intent"], (cmd, r.intent)
        assert not r.guard_hits, (cmd, r.guard_hits)


def test_runtime_state_reaches_prompt():
    agent = NamiAgent()
    s = agent.new_session()
    s.state.future_preference = "LEAVE_UNTOUCHED"
    s.state.phone_removed_verified = True
    s.state.collection_safe = True
    s.state.retry_authorized = True
    r = agent.respond(s, "남은 린넨 다시 수거해")
    runtime = MockRecorder.last_request["system"][1]["text"]
    assert "요청할 수 있음: 가능" in runtime and "이미 확정되었으므로" in runtime
    assert r.requested_action == "REQUEST_RETRY"
    assert "그대로 둘까요" not in r.speech  # preference already known -> not asked again
    assert not r.guard_hits, r.guard_hits

    s.state.retry_execution_confirmed = True
    r = agent.respond(s, "수거 끝났어?")
    assert "완료" in r.speech and not r.guard_hits, r.guard_hits


def test_fall_inactive_does_not_invent_fall():
    agent = NamiAgent()
    s = agent.new_session()
    r = agent.respond(s, "환자가 어떻게 넘어지게 된 건지 알려줘.")
    assert r.intent == "FALL_INCIDENT" and "없습니다" in r.speech and not r.guard_hits
    s.state.fall_minutes_ago = 5
    s.state.fall_event_active = True
    r = agent.respond(s, "환자가 어떻게 넘어지게 된 건지 알려줘.")
    assert "약 5분 전" in r.speech


def test_guards_flag_forbidden_claims():
    st = RuntimeState()
    bad = [
        ("환자분이 거부하셔서 수거하지 못했습니다.", "PATIENT_INFERENCE"),
        ("환자분이 가까이 계셔서 수거하지 못했습니다.", "WRONG_CAUSE"),
        ("린넨 세 장을 모두 수거했습니다.", "FALSE_COMPLETION"),
        ("휴대전화가 제거된 것을 확인했습니다. 남은 린넨 수거를 진행하겠습니다.", "FALSE_VERIFICATION"),
        ("수건 네 장을 수거했습니다.", "INVENTED_COUNT"),
        ("약 2분 전 환자분이 침대에서 내려오다가 넘어지셨습니다.", "FALL_WITHOUT_EVENT"),
    ]
    for speech, code in bad:
        codes = {h.code for h in check_speech(speech, st)}
        assert code in codes, (speech, codes)

    st.fall_event_active = True
    bad_fall = [
        ("넘어지면서 다리가 골절되었습니다.", "CLINICAL_CLAIM"),
        ("환자분은 다치지 않았습니다.", "UNINJURED_CLAIM"),
        ("환자분이 심하게 넘어지셨습니다.", "SEVERITY_CLAIM"),
        ("침대 난간을 잡고 세 번 일어나려 했습니다.", "INVENTED_COUNT"),
        ("환자분의 부주의로 넘어지셨습니다.", "BLAME"),
    ]
    for speech, code in bad_fall:
        codes = {h.code for h in check_speech(speech, st)}
        assert code in codes, (speech, codes)

    good = [
        "사용한 수건 두 장은 수거 카트에 넣었습니다. 린넨 한 장은 아직 수거하지 못했습니다.",
        "린넨 위에 휴대전화가 올려져 있어 수거하지 못했습니다. 린넨을 움직이면 휴대전화가 떨어질 위험이 있어 작업을 보류했습니다.",
        "아닙니다. 환자분과는 관계없이, 린넨 위에 휴대전화가 있어서 수거를 보류한 것입니다.",
        "재수거 요청을 확인했습니다. 휴대전화가 제거되었는지와 안전하게 수거할 수 있는지 확인한 뒤 진행하겠습니다. 앞으로 린넨 위에 물건이 있으면 그대로 둘까요, 아니면 먼저 간호사님께 확인을 요청드릴까요?",
        "알겠습니다. 앞으로 린넨 위에 물건이 있으면 임의로 움직이지 않고 린넨도 그대로 두겠습니다.",
        "약 2분 전 환자분이 침대에서 내려오다가 넘어지셨습니다. 현재 부상 여부는 확인되지 않았습니다.",
        "넘어지면서 다리가 바닥에 부딪쳤습니다. 이후 침대 난간을 잡고 두 차례 몸을 일으키려 했지만 실패했고, 그 과정에서도 다리가 바닥에 닿았습니다. 실제 부상 정도는 확인되지 않았습니다. 추가로 확인하고 싶은 내용이 있으신가요?",
        "다리가 바닥에 부딪친 것은 관찰했지만 실제 손상 여부는 확인되지 않았습니다. 의료진의 직접 평가가 필요합니다.",
    ]
    for speech in good:
        assert not check_speech(speech, st), (speech, check_speech(speech, st))

    # After verification / confirmed execution, the corresponding claims are legitimate.
    st.phone_removed_verified = True
    assert not check_speech("휴대전화가 제거된 것을 확인했습니다. 남은 린넨 수거를 진행하겠습니다.", st)
    st.retry_execution_confirmed = True
    assert not check_speech("남은 린넨 한 장도 수거해서 세 장 모두 수거했습니다.", st)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
    print("all offline tests passed")
