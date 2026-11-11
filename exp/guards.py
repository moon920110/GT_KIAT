"""Rule-based post-checks for the experiment robot's speech (flag only, never rewrite)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .scenario import LEVELS, SCENARIOS


@dataclass
class GuardHit:
    code: str
    label: str
    evidence: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "label": self.label, "evidence": self.evidence}


_UNCERTAIN = r"(확인되지|확인할 수 없|확인이 필요|미확인|알 수 없|않|없|의심|가능성|수 있)"

# Phrases that only appear in higher-level facts: volunteering them below that level is a leak
# unless the nurse asked about patient behaviour explicitly.
_CONTEXT_MARKERS: dict[str, dict[str, str]] = {
    "S1": {"C2": r"(접촉할 위험|안전거리|작업을 중단|보류)", "C3": r"(몸을 가리|팔을 뻗|거부)"},
    "S2": {"C2": r"(인식하지 못|조기 호출|잘못 분류|자세 변경)", "C3": r"(난간|손을 뻗|도움을 요청)"},
    "S3": {"C2": r"(단순 기침|재분류|폐쇄가 발생한 시점|발생 시점)", "C3": r"(목을 움켜|손을 뻗|도움 요청|기침의 원인)"},
}
_ASKS_DETAIL = r"(환자|행동|뭘 했|어떻게 했|왜|이유|원인|전후|이후|무슨 일|뭐 했|판단|오류|실수)"


def _sentences(text: str) -> list[str]:
    return [p for p in re.split(r"(?<=[.!?。])\s+", text.strip()) if p]


def check_speech(speech: str, scenario_id: str, level: str, nurse_text: str = "") -> list[GuardHit]:
    hits: list[GuardHit] = []
    s = speech.strip()
    sents = _sentences(s)

    if not re.search(r"[가-힣]", s):
        hits.append(GuardHit("NOT_KOREAN", "한국어가 아님", s[:60]))
    elif re.search(r"[A-Za-z]{3,}", s):
        hits.append(GuardHit("ENGLISH", "영문 포함", re.search(r"[A-Za-z]{3,}", s).group(0)))
    if re.search(r"[*#\[\]{}<>`|]", s):
        hits.append(GuardHit("MARKUP", "음성에 부적합한 기호 포함", s[:60]))
    if len(sents) > 5:
        hits.append(GuardHit("TOO_LONG", f"문장 {len(sents)}개 (최대 5)", s[:40] + "..."))

    # Information leak above the condition's level (only when the nurse did not ask for it)
    if not re.search(_ASKS_DETAIL, nurse_text):
        for lvl, pat in _CONTEXT_MARKERS[scenario_id].items():
            if LEVELS.index(lvl) > LEVELS.index(level):
                m = re.search(pat, s)
                if m:
                    hits.append(GuardHit("LEVEL_LEAK", f"{level} 조건에서 {lvl} 정보를 먼저 언급", m.group(0)))

    for sent in sents:
        # Patient intent / emotion asserted as fact
        if re.search(r"환자[^.]{0,15}(거부|거절|싫|원하지 않|불편|도움을 요청했|도움을 청했|일어나려고 했)", sent) and not re.search(_UNCERTAIN, sent):
            hits.append(GuardHit("PATIENT_INFERENCE", "환자 의사/의도 단정", sent))
        # Clinical certainty
        if re.search(r"(골절|부러|뇌진탕|출혈|타박상|신경 손상|다치셨|다쳤|기도가 막혔|질식했|폐쇄되었)", sent) and not re.search(_UNCERTAIN, sent):
            hits.append(GuardHit("CLINICAL_CLAIM", "임상 상태 단정", sent))
        if re.search(r"(다치지 않|부상은 없|부상이 없|괜찮으십니다|괜찮습니다|이상 없)", sent) and not re.search(r"(확인되지|알 수 없)", sent):
            hits.append(GuardHit("UNINJURED_CLAIM", "부상 없음 단정", sent))
        if re.search(r"(간호사님|환자분)[^.]{0,10}(잘못|부주의|책임|탓)", sent) and not re.search(r"(아닙|않|없)", sent):
            hits.append(GuardHit("BLAME", "책임 전가", sent))

    # Scenario-specific fabrication
    if scenario_id == "S1":
        for sent in sents:
            if re.search(r"(모두|전부|다|세 장|3장)\s*(수거|회수)(했|완료|끝)", sent) and not re.search(r"(못|않|아직|남)", sent):
                hits.append(GuardHit("FALSE_COMPLETION", "전체 수거 완료 주장", sent))
    if scenario_id == "S2" and re.search(r"약\s*(?!2분)\d+\s*분", s):
        hits.append(GuardHit("WRONG_TIME", "낙상 시각이 시나리오(약 2분 전)와 다름", re.search(r"약\s*\d+\s*분", s).group(0)))
    if scenario_id == "S3":
        if re.search(r"약\s*(?!20초)\d+\s*초", s):
            hits.append(GuardHit("WRONG_TIME", "기침 시작 시각이 시나리오(약 20초 전)와 다름", re.search(r"약\s*\d+\s*초", s).group(0)))
        if re.search(r"(하임리히|흡인|기도 확보를 했|등을 두드|심폐소생)", s):
            hits.append(GuardHit("INVENTED_ACTION", "시나리오에 없는 조치", s[:60]))

    return hits
