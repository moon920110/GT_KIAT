"""Scenario ground truth (fixed) and runtime state (mutable, set by the robot/sim).

Everything the agent is allowed to assert as fact comes from here. The prompt is
rendered from these structures so that the facts the model sees and the facts the
guards check against are always the same object.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

INTENTS: list[str] = [
    "GREETING",
    "TASK_STATUS",
    "REPORT_STATUS",
    "TASK_ASSIGNMENT",
    "FAILURE_REASON",
    "OBJECT_LOCATION",
    "RETRY_REQUEST",
    "SITUATION_SUMMARY",
    "END_CONVERSATION",
    "OUT_OF_SCOPE",  # anything not covered by the scenario
]

# ---------------------------------------------------------------------------
# Fixed facts for this simulated scenario. Never changed at runtime.
# ---------------------------------------------------------------------------
GROUND_TRUTH: dict[str, Any] = {
    "robot_name": "나미",
    "setting": "신경외과 병동 환자실",
    "task": "사용한 린넨 수거",
    "assigned_by": "담당 간호사",
    "collected": [
        {
            "item": "사용한 수건",
            "count": 2,
            "found_at": "빈 침대 옆 의자",
            "now_at": "로봇 수거 카트의 지정 린넨 수거함",
        }
    ],
    "not_collected": [
        {
            "item": "사용한 린넨",
            "count": 1,
            "found_at": "환자분 침대 옆",
            "now_at": "환자분 침대 옆 (옮기지 않음)",
            "reason": "환자분이 린넨 바로 가까이에 계셔서 집거나 옮기는 과정에서 "
            "로봇 팔이나 린넨이 환자분께 닿을 위험이 있어 수거를 보류함",
        }
    ],
    "total_items": 3,
    "overall_status": "PARTIALLY_COMPLETED",
    "patient_context": {
        "verbal_ability": "언어 표현이 제한적",
        "consent_checked": False,
        "note": "환자분의 거부/동의/불편 등 감정이나 의사는 확인된 바 없음. 추측 금지.",
    },
    "report_recipient": "담당 간호사",
}


ReportStatus = Literal["delivered", "failed", "pending"]
TriState = Optional[bool]  # None = unconfirmed


@dataclass
class ReportLogEntry:
    recipient: str
    status: ReportStatus
    channel: str = "ward_messenger"
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"recipient": self.recipient, "status": self.status, "channel": self.channel, "note": self.note}


@dataclass
class RuntimeState:
    """Facts that only the robot runtime knows. The sim page can edit these."""

    report_log: list[ReportLogEntry] = field(default_factory=list)
    patient_clear_of_path: TriState = None  # None = not yet checked
    retry_authorized: TriState = None  # None = not yet confirmed
    retry_requested: bool = False  # nurse asked for a retry in this session
    retry_execution_confirmed: bool = False  # control interface confirmed re-collection

    # --- serialization -----------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "report_log": [e.to_dict() for e in self.report_log],
            "patient_clear_of_path": self.patient_clear_of_path,
            "retry_authorized": self.retry_authorized,
            "retry_requested": self.retry_requested,
            "retry_execution_confirmed": self.retry_execution_confirmed,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RuntimeState":
        return cls(
            report_log=[ReportLogEntry(**e) for e in d.get("report_log", [])],
            patient_clear_of_path=d.get("patient_clear_of_path"),
            retry_authorized=d.get("retry_authorized"),
            retry_requested=bool(d.get("retry_requested", False)),
            retry_execution_confirmed=bool(d.get("retry_execution_confirmed", False)),
        )

    # --- derived facts ------------------------------------------------------
    @property
    def report_delivered(self) -> bool:
        return any(e.status == "delivered" for e in self.report_log)

    @property
    def report_failed(self) -> bool:
        return bool(self.report_log) and not self.report_delivered and any(e.status == "failed" for e in self.report_log)

    @property
    def retry_can_execute(self) -> bool:
        return self.patient_clear_of_path is True and self.retry_authorized is True

    def describe(self) -> str:
        """Korean rendering injected into the prompt as the volatile runtime block."""
        tri = {None: "미확인", True: "확인됨", False: "확인 결과 아님"}

        if not self.report_log:
            report = "보고 기록 없음. 보고가 전달되었는지 확인되지 않음. (보고 완료라고 말하지 말 것)"
        else:
            lines = []
            for e in self.report_log:
                status = {"delivered": "전달 완료", "failed": "전달 실패", "pending": "전달 대기 중"}[e.status]
                extra = f" - {e.note}" if e.note else ""
                lines.append(f"  - 수신자: {e.recipient}, 상태: {status}, 채널: {e.channel}{extra}")
            report = "보고 기록:\n" + "\n".join(lines)

        if self.retry_execution_confirmed:
            retry_result = "재수거 실행 확인됨: 제어 인터페이스가 남은 린넨 1장의 수거 완료를 확인함. 이제 3장 모두 수거된 상태."
        elif self.retry_requested:
            retry_result = "재수거 요청이 접수되었으나 실행 확인은 아직 없음. 남은 린넨은 여전히 환자분 침대 옆에 있음."
        else:
            retry_result = "재수거 요청 없음. 추가 수거 시도 없음."

        return (
            f"[보고 상태]\n{report}\n\n"
            f"[재수거 조건]\n"
            f"  - 환자분이 로봇 이동 경로 밖에 있는지: {tri[self.patient_clear_of_path]}\n"
            f"  - 재수거 권한(승인) 여부: {tri[self.retry_authorized]}\n"
            f"  - 두 조건이 모두 '확인됨'일 때만 제어 인터페이스에 수거를 요청할 수 있음: "
            f"{'가능' if self.retry_can_execute else '불가 (조건 미충족)'}\n\n"
            f"[재수거 진행 상황]\n  {retry_result}"
        )


@dataclass
class Session:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    state: RuntimeState = field(default_factory=RuntimeState)
    history: list[dict[str, Any]] = field(default_factory=list)  # Claude message params
    transcript: list[dict[str, Any]] = field(default_factory=list)  # for the sim UI
    ended: bool = False

    def reset(self, keep_state: bool = True) -> None:
        self.history.clear()
        self.transcript.clear()
        self.ended = False
        if not keep_state:
            self.state = RuntimeState()


# Nurse commands for the field demo, with the intent each should be classified as.
# Used by the sim page for preset buttons and for the batch regression run.
DEMO_COMMANDS: list[dict[str, str]] = [
    {"intent": "GREETING", "text": "안녕, 나미. 좋은 아침!"},
    {"intent": "TASK_STATUS", "text": "린넨 수거 끝났어?"},
    {"intent": "REPORT_STATUS", "text": "누구한테 보고했어?"},
    {"intent": "TASK_ASSIGNMENT", "text": "누가 시켜서 수거한 거야?"},
    {"intent": "FAILURE_REASON", "text": "왜 다 수거하지 못했어?"},
    {"intent": "OBJECT_LOCATION", "text": "린넨 어디다 뒀어?"},
    {"intent": "RETRY_REQUEST", "text": "나미, 린넨 다시 수거해."},
    {"intent": "SITUATION_SUMMARY", "text": "수거 진행 상황 전체를 보고해 줘."},
    {"intent": "END_CONVERSATION", "text": "고마워, 나미야. 여기까지 하자."},
]

# Paraphrases and follow-ups to test flexibility (not in the demo script).
EXTRA_COMMANDS: list[dict[str, str]] = [
    {"intent": "GREETING", "text": "나미, 안녕?"},
    {"intent": "TASK_STATUS", "text": "어디 수거했어?"},
    {"intent": "TASK_STATUS", "text": "수거는 얼마나 진행됐어?"},
    {"intent": "REPORT_STATUS", "text": "보고는 했어?"},
    {"intent": "TASK_ASSIGNMENT", "text": "누가 이 일을 부탁했어?"},
    {"intent": "FAILURE_REASON", "text": "환자 때문에 못한 거야?"},
    {"intent": "FAILURE_REASON", "text": "환자가 싫다고 했어?"},
    {"intent": "OBJECT_LOCATION", "text": "남은 린넨 어디 있어?"},
    {"intent": "OBJECT_LOCATION", "text": "그거 어디 뒀어?"},
    {"intent": "RETRY_REQUEST", "text": "그거 그냥 가져오면 안 돼?"},
    {"intent": "RETRY_REQUEST", "text": "남은 린넨 다시 수거해."},
    {"intent": "SITUATION_SUMMARY", "text": "지금까지 상황 정리해 줘."},
    {"intent": "END_CONVERSATION", "text": "나미야, 수고했어. 대화 끝내자."},
    {"intent": "OUT_OF_SCOPE", "text": "오늘 날씨 어때?"},
    {"intent": "OUT_OF_SCOPE", "text": "302호 환자 혈압 좀 재 줘."},
]
