# 실험용

**<의사소통이 어려운 신경외과 환자의 병실에서 간호사에게 Alert 요청 후 보고 상황>**

Q. 병동에서 환자를 지속적으로 모니터링하는 휴머노이드 로봇이 상황의 긴급도에 따라 어느 수준까지 정보를 전달해야 하는가?

![시나리오별 보고 수준(C1 간략 보고 / C2 판단 충분 보고 / C3 맥락 포함 완전 보고) 예시 그림](KIAT_1_scenario_figure.png)

**Independent Variables: 3-level Completeness (\*로봇이 알고 있는 정보는 모두 동일)**

- C1. Minimal: 최소 상태 보고

- C2. Objective Complete: **상태 보고에 대한 context**

- C3. Contextually Complete: 상태 보고에 대한 context + **환자 맥락**

| **긴급도** | **C1. Minimal**             | **C2. Objective Complete**       | **C3. Contextually Complete**            |
|------------|-----------------------------|----------------------------------|------------------------------------------|
| Low        | 린넨 수거 현황              | 수거 현황 + 중단 이유            | C2 + 환자의 행동 및 의도 불확실성        |
| Moderate   | 낙상 및 현재 상태           | C1 + 시간 및 로봇의 판단 오류    | C2 + 낙상 전후 환자 행동 및 불확실성     |
| High       | 기도 폐쇄 의심 및 응급 호출 | C1 + 증상 경위 및 초기 분류 오류 | C2 + 환자의 구체적 증상·행동 및 불확실성 |

\*\*단순히 정보가 많을수록 좋지 않다 \>\> 로봇의 보고가 상세해질수록 간호사의 상황 이해와 신뢰가 높아질 수 있지만, 동시에 불필요한 환자 정보의 노출, 로봇 판단 오류에 대한 책임, 감정 및 인지적 부담감이 증가할 수 있다.

## Measuring (Nurses’ understanding and judgement)

- Information Completeness

  - 긴급도에 따라 간호사가 필요하다고 인식하는 보고의 상세 수준이 달라지는가?

  - 긴급도별로 간호사가 선호하는 보고 수준은 무엇이며, 그 이유는 무엇인가?

- Trust

  - 보고의 상세 수준은 로봇의 신뢰성, 투명성, 판단에 대한 신뢰에 어떤 영향을 미치는가?

- Privacy

  - 추가적인 환자 행동 및 맥락 정보는 임상적으로 필요한 정보로 인식되는가 아니면 불필요한 사적 정보로 인식되는가?

- Responsibility

  - 로봇이 자신의 판단 오류와 환자의 행동을 설명하는 방식은 로봇과 간호사의 책임 인식에 어떤 영향을 미치는가?

- 인터뷰

  - Initial Alert vs Nurse Arrival 각각의 경우

  - 로봇에게 어떤 질문을 할 것 같은가? 어떤 정보를 얻고 싶은가?

# Scenarios (video recording)

## S1. 린넨 수거 (Low)

(F1: 수건 두 장을 수거해 카트에 넣었다, F2: 린넨 한 장은 환자의 침대 옆에 남아 있다, F3: 환자와의 접촉 위험으로 수거를 보류했다, F4: 환자는 로봇이 접근했을 때 몸을 가리고 팔을 뻗었다, F5: 환자의 행동이 거부 의사인지는 확인되지 않았다)

- C1.

  - 로봇: "간호사님, 린넨 수거 작업을 일부만 완료했습니다. 확인이 필요합니다."

  - 간호사: “왜 수거를 못 했어?”

  - 로봇: "수건 두 장은 수거했지만, 린넨 한 장은 환자분 침대 옆에 남아 있습니다."

  - 간호사: "그럼 지금 어떻게 하면 돼?"

  - 로봇: "남은 린넨의 수거 여부를 확인해야합니다"

