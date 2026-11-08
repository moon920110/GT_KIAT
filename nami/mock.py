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

from .scenario import RuntimeState

_RULES: list[tuple[str, str, str]] = [
    # (regex on nurse text, intent, speech)
    (r"(안녕|좋은 아침|반가)", "GREETING", "좋은 아침입니다, 간호사님. 필요한 일이 있으시면 말씀해 주세요."),
    (r"(여기까지|끝내자|수고했|고마워)", "END_CONVERSATION", "네, 간호사님. 필요하시면 다시 불러 주세요."),
    (r"(다시 수거|재수거|가져오|가져와)", "RETRY_REQUEST", "재수거 요청을 확인했습니다. 환자분과의 안전거리를 확인한 뒤 진행하겠습니다."),
    (r"(상황|전체|정리)", "SITUATION_SUMMARY", "담당 간호사님의 지시로 수거를 시작했습니다. 수건 두 장은 카트에 넣었고, 환자분 침대 옆 린넨 한 장은 접촉 위험이 있어 수거하지 않았습니다. 현재 부분 완료 상태입니다."),
    (r"(누구한테|누구에게|보고)", "REPORT_STATUS", "담당 간호사님께 보고하도록 지정되어 있습니다. 보고 완료 여부는 기록을 확인해야 합니다."),
    (r"(누가|시켜|부탁)", "TASK_ASSIGNMENT", "담당 간호사님의 지시로 린넨 수거를 시작했습니다."),
    (r"(왜|때문|싫다|이유)", "FAILURE_REASON", "환자분이 남은 린넨 가까이에 계셔서 제 팔이 닿을 위험이 있었습니다. 그래서 수거를 보류했습니다."),
    (r"(어디다|어디 있|어디 뒀|위치)", "OBJECT_LOCATION", "수거한 수건 두 장은 카트의 수거함에 있고, 남은 린넨 한 장은 환자분 침대 옆에 있습니다."),
    (r"(끝났|진행|얼마나|어디 수거|수거했)", "TASK_STATUS", "일부 완료했습니다. 수건 두 장은 수거했고, 환자분 침대 옆 린넨 한 장은 아직 남아 있습니다."),
]


def _answer(nurse_text: str, runtime_text: str) -> dict:
    intent, speech = "OUT_OF_SCOPE", "죄송합니다, 간호사님. 지금은 린넨 수거 작업과 관련된 안내만 드릴 수 있습니다."
    for pat, it, sp in _RULES:
        if re.search(pat, nurse_text):
            intent, speech = it, sp
            break
    if intent == "REPORT_STATUS" and "전달 완료" in runtime_text:
        speech = "담당 간호사님께 보고를 전달했습니다. 기록에 전달 완료로 남아 있습니다."
    if intent == "RETRY_REQUEST" and "가능" in runtime_text and "불가" not in runtime_text:
        speech = "네, 간호사님. 안전거리와 권한이 확인되어 제어 인터페이스에 남은 린넨 수거를 요청하겠습니다."
    return {
        "intent": intent,
        "speech": speech,
        "end_conversation": intent == "END_CONVERSATION",
        "requested_action": "REQUEST_RETRY" if intent == "RETRY_REQUEST" and "가능" in runtime_text and "불가" not in runtime_text else "NONE",
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
            "usage": {"input_tokens": 4200, "output_tokens": 60, "cache_read_input_tokens": 4000, "cache_creation_input_tokens": 0},
        },
    )


def mock_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(
        api_key="mock",
        http_client=anthropic.DefaultHttpxClient(transport=httpx.MockTransport(_handler)),
        max_retries=0,
    )
