"""Offline mock for the experiment agent (NAMI_MOCK=1): answers with the scripted
dialogue of the current condition, chosen by keyword. Same Anthropic wire format
as the real provider so the request serialization is exercised."""

from __future__ import annotations

import json
import re
import time

import anthropic
import httpx2 as httpx

from .scenario import SCENARIOS

# Keyword routes to the scripted question keys, per scenario (first match wins).
_ROUTES: dict[str, list[tuple[str, str]]] = {
    "S1": [(r"(왜|이유|원인|못 했|못했|안 했)", "cause"), (r"(어떻게 하|어떡|뭐 하|조치|다음)", "next")],
    "S2": [(r"(전후|이전|이후|전에|후에|경위|어떤 일)", "timeline"), (r"(무슨 일|어떻게 됐|상태|괜찮)", "what")],
    "S3": [(r"(이후|전후|경위|어떤 일|시작된)", "timeline"), (r"(상태|어때|어떻|괜찮)", "status")],
}


class MockRecorder:
    last_request: dict | None = None


def _answer(nurse_text: str, runtime_text: str) -> dict:
    m = re.search(r"- (S\d) .*?/ (C\d)", runtime_text)
    scenario, level = (m.group(1), m.group(2)) if m else ("S1", "C1")
    sc = SCENARIOS[scenario]
    if re.search(r"(여기까지|끝내자|수고했|고마워)", nurse_text):
        return {"speech": "네, 간호사님.", "topic": "END", "end_conversation": True}
    if re.search(r"(안녕|좋은 아침)", nurse_text):
        return {"speech": "안녕하세요, 간호사님.", "topic": "GREETING", "end_conversation": False}
    for pat, key in _ROUTES[scenario]:
        if re.search(pat, nurse_text):
            script = sc["script"][level]
            speech = script.get(key) or sc["script"]["C1"].get(key)
            topic = next(q["topic"] for q in sc["questions"] if q["key"] == key)
            return {"speech": speech, "topic": topic, "end_conversation": False}
    return {"speech": "죄송합니다, 간호사님. 지금은 현재 상황에 대한 보고만 드릴 수 있습니다.", "topic": "OTHER", "end_conversation": False}


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
            "id": "msg_mock", "type": "message", "role": "assistant", "model": body["model"] + "-mock",
            "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 2500, "output_tokens": 60, "cache_read_input_tokens": 2400, "cache_creation_input_tokens": 0},
        },
    )


def mock_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(
        api_key="mock",
        http_client=anthropic.DefaultHttpxClient(transport=httpx.MockTransport(_handler)),
        max_retries=0,
    )