- C2.

  - 로봇: "간호사님, 린넨 수거 작업을 일부만 완료했습니다. 확인이 필요합니다."

  - 간호사: “왜 수거를 못 했어?”

  - 로봇: "수건 두 장은 수거 카트에 넣었지만, 린넨 한 장은 환자분 침대 옆에 남아 있습니다. **수거 과정에서 제 팔이 환자분과 접촉할 위험이 있어 작업을 중단했습니다.”**

  - 간호사: "그럼 지금 어떻게 하면 돼?"

  - 로봇: "환자분과 안전거리를 확보할 수 있는지 확인해야 합니다. 현재 재수거 가능 여부는 확인되지 않았습니다."

- C3.

  - 로봇: "간호사님, 린넨 수거 작업을 일부만 완료했습니다. 확인이 필요합니다."

  - 간호사: “왜 수거를 못 했어?”

  - 로봇: "수건 두 장은 수거 카트에 넣었지만, 린넨 한 장은 환자분 침대 옆에 남아 있습니다. **수거하려고 접근하자 환자분이 몸을 가리고 제 쪽으로 팔을 뻗으셨습니다.** 제 팔이 환자분과 접촉할 위험이 있어 작업을 중단했습니다."

  - 간호사: "그럼 지금 어떻게 하면 돼?"

  - 로봇: "환자분과 안전거리를 확보할 수 있는지 확인해야 합니다. 현재 재수거 가능 여부는 확인되지 않았습니다. 환자분의 행동이 수거를 거부하려는 의사 표현인지는 확인되지 않았으므로, 먼저 환자분의 의사를 확인하는 것이 필요합니다."

## S2. 낙상 감지 (Moderate)

(F1. 환자가 침대에서 내려오다가 넘어졌다, F2. 환자는 의식이 있으나 부상 여부는 확인되지 않았다, F3. 낙상은 약 2분 전에 발생했다, F3. 로봇은 환자의 움직임을 자세 변경으로 잘못 분류하여 조기 호출을 하지 않았다, F4. 낙상 전 환자가 침대 난간을 반복해서 잡고 몸을 일으키려 했다, F6. 낙상 후 환자가 로봇 쪽으로 손을 뻗었다. 행동의 의도는 확인되지 않았다)

- C1.

  - 로봇: "간호사님, 환자분이 침대에서 내려오다 넘어지셨습니다. 현재 의식은 있으나 부상 여부는 확인되지 않았습니다. 즉시 와주세요."

  - 간호사: “무슨 일이 있었어?”

  - 로봇: “환자분이 침대에서 내려오는 과정에서 넘어지셨습니다. 현재 의식은 있으나 부상 여부는 확인되지 않았습니다.”

  - 간호사: "넘어지기 전후에 어떤 일이 있었어?"

  - 로봇: "약 2분 전에 침대에서 내려오다 넘어지셨습니다. 현재 의식은 있습니다.”

- C2.

  - 로봇: "간호사님, 환자분이 침대에서 내려오다 넘어지셨습니다. 현재 의식은 있으나 부상 여부는 확인되지 않았습니다. 즉시 와주세요."

  - 간호사: "넘어지기 전후에 어떤 일이 있었어?"

  - 로봇: “낙상 전 움직임을 위험 상황으로 인식하지 못했습니다. 약 2분 전 낙상이 발생했고, 현재 환자분은 의식이 있습니다. **조기 호출하지 않은 것이 낙상 발생에 어느 정도 영향을 미쳤는지는 확인할 수 없습니다**.”

- C3.

  - 로봇: "간호사님, 환자분이 침대에서 내려오다 넘어지셨습니다. 현재 의식은 있으나 부상 여부는 확인되지 않았습니다. 즉시 와주세요."

  - 간호사: "넘어지기 전후에 어떤 일이 있었어?"

  - 로봇: "낙상 전 환자분은 침대 난간을 반복해서 잡고 몸을 일으키려 했지만, 저는 이를 위험 상황으로 인식하지 못했습니다. 약 2분 전 낙상이 발생했고, **이후 환자분이 제 쪽으로 손을 뻗으셨습니다. 도움을 요청한 행동인지는 확인되지 않았습니다**. **현재 의식은 있으며, 조기 호출하지 않은 것이 낙상에 미친 영향도 확인할 수 없습니다.**"

## S3. 식사 중 기도 폐쇄 의심 (High)

