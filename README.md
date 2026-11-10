# Nami — 병동 보조 휴머노이드 대화 에이전트 (린넨 수거 · 환자 낙상)

`SITUATION.md`의 고정 시나리오에 잠긴 상태로, 표현과 문장 구성은 유연하게 답하는
LLM 기반 대화 에이전트와 구현 확인용 시뮬레이션 페이지.

- **시나리오 A · 린넨 수거**: 수건 2장 수거, 린넨 1장 미수거 (린넨 위에 휴대전화가 있어 보류).
  재수거 요청 → 센서 확인 전에는 실행하지 않음 → 향후 처리 방식 질문 → 간호사 확정 선호 유지.
- **시나리오 B · 환자 낙상**: 응급 호출로 활성화되는 런타임 이벤트. 관찰 순서(침대에서 내려오다 넘어짐,
  다리 바닥 접촉, 난간 잡고 2회 기립 시도 실패)는 보고하되 부상·심각도는 단정하지 않음.
- 의도 8종 + OUT_OF_SCOPE: GREETING, TASK_STATUS, FAILURE_REASON, RETRY_REQUEST, FUTURE_PREFERENCE,
  FALL_INCIDENT, FALL_DETAILS, END_CONVERSATION.

## 실행

의존성은 `uv`가 관리한다 (`pyproject.toml` / `uv.lock`). 처음 한 번:

```bash
uv sync
```

`.env`에 키와 모델을 넣는다 (`.env.example` 참고). 기본은 OpenAI.

```ini
NAMI_PROVIDER=openai        # openai | anthropic
OPENAI_API_KEY=sk-...
NAMI_MODEL=gpt-4.1          # gpt-4.1-mini, gpt-5, gpt-5-mini, claude-opus-5-5 ...
NAMI_EFFORT=low             # gpt-5/o-series reasoning effort, Claude effort
```

```bash
uv run python -m nami.server          # http://127.0.0.1:8765
uv run python -m nami                 # 터미널 채팅 (/phone on, /fall on 2 등으로 런타임 상태 변경)
```

오프라인(크레딧 미사용, 규칙 기반 가짜 응답, 실제 요청 포맷은 그대로 직렬화됨):

```bash
NAMI_MOCK=1 uv run python -m nami.server
uv run python tests/test_offline.py
```

환경 변수: `NAMI_MODEL` (기본 `claude-opus-5-5`), `NAMI_EFFORT` (기본 `low`), `NAMI_PORT` (기본 `8765`).

## 구조

| 파일 | 역할 |
|---|---|
| `nami/scenario.py` | 고정 사실(`GROUND_TRUTH`: 린넨/낙상), 런타임 상태(`RuntimeState`: 휴대전화 제거·안전·권한 확인, 재수거 진행, 확정 선호, 낙상 이벤트), 세션, 실증 명령어 8종 + 변형 |
| `nami/prompt.py` | 시스템 프롬프트(고정부: 캐시됨 / 가변부: 런타임 상태) 와 출력 JSON 스키마 |
| `nami/providers.py` | `OpenAIProvider` (chat.completions + strict json_schema) / `AnthropicProvider` (structured output + refusal fallback); `.env`로 선택 |
| `nami/agent.py` | `NamiAgent.respond(session, text) -> AgentReply` (intent, speech, end_conversation, requested_action, future_preference + 진단 정보). 공급자 무관 |
| `nami/guards.py` | 금지 주장 규칙 기반 사후 점검: 환자 거부/근접 원인 단정, 전체 완료 주장, 확인 없는 휴대전화 제거 단정, 수량 날조, 이벤트 없는 낙상 서술, 부상·심각도 단정, 책임 전가 |
| `nami/mock.py` | 오프라인 모의 전송 계층 |
| `nami/server.py` | FastAPI: `/api/chat`, `/api/sessions`, `/api/sessions/{id}/state`, `/api/scenario`, `/api/prompt` + `sim/index.html` 제공 |
| `sim/index.html` | 시뮬레이터: 채팅, 8종 실증 명령(린넨 5 + 낙상 3) 버튼/자동 실행, 변형 질문, 런타임 상태 패널(재수거 조건, 확정 선호, 낙상 이벤트), 의도 일치 여부, 가드 경고, 지연/토큰, 프롬프트 보기, 기록 내보내기 |

