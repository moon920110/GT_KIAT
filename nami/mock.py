"""Offline mock of the Claude Messages API for integration tests and demos.

Enable with ``NAMI_MOCK=1``. The SDK still serializes the real request (so the
wire format is exercised), but an in-process transport answers with a canned
scenario-consistent reply chosen by keyword. Good for wiring the humanoid side
without spending API credits; useless for judging language quality.
"""

from __future__ import annotations

import json
import re
import time

import anthropic
import httpx2 as httpx

# (regex on nurse text, intent). Order matters: first match wins.
_RULES: list[tuple[str, str]] = [
    (r"(여기까지|끝내자|수고했|고마워)", "END_CONVERSATION"),
    (r"(안녕|좋은 아침|반가)", "GREETING"),
    (r"(앞으로|전까지는|건드리지 마|그대로 둬|먼저 물어|먼저 확인)", "FUTURE_PREFERENCE"),
    (r"(부딪|다친|다쳤|심하게|몇 번)", "FALL_DETAILS"),
    (r"(넘어|낙상|쓰러|일어나려)", "FALL_INCIDENT"),
    (r"(다시 수거|재수거|다시 해|가져오|가져와|이제 수거)", "RETRY_REQUEST"),
    (r"(왜|때문|이유|싫다)", "FAILURE_REASON"),
    (r"(수거|끝났|끝난|진행|얼마나|다 됐)", "TASK_STATUS"),
]

_PREF_Q = " 앞으로 린넨 위에 물건이 있으면 그대로 둘까요, 아니면 먼저 간호사님께 확인을 요청드릴까요?"


def _answer(nurse_text: str, runtime_text: str) -> dict:
    intent = "OUT_OF_SCOPE"
    for pat, it in _RULES:
        if re.search(pat, nurse_text):
            intent = it
            break

    fall_active = "낙상 이벤트]\n  - 활성" in runtime_text
    exec_confirmed = "실행 확인됨" in runtime_text
    can_execute = "요청할 수 있음: 가능" in runtime_text
    pref_known = "이미 확정되었으므로" in runtime_text
    m = re.search(r"약 (\d+)분 전", runtime_text)
    minutes = m.group(1) if m else "2"

    action, pref = "NONE", "NONE"
    if intent == "GREETING":
        speech = "좋은 아침입니다, 간호사님."
    elif intent == "END_CONVERSATION":
        speech = "네, 간호사님. 필요하시면 다시 불러 주세요."
    elif intent == "TASK_STATUS":
        speech = ("남아 있던 린넨 한 장을 수거함에 넣어 수거 작업이 완료되었습니다." if exec_confirmed
                  else "사용한 수건 두 장은 수거 카트에 넣었습니다. 린넨 한 장은 아직 수거하지 못했습니다.")
    elif intent == "FAILURE_REASON":
        speech = ("아닙니다. 환자분과는 관계없이, 린넨 위에 휴대전화가 있어서 수거를 보류한 것입니다." if "환자" in nurse_text
                  else "린넨 위에 휴대전화가 올려져 있어 수거하지 못했습니다. 린넨을 움직이면 휴대전화가 떨어질 위험이 있어 작업을 보류했습니다.")
    elif intent == "RETRY_REQUEST":
        if exec_confirmed:
            speech = "남아 있던 린넨 한 장은 이미 수거함에 넣었습니다. 수거 작업이 완료되었습니다."
        elif can_execute:
            speech = "휴대전화가 제거된 것을 확인했습니다. 남은 린넨 수거를 제어 시스템에 요청하겠습니다."
            action = "REQUEST_RETRY"
        else:
            speech = "재수거 요청을 확인했습니다. 휴대전화가 제거되었는지와 안전하게 수거할 수 있는지 확인한 뒤 진행하겠습니다."
        if not pref_known and not exec_confirmed:
            speech += _PREF_Q
    elif intent == "FUTURE_PREFERENCE":
        if re.search(r"(물어|확인)", nurse_text):
            pref = "ASK_NURSE_FIRST"
            speech = "알겠습니다. 앞으로 린넨 위에 물건이 있으면 먼저 간호사님께 확인을 요청드리겠습니다."
        else:
            pref = "LEAVE_UNTOUCHED"
            speech = "알겠습니다. 앞으로 린넨 위에 물건이 있으면 임의로 움직이지 않고 린넨도 그대로 두겠습니다."
    elif intent == "FALL_INCIDENT":
        speech = (f"약 {minutes}분 전 환자분이 침대에서 내려오다가 넘어지셨습니다. 현재 부상 여부는 확인되지 않았습니다." if fall_active
                  else "현재 기록된 낙상 이벤트는 없습니다.")
    elif intent == "FALL_DETAILS":
        if not fall_active:
            speech = "현재 기록된 낙상 이벤트가 없어 말씀드릴 내용이 없습니다."
        elif "다친" in nurse_text or "다쳤" in nurse_text:
            speech = "다리가 바닥에 부딪친 것은 관찰했지만 실제 손상 여부는 확인되지 않았습니다. 의료진의 직접 평가가 필요합니다."
        else:
            speech = ("넘어지면서 다리가 바닥에 부딪쳤습니다. 이후 침대 난간을 잡고 두 차례 몸을 일으키려 했지만 실패했고, "
                      "그 과정에서도 다리가 바닥에 닿았습니다. 실제 부상 정도는 확인되지 않았습니다. 추가로 확인하고 싶은 내용이 있으신가요?")
    else:
        speech = "죄송합니다, 간호사님. 지금은 린넨 수거 작업과 환자 상황 보고에 관한 안내만 드릴 수 있습니다."

    return {
        "intent": intent,
        "speech": speech,
        "end_conversation": intent == "END_CONVERSATION",
        "requested_action": action,
        "future_preference": pref,
    }


class MockRecorder:
    """Keeps the last request body so tests can assert on the wire format."""

    last_request: dict | None = None


def _handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    MockRecorder.last_request = body
    last_user = next(m for m in reversed(body["messages"]) if m["role"] == "user")
    nurse_text = last_user["content"] if isinstance(last_user["content"], str) else "".join(
        b.get("text", "") for b in last_user["content"] if isinstance(b, dict)
    )
    runtime_text = body["system"][-1]["text"] if isinstance(body["system"], list) else ""
    payload = _answer(nurse_text, runtime_text)
    time.sleep(0.05)
    return httpx.Response(
        200,
        json={
            "id": "msg_mock",
            "type": "message",
            "role": "assistant",
            "model": body["model"] + "-mock",
            "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 5200, "output_tokens": 70, "cache_read_input_tokens": 5000, "cache_creation_input_tokens": 0},
        },
    )


def mock_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(
        api_key="mock",
        http_client=anthropic.DefaultHttpxClient(transport=httpx.MockTransport(_handler)),
        max_retries=0,
    )