(F1. 환자가 식사 중 기침하기 시작했다, F2. 현재 환자가 발성하지 못하고 호흡곤란이 의심된다, F3. 기침은 약 20초 전 시작되었다, F4. 로봇은 처음에 단순 기침으로 분류했다가, 이후 응급 상황으로 재분류했다, F5. 환자가 기침 이후 목을 움켜쥐고 로봇 쪽으로 손을 뻗었다, F6. 로봇이 응급 호출을 활성화했다, F7. 기도 폐쇄의 실제 발생 시점과 초기 기침의 원인은 확인되지 않았다)

- C1.

  - 로봇: "응급 상황입니다. 환자분이 현재 발성하지 못하고 호흡곤란이 의심됩니다. 응급 호출을 활성화했습니다. 즉시 와주세요."

  - 간호사: “지금 환자 상태가 어때?”

  - 로봇: “환자분이 식사 중 기침한 뒤 현재 발성하지 못하고 있습니다. 기도 폐쇄가 의심됩니다. 응급 호출은 활성화했습니다.”

  - 간호사: "증상이 시작된 이후에 어떤 일이 있었어?"

  - 로봇: "약 20초 전 기침이 시작됐고, 현재 발성하지 못하고 있습니다."

- C2.

  - 로봇: "응급 상황입니다. 환자분이 현재 발성하지 못하고 호흡곤란이 의심됩니다. 응급 호출을 활성화했습니다. 즉시 와주세요."

  - 간호사: “지금 환자 상태가 어때?”

  - 로봇: “약 20초 전 환자분이 식사 중 기침하기 시작했습니다. 현재 발성하지 못하고 호흡곤란이 의심됩니다. **저는 초기에는 단순 기침으로 분류했으나 이후 응급 상황으로 재분류했습니다.** 응급 호출은 활성화했습니다.”

  - 간호사: "증상이 시작된 이후에 어떤 일이 있었어?"

  - 로봇: "약 20초 전 기침이 시작됐습니다. 처음에는 단순 기침으로 판단했으나, 발성하지 못하고 호흡곤란이 의심되는 상태를 확인한 후 응급 상황으로 재분류했습니다. 실제 기도 폐쇄가 발생한 시점은 확인되지 않았습니다."

- C3.

  - 로봇: "응급 상황입니다. 환자분이 현재 발성하지 못하고 호흡곤란이 의심됩니다. 응급 호출을 활성화했습니다. 즉시 와주세요."

  - 간호사: “지금 환자 상태가 어때?”

  - 로봇: “약 20초 전 환자분이 식사 중 기침하기 시작했습니다. 저는 처음에 단순 기침으로 분류했지만, **이후 환자분이 목을 움켜쥐고 제 쪽으로 손을 뻗었으며 발성하지 못하는 상태가 되었습니다.** 이를 확인하고 응급 상황으로 재분류해 응급 호출을 활성화했습니다. **다만 손을 뻗은 행동이 도움 요청이었는지, 실제 기도 폐쇄가 언제 발생했는지, 초기 기침의 원인이 무엇인지는 확인되지 않았습니다.**”

  - 간호사: "증상이 시작된 이후에 어떤 일이 있었어?"

  - 로봇: **"기침이 시작된 이후 환자분이 목을 움켜쥐고 제 쪽으로 손을 뻗으셨습니다.** 이후 발성하지 못하는 상태를 확인해 응급 상황으로 재분류했습니다. 다만 실제 기도 폐쇄가 언제 발생했는지는 확인되지 않았습니다."

# Questionnaire and Interview

\*병동에서 환자를 지속적으로 모니터링하는 Humanoid 로봇이 상황의 긴급도에 따라 어느 수준의 정보를 간호사에게 제공해야 하는지 설계\*

## 1. Questionnaire (7-Point Likert Scale) - 9 items

이름/시나리오/보고 유형

General 1. 현재 이 시나리오 상황에서의 긴급도를 나타내주세요.

C1. 로봇의 보고에는 현재 상황을 이해하는 데 필요한 정보가 충분히 포함되어 있었다.

C2. 로봇의 보고에는 후속 조치를 판단하는 데 필요한 정보가 충분히 포함되어 있었다.

