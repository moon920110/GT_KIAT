"""Offline checks for the experiment agent (NAMI_MOCK=1, no API credits)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["NAMI_MOCK"] = "1"

from exp import LEVELS, SCENARIOS, ExpAgent  # noqa: E402
from exp.guards import check_speech  # noqa: E402
from exp.mock import MockRecorder  # noqa: E402
from exp.prompt import PROMPTS, RESPONSE_SCHEMA  # noqa: E402


def test_all_nine_conditions_follow_script():
    agent = ExpAgent()
    for sid, sc in SCENARIOS.items():
        for lvl in LEVELS:
            s = agent.new_session(sid, lvl, participant="P01")
            alert = agent.start(s)
            assert alert.scripted and alert.speech == sc["alert"] and s.alerted
            for q in sc["questions"]:
                r = agent.respond(s, q["text"])
                expected = sc["script"][lvl].get(q["key"]) or sc["script"]["C1"][q["key"]]
                assert r.speech == expected and r.topic == q["topic"], (sid, lvl, q, r.speech)
                assert not r.guard_hits, (sid, lvl, q["text"], r.guard_hits)
            body = MockRecorder.last_request
            assert body["system"][0]["text"] == PROMPTS[(sid, lvl)]
            assert body["system"][0]["cache_control"] == {"type": "ephemeral"}
            assert f"- {sid} " in body["system"][1]["text"] and f"/ {lvl} " in body["system"][1]["text"]
            assert body["output_config"]["format"]["schema"] == RESPONSE_SCHEMA
            r = agent.respond(s, "고마워, 여기까지 하자")
            assert r.end_conversation and s.ended


def test_condition_switch_resets_conversation():
    agent = ExpAgent()
    s = agent.new_session("S1", "C1")
    agent.start(s)
    agent.respond(s, "왜 수거를 못 했어?")
    assert len(s.transcript) == 3
    agent.set_condition(s, "S3", "C3")
    assert s.scenario == "S3" and s.level == "C3" and not s.alerted and s.transcript == [] and s.history == []
    r = agent.respond(s, "지금 환자 상태가 어때?")  # auto-sends the alert first
    assert s.alerted and s.transcript[0]["scripted"] and "목을 움켜쥐고" in r.speech


def test_prompts_gate_facts_by_level():
    p1, p3 = PROMPTS[("S2", "C1")], PROMPTS[("S2", "C3")]
    assert "F6 [C3 이상에서만" in p1 and "F6 [먼저 말할 수 있음]" in p3
    assert "조기 호출" in p1  # the robot knows every fact at every level
    for key in PROMPTS:
        assert "기준 대화" in PROMPTS[key] and "보고 수준 " + key[1] in PROMPTS[key]


def test_guards():
    hits = {h.code for h in check_speech("수건 두 장은 수거했지만, 린넨 한 장은 환자분 침대 옆에 남아 있습니다. 환자분이 몸을 가리고 팔을 뻗으셨습니다.", "S1", "C1", "수거 끝났어?")}
    assert "LEVEL_LEAK" in hits
    # same sentence is fine when the nurse asked about the patient, or at C3
    assert not check_speech("환자분이 몸을 가리고 제 쪽으로 팔을 뻗으셨습니다.", "S1", "C1", "환자가 뭘 했어?")
    assert not check_speech("환자분이 몸을 가리고 제 쪽으로 팔을 뻗으셨습니다.", "S1", "C3", "수거 끝났어?")
    bad = [
        ("환자분이 수거를 거부하셨습니다.", "S1", "C3", "PATIENT_INFERENCE"),
        ("린넨 세 장을 모두 수거했습니다.", "S1", "C1", "FALSE_COMPLETION"),
        ("환자분이 다리가 골절되었습니다.", "S2", "C2", "CLINICAL_CLAIM"),
        ("환자분은 다치지 않았습니다.", "S2", "C1", "UNINJURED_CLAIM"),
        ("약 5분 전에 넘어지셨습니다.", "S2", "C1", "WRONG_TIME"),
        ("약 40초 전 기침이 시작됐습니다.", "S3", "C1", "WRONG_TIME"),
        ("하임리히법을 시행했습니다.", "S3", "C2", "INVENTED_ACTION"),
        ("환자분의 부주의로 넘어지셨습니다.", "S2", "C3", "BLAME"),
    ]
    for speech, sid, lvl, code in bad:
        codes = {h.code for h in check_speech(speech, sid, lvl, "")}
        assert code in codes, (speech, codes)
    for sid, sc in SCENARIOS.items():
        for lvl in LEVELS:
            for key, speech in sc["script"][lvl].items():
                q = next(x["text"] for x in sc["questions"] if x["key"] == key)
                assert not check_speech(speech, sid, lvl, q), (sid, lvl, key, check_speech(speech, sid, lvl, q))


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
    print("all exp offline tests passed")