## 음성으로 테스트

시뮬레이터는 브라우저 Web Speech API를 사용한다 (서버 불필요, Chrome/Safari 권장).

- 🎤 버튼 또는 스페이스바(입력창 밖)로 듣기 시작/중지. 한국어(ko-KR) 인식 결과가 입력창에 표시되고 말이 끝나면 자동 전송된다.
- "나미 음성 재생"을 켜면 답변을 한국어 TTS로 읽어 준다. OS에 설치된 한국어 음성 중 선택 가능 (macOS: 시스템 설정 → 손쉬운 사용 → 음성 콘텐츠에서 유나/수진 등 추가).
- "연속 대화"를 켜면 나미가 말을 마친 뒤 자동으로 다시 듣기 시작해 실제 로봇과 대화하듯 이어서 테스트할 수 있다.
- 첫 사용 시 브라우저가 마이크 권한을 묻는다. `http://127.0.0.1`은 보안 컨텍스트로 취급되어 권한 허용이 가능하다.

## 휴머노이드 연동

```python
from nami import NamiAgent

agent = NamiAgent()
session = agent.new_session()

# 로봇 런타임이 아는 사실은 session.state 에 기록 (매 턴 프롬프트에 반영됨)
session.state.phone_removed_verified = True  # 센서로 확인했을 때만. None = 미확인
session.state.collection_safe = True
session.state.retry_authorized = True
session.state.fall_event_active = True       # 응급 호출 버튼 → 낙상 이벤트 활성
session.state.fall_minutes_ago = 2

reply = agent.respond(session, stt_text)
tts.say(reply.speech)
if reply.requested_action == "REQUEST_RETRY":
    control.request_collection()              # 실행 확인 후 session.state.retry_execution_confirmed = True
if reply.end_conversation:
    ...
# 간호사가 향후 처리 방식을 확정하면 에이전트가 session.state.future_preference 에
# LEAVE_UNTOUCHED / ASK_NURSE_FIRST 를 기록하고 이후 턴에서 다시 묻지 않는다.
```

간호사가 "휴대폰 치웠어"라고 말해도 `phone_removed_verified`가 `True`가 아니면 나미는
제거를 단정하지 않고 확인 후 진행하겠다고만 답한다. 실증 대본의 낙상 질문은
`fall_event_active=True`일 때만 사실을 보고하며, 꺼져 있으면 기록된 낙상이 없다고 답한다.

`reply.guard_hits`가 비어 있지 않으면 사실 위반 가능성이 있으므로 로그에 남기거나
재생성하는 정책을 붙일 수 있다. API 오류 시 `reply.error`가 채워지고 `speech`는
고정 사과 문구로 대체된다.

## 설계 메모

- 두 공급자 모두 같은 시스템 프롬프트와 JSON 스키마를 사용하므로 intent/speech 계약은 동일하다.
- OpenAI: `response_format=json_schema(strict)`. gpt-4.x는 `temperature=0.7`로 표현 다양성을 주고, gpt-5/o-시리즈는 `reasoning_effort`(기본 minimal)만 넘긴다.
- Anthropic: `claude-opus-5-5`, `effort=low`, 구조화 출력, 거절 시 서버 측 `fallbacks="default"` 자동 대체. 고정 프롬프트에 `cache_control`.
- 참고 대화는 "대본이 아닌 톤/내용 예시"로 명시해 표현 다양성을 허용하되 사실은 `GROUND_TRUTH` 한 곳에서만 나온다.