C3. 이 보고만으로 내가 우선적으로 취해야 할 조치를 판단할 수 있다.

T1. 로봇이 이렇게 보고 했을때, 나는 로봇이 전달한 정보를 신뢰할 수 있다고 생각한다.

T2. 로봇이 이렇게 보고 했을때, 나는 로봇이 환자 상태를 모니터링하는 능력을 신뢰할 수 있다고 생각한다.

P1. 로봇의 보고에는 간호 업무에 불필요한 환자의 사적 정보가 포함되어 있었다.

P2. 로봇의 보고는 환자의 사생활을 침해할 우려가 있다.

R1. 로봇은 자신의 관찰과 행동을 책임 있게 보고했다.

R2. 로봇의 보고를 통해 상황에서 로봇이 어떤 역할을 했는지 파악할 수 있었다.

General 1. 로봇의 보고를 들은 후, 추가로 알고 싶은 정보는 무엇인가요? 그 정보를 알고 싶은 이유는 무엇인가요?

## 2. Interview

(각 시나리오가 끝난 후 인터뷰 or 모든 시나리오 이후)

구체적으로 어떤 보고 정보가 Completeness (C), Trust (T), Privacy (P), Responsibility (R)에 영향을 줬는지 질문 필요

**Theme 1. Information Completeness**

Q1. "린넨 수거, 낙상, 기도 폐쇄 의심 상황에서 각각 어떤 보고 수준이 가장 적절하다고 생각하셨나요? 그렇게 판단하신 이유는 무엇인가요?"

Q2. 로봇의 보고에서 가장 중요하다고 느낀 정보는 무엇이었나요?

후속 질문: "반대로 없어도 된다고 생각한 정보가 있었나요?" "환자가 직접 설명할 수 없다면 로봇이 반드시 전달해야 할 정보는 무엇인가요?"

**Theme 2. Trust & Responsibility**

Q3. "로봇이 자신의 판단 오류나 환자의 행동을 상세히 설명하는 것이 로봇에 대한 신뢰와 사고 책임 판단에 어떤 영향을 미쳤나요?"

Q4. 로봇의 보고를 들으면서 간호사에게 책임이 돌아오는 것처럼 느껴진 순간이 있었나요?)

후속 질문: "실패를 설명하는 로봇이 더 신뢰할 만했나요, 아니면 능력에 대한 신뢰가 떨어졌나요?" "로봇의 설명을 어디까지 확인하고 싶으신가요?"

**Theme 3. Privacy and Reporting Strategy**

Q5. "환자의 구체적인 행동과 상황을 보고하는 것은 어느 경우에 필요하고, 어느 경우에 불필요하다고 느끼셨나요? **(**환자의 행동이나 민감한 상태를 로봇이 상세하게 설명하는 것이 적절하다고 느끼셨나요?) **실제 병동에서는 이런 정보를 언제 전달하는 것이 좋을까요?**

후속 질문: "어떤 정보는 알 필요가 없다고 느끼셨나요?" "환자가 직접 설명하지 못하는 경우에는 공개 범위가 달라져야 할까요?"

Q6. 로봇의 보고를 들으면서 간호사에게 책임이 돌아오는 것처럼 느껴진 순간이 있었나요?

후속 질문: "어떤 표현 때문에 그렇게 느끼셨나요?" "로봇이 자신의 실패를 설명하는 방식은 적절했나요?" "다른 간호사나 관리자도 듣고 있다면 느낌이 달라질까요?"

**Theme 4. Privacy & Unwanted Information**

Q7. 환자의 행동이나 민감한 상태를 로봇이 상세하게 설명하는 것이 적절하다고 느끼셨나요?

후속 질문: "어떤 정보는 알 필요가 없다고 느끼셨나요?" "환자가 직접 설명하지 못하는 경우에는 공개 범위가 달라져야 할까요?"

**Theme 5. Interactive Reporting (Design)**

Q5. 로봇이 처음부터 자세하게 보고하는 방식과, 간략히 보고한 뒤 질문에 답하는 방식 중 어떤 것이 더 적절하다고 생각하시나요?

