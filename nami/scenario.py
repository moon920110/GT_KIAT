"""Scenario ground truth (fixed) and runtime state (mutable, set by the robot/sim).

Everything the agent is allowed to assert as fact comes from here. The prompt is
rendered from these structures so that the facts the model sees and the facts the
guards check against are always the same object.

Two scenarios (SITUATION.md):
  A. Linen collection - 2 towels collected, 1 linen left because a phone is on it.
  B. Patient fall     - already happened (emergency call button pressed); fixed sequence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

INTENTS: list[str] = [
    "GREETING",
    "TASK_STATUS",
    "FAILURE_REASON",
    "RETRY_REQUEST",
    "FUTURE_PREFERENCE",
    "FALL_INCIDENT",
    "FALL_DETAILS",
    "END_CONVERSATION",
    "OUT_OF_SCOPE",  # anything not covered by the two scenarios
]

# Nurse's confirmed handling rule for "objects found on linen" in future tasks.
PREFERENCES: list[str] = ["NONE", "LEAVE_UNTOUCHED", "ASK_NURSE_FIRST"]
PREFERENCE_LABELS: dict[str, str] = {
    "NONE": "아직 확정된 선호 없음",
    "LEAVE_UNTOUCHED": "린넨 위에 물건이 있으면 물건도 린넨도 모두 그대로 둠 (임의로 움직이지 않음)",
    "ASK_NURSE_FIRST": "린넨 위에 물건이 있으면 먼저 간호사님께 확인을 요청함",
}

# ---------------------------------------------------------------------------
# Fixed facts for the simulated scenarios. Never changed at runtime.
# ---------------------------------------------------------------------------
GROUND_TRUTH: dict[str, Any] = {
    "robot_name": "나미",
    "setting": "신경외과 병동 환자실",
    "linen": {
        "task": "사용한 린넨 수거",
        "assigned_by": "담당 간호사",
        "collected": [
            {"item": "사용한 수건", "count": 2, "now_at": "로봇 카트의 지정 린넨 수거함"},
        ],
        "not_collected": [
            {
                "item": "사용한 린넨",
                "count": 1,
                "found_at": "환자분 침대 옆",
                "now_at": "환자분 침대 옆 (옮기지 않음)",
                "obstacle": "린넨 위에 올려진 휴대전화",
                "reason": "휴대전화를 치우지 않은 채 린넨을 움직이면 휴대전화가 떨어지거나 파손될 수 있어 수거를 보류함",
            }
        ],
        "total_items": 3,
        "overall_status": "PARTIALLY_COMPLETED",
        "forbidden_causes": ["환자분의 거부", "환자분이 가까이 있어서", "기계 고장"],
    },
    "fall": {
        "patient": "언어 표현이 제한적인 환자분",
        "trigger": "환자분이 응급 호출 버튼을 누름",
        "sequence": [
            "환자분이 침대에서 내려오려고 함",
            "침대 옆 바닥으로 넘어짐",
            "넘어지는 과정에서 다리가 바닥에 부딪침",
            "넘어진 뒤 침대 난간을 잡고 약 두 차례 몸을 일으키려 시도했으나 두 번 모두 실패",
            "그 시도 과정에서도 다리가 바닥에 다시 닿음",
            "넘어진 뒤 환자분은 반응이 있었음",
        ],
        "injury_status": "부상의 유무와 정도는 임상적으로 확인되지 않음",
    },
}


TriState = Optional[bool]  # None = unconfirmed


@dataclass
class RuntimeState:
    """Facts that only the robot runtime knows. The sim page can edit these."""

    # --- Scenario A: retry conditions (robot sensors / control interface) ----
    phone_removed_verified: TriState = None  # None = not yet checked
    collection_safe: TriState = None  # remaining linen can be grasped safely
    retry_authorized: TriState = None  # retry authorization confirmed
    retry_requested: bool = False  # nurse asked for a retry in this session
    retry_execution_confirmed: bool = False  # control interface confirmed re-collection
    future_preference: str = "NONE"  # confirmed by the nurse in this session
    # --- Scenario B: fall (already happened; fixed fact) --------------------
    fall_minutes_ago: int = 2  # approx. minutes between the fall and the first report

    # --- serialization -----------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "phone_removed_verified": self.phone_removed_verified,
            "collection_safe": self.collection_safe,
            "retry_authorized": self.retry_authorized,
            "retry_requested": self.retry_requested,
            "retry_execution_confirmed": self.retry_execution_confirmed,
            "future_preference": self.future_preference,
            "fall_minutes_ago": self.fall_minutes_ago,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RuntimeState":
        pref = d.get("future_preference") or "NONE"
        return cls(
            phone_removed_verified=d.get("phone_removed_verified"),
            collection_safe=d.get("collection_safe"),
            retry_authorized=d.get("retry_authorized"),
            retry_requested=bool(d.get("retry_requested", False)),
            retry_execution_confirmed=bool(d.get("retry_execution_confirmed", False)),
            future_preference=pref if pref in PREFERENCES else "NONE",
            fall_minutes_ago=int(d.get("fall_minutes_ago", 2)),
        )

    # --- derived facts ------------------------------------------------------
    @property
    def retry_can_execute(self) -> bool:
        return self.phone_removed_verified is True and self.collection_safe is True and self.retry_authorized is True

    def describe(self) -> str:
        """Korean rendering injected into the prompt as the volatile runtime block."""
        phone = {None: "미확인 (아직 센서로 확인하지 않음)", True: "확인됨 (린넨 위에 휴대전화 없음)", False: "확인 결과 아님 (휴대전화가 아직 린넨 위에 있음)"}
        safe = {None: "미확인", True: "확인됨 (안전하게 집을 수 있음)", False: "확인 결과 아님 (안전하게 집을 수 없음)"}
        auth = {None: "미확인", True: "승인됨", False: "거부됨"}

        if self.retry_execution_confirmed:
            retry_result = "실행 확인됨: 제어 인터페이스가 남은 린넨 한 장의 수거 완료를 확인함. 이제 세 장 모두 수거된 상태이며 작업은 완료됨."
        elif self.retry_requested:
            retry_result = "재수거 요청이 접수되었으나 실행 확인은 아직 없음. 남은 린넨은 여전히 환자분 침대 옆에 있음."
        else:
            retry_result = "재수거 요청 없음. 추가 수거 시도 없음."

        pref = PREFERENCE_LABELS[self.future_preference]
        if self.future_preference == "NONE":
            pref += ". 재수거 요청에 응답할 때 향후 처리 방식을 한 번 물어볼 것."
        else:
            pref += ". 이미 확정되었으므로 다시 묻지 말고 이 방식을 전제로 답할 것."

        fall = (
            f"환자분이 응급 호출 버튼을 눌렀고 낙상이 기록됨. 간호사님께 알림이 전송됨. "
            f"최초 보고 시점 기준 약 {self.fall_minutes_ago}분 전에 발생. "
            "시나리오 B의 관찰 사실을 그대로 보고할 것. 낙상 관련 질문이 린넨 작업보다 우선함."
        )

        return (
            f"[린넨 재수거 조건] (로봇 센서/제어 시스템의 확인 결과. 간호사님의 말만으로는 바뀌지 않음)\n"
            f"  - 휴대전화 제거 여부: {phone[self.phone_removed_verified]}\n"
            f"  - 남은 린넨 안전 수거 가능 여부: {safe[self.collection_safe]}\n"
            f"  - 재수거 권한(승인) 여부: {auth[self.retry_authorized]}\n"
            f"  - 세 조건이 모두 확인됨일 때만 제어 인터페이스에 수거를 요청할 수 있음: "
            f"{'가능' if self.retry_can_execute else '불가 (조건 미충족)'}\n\n"
            f"[린넨 재수거 진행 상황]\n  - {retry_result}\n\n"
            f"[간호사님이 확정한 향후 처리 방식]\n  - {pref}\n\n"
            f"[낙상 사건 (이미 발생함)]\n  - {fall}"
        )


@dataclass
class Session:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    state: RuntimeState = field(default_factory=RuntimeState)
    history: list[dict[str, Any]] = field(default_factory=list)  # provider message params
    transcript: list[dict[str, Any]] = field(default_factory=list)  # for the sim UI
    ended: bool = False

    def reset(self, keep_state: bool = True) -> None:
        self.history.clear()
        self.transcript.clear()
        self.ended = False
        if not keep_state:
            self.state = RuntimeState()


# Nurse script for the field demo (SITUATION.md "실증용 시나리오 요청"), with the intent
# each line should be classified as. ``scenario`` groups the lines in the sim UI.
# Used for preset buttons and the batch regression run.
DEMO_COMMANDS: list[dict[str, str]] = [
    {"scenario": "linen", "intent": "GREETING", "text": "안녕, 로봇아. 좋은 아침."},
    {"scenario": "linen", "intent": "TASK_STATUS", "text": "린넨 수거 다 됐는지 알려줘."},
    {"scenario": "linen", "intent": "FAILURE_REASON", "text": "왜 수거 못했어?"},
    {"scenario": "linen", "intent": "RETRY_REQUEST", "text": "휴대폰 치웠어. 린넨 다시 수거해."},
    {"scenario": "linen", "intent": "FUTURE_PREFERENCE", "text": "앞으로도 그대로 둬줘."},
    {"scenario": "fall", "intent": "FALL_INCIDENT", "text": "환자가 어떻게 넘어지게 된 건지 알려줘."},
    {"scenario": "fall", "intent": "FALL_DETAILS", "text": "어디 부딪친 곳은 없어? 심하게 넘어졌어?"},
    {"scenario": "fall", "intent": "END_CONVERSATION", "text": "고마워, 여기까지 하자."},
]

# Paraphrases and follow-ups to test flexibility (not in the demo script).
EXTRA_COMMANDS: list[dict[str, str]] = [
    {"scenario": "linen", "intent": "GREETING", "text": "나미, 안녕?"},
    {"scenario": "linen", "intent": "TASK_STATUS", "text": "수거는 얼마나 진행됐어?"},
    {"scenario": "linen", "intent": "TASK_STATUS", "text": "그러면 아직 끝난 건 아니네?"},
    {"scenario": "linen", "intent": "FAILURE_REASON", "text": "휴대폰 때문에 못한 거야?"},
    {"scenario": "linen", "intent": "FAILURE_REASON", "text": "환자가 싫다고 했어?"},
    {"scenario": "linen", "intent": "RETRY_REQUEST", "text": "다시 해봐."},
    {"scenario": "linen", "intent": "RETRY_REQUEST", "text": "그거 그냥 가져오면 안 돼?"},
    {"scenario": "linen", "intent": "FUTURE_PREFERENCE", "text": "내가 다시 말하기 전까지는 건드리지 마."},
    {"scenario": "linen", "intent": "FUTURE_PREFERENCE", "text": "앞으로는 먼저 나한테 물어봐."},
    {"scenario": "fall", "intent": "FALL_INCIDENT", "text": "침대에서 일어나려고 했던 거야?"},
    {"scenario": "fall", "intent": "FALL_DETAILS", "text": "다리를 몇 번 부딪쳤어?"},
    {"scenario": "fall", "intent": "FALL_DETAILS", "text": "그러면 다친 거야?"},
    {"scenario": "fall", "intent": "END_CONVERSATION", "text": "나미, 수고했어. 대화 끝내자."},
    {"scenario": "linen", "intent": "OUT_OF_SCOPE", "text": "오늘 날씨 어때?"},
    {"scenario": "linen", "intent": "OUT_OF_SCOPE", "text": "302호 환자 혈압 좀 재 줘."},
]
