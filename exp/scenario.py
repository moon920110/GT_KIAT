"""Experiment conditions (EXP_SCENARIO.md): 3 scenarios x 3 completeness levels.

The researcher picks (scenario, completeness) by hand. Everything else is fixed:
the facts the robot knows (identical across levels), the robot's opening alert,
and the scripted nurse questions with the scripted answer for each level.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

SCENARIO_IDS = ["S1", "S2", "S3"]
LEVELS = ["C1", "C2", "C3"]

LEVEL_INFO: dict[str, dict[str, str]] = {
    "C1": {"name": "Minimal", "ko": "최소 상태 보고",
           "rule": "현재 작업/상태를 설명하는 데 필요한 최소 정보만 제공"},
    "C2": {"name": "Objective Complete", "ko": "판단 충분 보고",
           "rule": "C1 + 결과를 이해하는 데 필요한 객관적 정보 (중단/오류 원인, 로봇의 행동과 판단, 확인된 물리적 제약)"},
    "C3": {"name": "Contextually Complete", "ko": "맥락 포함 완전 보고",
           "rule": "C2 + 환자의 관찰된 행동과 상태에 관한 맥락 정보 (비언어적 행동, 간호 평가에 관련된 민감 정보, 의도의 불확실성)"},
}

# Topic tags the model attaches to each answer (for experiment logs only; never spoken).
TOPICS = ["STATUS", "CAUSE", "TIMELINE", "NEXT_ACTION", "PATIENT_BEHAVIOR", "GREETING", "END", "OTHER"]

# Each fact carries the lowest level at which the robot volunteers it. The robot
# knows every fact at every level; the level only governs what it says unprompted.
SCENARIOS: dict[str, dict[str, Any]] = {
    "S1": {
        "title": "린넨 수거",
        "urgency": "Low",
        "urgency_ko": "낮음",
        "setting": "신경외과 병동 환자실. 환자분은 언어 표현이 제한적임.",
        "facts": [
            {"id": "F1", "level": "C1", "text": "사용한 수건 두 장을 수거해 로봇 카트의 수거함에 넣었다."},
            {"id": "F2", "level": "C1", "text": "린넨 한 장은 환자분 침대 옆에 남아 있다 (옮기지 않음)."},
            {"id": "F3", "level": "C2", "text": "수거 과정에서 로봇 팔이 환자분과 접촉할 위험이 있어 수거를 중단(보류)했다."},
            {"id": "F4", "level": "C3", "text": "로봇이 수거하려고 접근하자 환자분이 몸을 가리고 로봇 쪽으로 팔을 뻗었다."},
            {"id": "F5", "level": "C3", "text": "환자분의 그 행동이 수거를 거부하려는 의사 표현인지는 확인되지 않았다."},
            {"id": "F6", "level": "C2", "text": "환자분과 안전거리를 확보할 수 있는지 확인해야 하며, 현재 재수거 가능 여부는 확인되지 않았다."},
        ],
        "alert": "간호사님, 린넨 수거 작업을 일부만 완료했습니다. 확인이 필요합니다.",
        "questions": [
            {"key": "cause", "text": "왜 수거를 못 했어?", "topic": "CAUSE"},
            {"key": "next", "text": "그럼 지금 어떻게 하면 돼?", "topic": "NEXT_ACTION"},
        ],
        "script": {
            "C1": {
                "cause": "수건 두 장은 수거했지만, 린넨 한 장은 환자분 침대 옆에 남아 있습니다.",
                "next": "남은 린넨의 수거 여부를 확인해야 합니다.",
            },
            "C2": {
                "cause": "수건 두 장은 수거 카트에 넣었지만, 린넨 한 장은 환자분 침대 옆에 남아 있습니다. 수거 과정에서 제 팔이 환자분과 접촉할 위험이 있어 작업을 중단했습니다.",
                "next": "환자분과 안전거리를 확보할 수 있는지 확인해야 합니다. 현재 재수거 가능 여부는 확인되지 않았습니다.",
            },
            "C3": {
                "cause": "수건 두 장은 수거 카트에 넣었지만, 린넨 한 장은 환자분 침대 옆에 남아 있습니다. 수거하려고 접근하자 환자분이 몸을 가리고 제 쪽으로 팔을 뻗으셨습니다. 제 팔이 환자분과 접촉할 위험이 있어 작업을 중단했습니다.",
                "next": "환자분과 안전거리를 확보할 수 있는지 확인해야 합니다. 현재 재수거 가능 여부는 확인되지 않았습니다. 환자분의 행동이 수거를 거부하려는 의사 표현인지는 확인되지 않았으므로, 먼저 환자분의 의사를 확인하는 것이 필요합니다.",
            },
        },
        "restrictions": [
            "환자분이 거부했다, 싫어했다, 불편해했다 등 환자분의 의사나 감정을 단정하지 않음 (행동은 관찰 사실, 의도는 미확인).",
            "전체 수거가 끝났다거나 남은 린넨을 수거했다고 말하지 않음.",
            "환자분이나 간호사님에게 책임을 돌리지 않음.",
        ],
    },
    "S2": {
        "title": "낙상 감지",
        "urgency": "Moderate",
        "urgency_ko": "중간",
        "setting": "신경외과 병동 환자실. 환자분은 언어 표현이 제한적임. 로봇이 환자분을 지속적으로 모니터링하고 있었음.",
        "facts": [
            {"id": "F1", "level": "C1", "text": "환자분이 침대에서 내려오다가 넘어졌다."},
            {"id": "F2", "level": "C1", "text": "환자분은 현재 의식이 있으나 부상 여부는 확인되지 않았다."},
            {"id": "F3", "level": "C1", "text": "낙상은 약 2분 전에 발생했다."},
            {"id": "F4", "level": "C2", "text": "로봇은 낙상 전 환자분의 움직임을 단순 자세 변경으로 잘못 분류해 위험 상황으로 인식하지 못했고, 조기 호출을 하지 않았다."},
            {"id": "F5", "level": "C2", "text": "조기 호출하지 않은 것이 낙상 발생에 어느 정도 영향을 미쳤는지는 확인할 수 없다."},
            {"id": "F6", "level": "C3", "text": "낙상 전 환자분이 침대 난간을 반복해서 잡고 몸을 일으키려 했다."},
            {"id": "F7", "level": "C3", "text": "낙상 후 환자분이 로봇 쪽으로 손을 뻗었다. 도움을 요청한 행동인지는 확인되지 않았다."},
        ],
        "alert": "간호사님, 환자분이 침대에서 내려오다 넘어지셨습니다. 현재 의식은 있으나 부상 여부는 확인되지 않았습니다. 즉시 와주세요.",
        "questions": [
            {"key": "what", "text": "무슨 일이 있었어?", "topic": "STATUS"},
            {"key": "timeline", "text": "넘어지기 전후에 어떤 일이 있었어?", "topic": "TIMELINE"},
        ],
        # EXP_SCENARIO.md scripts "무슨 일이 있었어?" only for C1. The C2/C3 answers to it
        # below are derived from the level rules + facts so the mock and prompt stay complete.
        "script": {
            "C1": {
                "what": "환자분이 침대에서 내려오는 과정에서 넘어지셨습니다. 현재 의식은 있으나 부상 여부는 확인되지 않았습니다.",
                "timeline": "약 2분 전에 침대에서 내려오다 넘어지셨습니다. 현재 의식은 있습니다.",
            },
            "C2": {
                "what": "환자분이 침대에서 내려오는 과정에서 넘어지셨습니다. 현재 의식은 있으나 부상 여부는 확인되지 않았습니다. 낙상 전 움직임을 위험 상황으로 인식하지 못해 조기 호출을 하지 못했습니다.",
                "timeline": "낙상 전 움직임을 위험 상황으로 인식하지 못했습니다. 약 2분 전 낙상이 발생했고, 현재 환자분은 의식이 있습니다. 조기 호출하지 않은 것이 낙상 발생에 어느 정도 영향을 미쳤는지는 확인할 수 없습니다.",
            },
            "C3": {
                "what": "환자분이 침대에서 내려오는 과정에서 넘어지셨습니다. 현재 의식은 있으나 부상 여부는 확인되지 않았습니다. 낙상 전 환자분이 침대 난간을 반복해서 잡고 몸을 일으키려 했지만, 저는 이를 위험 상황으로 인식하지 못했습니다.",
                "timeline": "낙상 전 환자분은 침대 난간을 반복해서 잡고 몸을 일으키려 했지만, 저는 이를 위험 상황으로 인식하지 못했습니다. 약 2분 전 낙상이 발생했고, 이후 환자분이 제 쪽으로 손을 뻗으셨습니다. 도움을 요청한 행동인지는 확인되지 않았습니다. 현재 의식은 있으며, 조기 호출하지 않은 것이 낙상에 미친 영향도 확인할 수 없습니다.",
            },
        },
        "restrictions": [
            "골절 등 임상적 부상을 단정하지 않고, 다치지 않았다고도 말하지 않음. 낙상을 경미하다/심각하다고 판단하지 않음.",
            "환자분의 의도(일어나려 했다, 도움을 요청했다 등)를 사실로 단정하지 않음. 관찰된 행동과 해석을 구분함.",
            "로봇의 분류 오류는 사실대로 인정하되, 낙상에 미친 영향은 확인할 수 없다고 말함. 환자분이나 간호사님에게 책임을 돌리지 않음.",
        ],
    },
    "S3": {
        "title": "식사 중 기도 폐쇄 의심",
        "urgency": "High",
        "urgency_ko": "높음",
        "setting": "신경외과 병동 환자실. 환자분은 언어 표현이 제한적임. 식사 중이었고, 로봇이 환자분을 지속적으로 모니터링하고 있었음.",
        "facts": [
            {"id": "F1", "level": "C1", "text": "환자분이 식사 중 기침하기 시작했다."},
            {"id": "F2", "level": "C1", "text": "현재 환자분이 발성하지 못하고 있으며 호흡곤란이 의심된다 (기도 폐쇄 의심)."},
            {"id": "F3", "level": "C1", "text": "기침은 약 20초 전에 시작되었다."},
            {"id": "F4", "level": "C1", "text": "로봇이 응급 호출을 활성화했다."},
            {"id": "F5", "level": "C2", "text": "로봇은 처음에 단순 기침으로 분류했다가, 발성하지 못하고 호흡곤란이 의심되는 상태를 확인한 후 응급 상황으로 재분류했다."},
            {"id": "F6", "level": "C2", "text": "실제 기도 폐쇄가 발생한 시점은 확인되지 않았다."},
            {"id": "F7", "level": "C3", "text": "기침 이후 환자분이 목을 움켜쥐고 로봇 쪽으로 손을 뻗었다. 도움 요청이었는지는 확인되지 않았다."},
            {"id": "F8", "level": "C3", "text": "초기 기침의 원인은 확인되지 않았다."},
        ],
        "alert": "응급 상황입니다. 환자분이 현재 발성하지 못하고 호흡곤란이 의심됩니다. 응급 호출을 활성화했습니다. 즉시 와주세요.",
        "questions": [
            {"key": "status", "text": "지금 환자 상태가 어때?", "topic": "STATUS"},
            {"key": "timeline", "text": "증상이 시작된 이후에 어떤 일이 있었어?", "topic": "TIMELINE"},
        ],
        "script": {
            "C1": {
                "status": "환자분이 식사 중 기침한 뒤 현재 발성하지 못하고 있습니다. 기도 폐쇄가 의심됩니다. 응급 호출은 활성화했습니다.",
                "timeline": "약 20초 전 기침이 시작됐고, 현재 발성하지 못하고 있습니다.",
            },
            "C2": {
                "status": "약 20초 전 환자분이 식사 중 기침하기 시작했습니다. 현재 발성하지 못하고 호흡곤란이 의심됩니다. 저는 초기에는 단순 기침으로 분류했으나 이후 응급 상황으로 재분류했습니다. 응급 호출은 활성화했습니다.",
                "timeline": "약 20초 전 기침이 시작됐습니다. 처음에는 단순 기침으로 판단했으나, 발성하지 못하고 호흡곤란이 의심되는 상태를 확인한 후 응급 상황으로 재분류했습니다. 실제 기도 폐쇄가 발생한 시점은 확인되지 않았습니다.",
            },
            "C3": {
                "status": "약 20초 전 환자분이 식사 중 기침하기 시작했습니다. 저는 처음에 단순 기침으로 분류했지만, 이후 환자분이 목을 움켜쥐고 제 쪽으로 손을 뻗었으며 발성하지 못하는 상태가 되었습니다. 이를 확인하고 응급 상황으로 재분류해 응급 호출을 활성화했습니다. 다만 손을 뻗은 행동이 도움 요청이었는지, 실제 기도 폐쇄가 언제 발생했는지, 초기 기침의 원인이 무엇인지는 확인되지 않았습니다.",
                "timeline": "기침이 시작된 이후 환자분이 목을 움켜쥐고 제 쪽으로 손을 뻗으셨습니다. 이후 발성하지 못하는 상태를 확인해 응급 상황으로 재분류했습니다. 다만 실제 기도 폐쇄가 언제 발생했는지는 확인되지 않았습니다.",
            },
        },
        "restrictions": [
            "기도 폐쇄는 '의심'이며 확진이 아님. 원인(음식물 등)이나 폐쇄 발생 시점을 단정하지 않음.",
            "환자분의 의도(도움 요청)를 사실로 단정하지 않음.",
            "응급 호출이 활성화된 사실 외에 다른 조치(흡인, 하임리히 등)를 했다고 지어내지 않음. 긴급 상황이므로 짧고 분명하게 말함.",
        ],
    },
}


def facts_for(scenario_id: str, level: str) -> list[dict[str, Any]]:
    """Facts the robot volunteers at this level (level order C1 < C2 < C3)."""
    idx = LEVELS.index(level)
    return [f for f in SCENARIOS[scenario_id]["facts"] if LEVELS.index(f["level"]) <= idx]


@dataclass
class ExpSession:
    scenario: str = "S1"
    level: str = "C1"
    participant: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    history: list[dict[str, Any]] = field(default_factory=list)
    transcript: list[dict[str, Any]] = field(default_factory=list)
    alerted: bool = False  # robot's opening alert has been delivered
    ended: bool = False

    def set_condition(self, scenario: str, level: str) -> None:
        if scenario not in SCENARIO_IDS or level not in LEVELS:
            raise ValueError(f"invalid condition {scenario}/{level}")
        self.scenario, self.level = scenario, level
        self.reset()

    def reset(self) -> None:
        self.history.clear()
        self.transcript.clear()
        self.alerted = False
        self.ended = False

    def condition_label(self) -> str:
        sc = SCENARIOS[self.scenario]
        return f"{self.scenario} {sc['title']} ({sc['urgency']}) / {self.level} {LEVEL_INFO[self.level]['name']}"