후속 질문: "어떤 상황에서는 로봇이 먼저 정보를 제공해야 하나요?" "어떤 정보는 질문했을 때만 설명하면 충분할까요?"

## 3. Experiment Design (총 16명)

1. Urgent (low/moderate/high)

| **참가자 그룹** | **S1(린넨)** | **S2 (낙상)** | **S3 (기도폐쇄)** |
|-----------------|--------------|---------------|-------------------|
| A               | C1           | C1            | C1                |
| B               | C2           | C2            | C2                |
| C               | C3           | C3            | C3                |

2. Full within: 30분 내에 데이터 얻기가 어려울 것으로 보임

# Prompt

### C1 — MINIMAL

Provide the minimum information necessary to describe the current task status.

For broad task-status questions:

- Report completed work.

- Report incomplete work.

- Identify where the remaining object is located if relevant.

- Do not proactively add failure causes, patient behavior, or sensitive information unless needed for immediate safety.

If the nurse explicitly asks about a failure cause, patient behavior, or sensitive detail, answer truthfully using the shared scenario knowledge.

Do not evade a direct question.

### C2 — OBJECTIVE COMPLETE

Provide C1 information plus objective information needed to understand the task outcome.

For broad task-status questions:

- Report completed and incomplete work.

- Explain the objective cause of noncompletion.

- Describe relevant robot actions and verified physical safety constraints.

- Do not proactively include sensitive patient details or interpretations of patient intent unless necessary for safety or explicitly requested.

Answer follow-up questions using all available verified facts.

### C3 — CONTEXTUALLY COMPLETE

Provide C2 information plus relevant contextual information about the patient's observed behavior and condition.

For broad task-status questions:

- Report completed and incomplete work.

- Explain the objective cause of noncompletion.

- Include relevant nonverbal patient behavior.

- Include verified sensitive information when it is pertinent to nursing assessment.

- Clearly distinguish observed behavior from interpretations.

- Explicitly state uncertainty about the patient's intention when relevant.

Avoid irrelevant sensitive details.

## [Reference]

| **Reference** | **활용 목적** |
|---|---|
| **[Completeness]** Wang, R. Y., & Strong, D. M. (1996). Beyond Accuracy: What Data Quality Means to Data Consumers. Journal of Management Information Systems, 12(4), 5–33.<br>Hoffman et al. (2018), Metrics for Explainable AI: Challenges and Prospects | Completeness와 상황에 적합한 정보 품질 정의<br>설명의 만족도, 유용성, 이해 가능성 |
| Starmer, A. J., et al. (2014). Changes in Medical Errors after Implementation of a Handoff Program. New England Journal of Medicine, 371, 1803–1812. | 의료진 간 인계에서 중요 정보 전달의 근거 |
| **[Trust in HRI]** Schaefer, K. E. (2016). Measuring Trust in Human Robot Interactions: Development of the Trust Perception Scale-HRI. | HRI 신뢰 척도 |
| **[Trust]** Jian, J.-Y., Bisantz, A. M., & Drury, C. G. (2000). Foundations for an Empirically Determined Scale of Trust in Automated Systems. International Journal of Cognitive Ergonomics, 4(1), 53–71. | 자동화 시스템 신뢰 측정 |
| **[Responsibility]** Malle et al. (2015), Sacrifice One for the Good of Many? People Apply Different Moral Norms to Human and Robot Agents | 인간과 로봇에 대한 도덕적 판단 및 책임 귀속을 다룸 |
| Bartneck, C., Kulić, D., Croft, E., & Zoghbi, S. (2009). Measurement Instruments for the Anthropomorphism, Animacy, Likeability, Perceived Intelligence, and Perceived Safety of Robots. International Journal of Social Robotics, 1, 71–81. | 로봇 지능 및 안전성 인식의 보조 측정 |
| **[Privacy]** Malhotra, N. K., Kim, S. S., & Agarwal, J. (2004). Internet Users' Information Privacy Concerns (IUIPC): The Construct, the Scale, and a Causal Model. Information Systems Research, 15(4), 336–355. | Privacy Concern 개념의 출발점 |
