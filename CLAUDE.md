# 따뜻한하루 — CLAUDE.md

## 프로젝트 개요

- **프로젝트명:** 따뜻한하루 (WarmDay)
- **설명:** 웹 채팅으로 독거노인의 외로움을 해소하고 건강·안전을 지키는 AI 케어 서비스
- **작성자:** 고명진 (학번 3401)
- **노션 계획서:** [프로젝트 계획서](https://www.notion.so/3286dcbf4e57805586d0fe27bdf4dd2a)

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | Next.js 14.2.35, React 18, TypeScript, Tailwind CSS |
| PWA | @ducanh2912/next-pwa 10.2.9 |
| Backend | Python, FastAPI, APScheduler |
| AI | GPT-4o-mini, LangChain, Sentiment Analysis (KR-FinBert-SC) |
| 채팅 | REST API (웹 채팅) + 카카오톡 챗봇 스킬 서버 (Twilio 제거됨) |
| Database | Firebase Firestore |
| 배포 | Vercel (Frontend), Uvicorn (Backend) |

---

## 디렉토리 구조

```
warmpal/
├── CLAUDE.md
├── backend/
│   ├── main.py                  # FastAPI 앱 + APScheduler 스케줄러
│   ├── requirements.txt
│   ├── .env.example
│   ├── models/
│   │   └── schemas.py           # Pydantic 스키마
│   ├── routers/
│   │   ├── chat.py              # 웹 채팅 수신 → AI 응답 반환
│   │   ├── kakao.py             # 카카오톡 챗봇 스킬 서버 웹훅
│   │   ├── users.py             # 가족/어르신 회원가입·로그인·CRUD, JWT 인증
│   │   ├── dashboard.py         # 감정 트렌드·건강 현황·알림 API
│   │   └── health.py            # 건강 리마인더 스케줄러 및 수동 발송 API
│   └── services/
│       ├── ai_service.py        # GPT-4o-mini + LangChain 대화 체인 + 페르소나
│       ├── sentiment.py         # 감정 분석 (KR-FinBert + 키워드 fallback)
│       └── firebase.py          # Firebase Firestore CRUD helpers
└── frontend/
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.js
    ├── public/
    │   ├── manifest.json
    │   └── icons/               # PWA 아이콘 (72~512px)
    └── src/
        ├── lib/
        │   └── api.ts
        ├── app/
        │   ├── layout.tsx
        │   ├── page.tsx         # 로그인/회원가입
        │   ├── chat/
        │   │   └── page.tsx     # 어르신용 채팅 페이지 (/chat?id=<elderly_id>)
        │   └── dashboard/
        │       └── page.tsx     # 가족 대시보드
        └── components/
            ├── EmotionChart.tsx
            ├── HealthTrendChart.tsx
            ├── ConversationLog.tsx
            ├── RegisterElderlyModal.tsx
            └── EditElderlyModal.tsx   # 어르신 설정 수정 모달 (신규)
```

---

## 실행 방법

### 백엔드

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
.\venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8001
```

### 프론트엔드

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

### 필수 환경 변수 (backend/.env)

```
OPENAI_API_KEY=sk-...
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
FIREBASE_PROJECT_ID=your-project-id
APP_SECRET_KEY=랜덤_문자열
APP_BASE_URL=http://localhost:8001
FRONTEND_URL=http://localhost:3000

DAILY_MESSAGE_HOUR=9
DAILY_MESSAGE_MINUTE=0
REMINDER_CHECK_INTERVAL_MINUTES=30

KAKAO_BOT_SECRET=         # (선택) 오픈빌더 스킬 헤더 X-Bot-Secret 검증용, 비우면 생략
```

### frontend/.env.local

```
NEXT_PUBLIC_API_URL=http://localhost:8001
```

---

## 개발 진행 현황

| 주차 | 내용 | 상태 |
|------|------|------|
| 사전 | 프로젝트 계획서 작성 | ✅ 완료 |
| 1주차 | AI 프롬프트 설계, Twilio 연동 | ✅ 완료 |
| 2주차 | FastAPI 백엔드 + Next.js PWA | ✅ 완료 |
| 3주차 | 가족 대시보드 + 감정 분석 | ✅ 완료 |
| 4주차 | SMS → 웹 채팅 전환, Firebase 연동 | ✅ 완료 |
| 5주차~ | AI 페르소나, 채팅 UX 개선, 퀴즈·오락 기능 | ✅ 완료 |
| 6주차~ | 카카오톡 챗봇 연동 (스킬 서버 + 자동연결) | 🔄 진행 중 (채널 라우팅 막힘) |

---

## 카카오톡 봇 연동 — 진행 상황 및 TODO

> 최종 업데이트: 2026-06-09

### ✅ 완료된 것 (서버/코드 측 전부 정상)
- 레거시 SMS 코드 제거 (`routers/sms.py`, `services/sms_service.py` 삭제 — Twilio 의존 죽은 코드)
- 카카오 i 오픈빌더 **스킬 서버** 구현 (`routers/kakao.py`, `POST /kakao/skill`)
  - 기존 `process_inbound_message`(감정분석·대화저장·퀴즈·알림) 재사용
  - `퀴즈`/`노래 추천` 빠른 명령 + quickReplies 버튼
- **자동연결** 구현: 어르신별 6자리 `kakao_connect_code` → 발화/파라미터에서 코드 추출해 `kakao_user_id` 매핑 (전화번호 인증은 보조 경로)
- 대시보드 '💬 카카오톡으로 연결' 카드 + `GET /users/elderly/{id}/kakao-link` (연결번호·채널 링크·QR·안내문구 복사)
- `.env` 설정: `KAKAO_CHANNEL_PUBLIC_ID=_VwXnX` (채널 홈 URL `http://pf.kakao.com/_VwXnX`)
- 로컬 공개 노출: **ngrok (JP 지역)** 으로 https 터널 확보 → 카카오가 스킬 서버 호출 확인
- **검증 완료**: 오픈빌더 *봇 테스트*에서 우리 서버가 200 + 정상 JSON 응답
  (안내 → 연결번호로 연결 성공 인사 → 퀴즈 생성까지 전 과정 확인, ngrok 로그로 요청 도달 확인)

### 🔴 현재 막힌 것 (다음에 이어서 할 일 #1)
- **실제 카카오톡 채널에서 봇이 무응답** (봇 테스트는 정상)
  - 상태: 봇 "실행" / 운영채널 "warmpal" 연결됨 / 배포 완료 — 오픈빌더 쪽은 정상
  - 증상: 실제 채널 메시지가 **우리 서버에 0건 도달** (ngrok 로그 확인) = 카카오가 봇을 호출 안 함
  - **추정 원인:** 카카오톡 채널 관리자센터의 **상담(1:1 채팅) 우선** 라우팅 → 메시지가 봇 대신 상담함으로 빠짐
  - **해결 방법(확인 필요):** center-pf.kakao.com → warmpal → **챗봇** 메뉴에서
    "챗봇 우선 응답"으로 설정 / 테스트 동안 **1:1 채팅(상담) OFF**.
    채널 상담목록에 내 메시지가 "상담 대기"로 쌓이면 상담-우선 확정.

### 📋 앞으로 할 일 (TODO)
1. **[최우선] 채널 상담-우선 라우팅 해제** → 실제 폰에서 봇 응답 살리기 (위 🔴)
2. **ngrok 주소 관리:** 무료 ngrok은 재시작 시 주소가 바뀜 → 매번 오픈빌더 스킬 URL 갱신 + **재배포** 필요.
   재시작 명령은 반드시 `ngrok http 8001 --region jp` (이 네트워크는 US/글로벌 차단됨).
   → 장기적으론 **고정 도메인(ngrok 유료) 또는 클라우드 배포**로 이전 검토.
3. **실제 폰 첫 연결:** 봇 테스트로 연결된 가짜 user.id는, 실제 폰에서 연결번호 재전송 시 자동 갱신됨(코드가 최신 사용자로 덮어씀) — 동작 확인 필요.
4. **리마인더 발송 정책 결정** (봇은 정시 푸시 불가):
   - (무료, 추천) **피기백 강화** — 어르신이 채팅 열 때 밀린 리마인더를 봇이 먼저 안내 (`/kakao/skill`에 로직 추가 예정)
   - (유료) **알림톡 연동** — 발신대행사(솔라피/알리고/NHN) + 템플릿 심사 필요. `send_alimtalk()` 스텁부터 스캐폴딩 가능
   - 카카오 이벤트 API는 비즈니스 심사 필요 → 학교 프로젝트엔 비현실적
5. (선택) 스킬 보안: `.env`의 `KAKAO_BOT_SECRET` 설정 시 `X-Bot-Secret` 헤더 검증 활성화

---

## 주요 구현 사항

### 채팅 흐름

```
가족(대시보드) → 채팅 링크 복사 → 어르신 기기에 전달
어르신 → /chat?id=<elderly_id> 접속 → 메시지 입력
→ POST /chat/message → AI 응답 → Firestore 저장 → 화면 표시
```

스케줄러 메시지(아침 인사/리마인더/선제 메시지)는 Firestore에 저장 → 채팅창 폴링(3초)으로 수신

---

### 카카오톡 챗봇 연동 (routers/kakao.py)

카카오 i 오픈빌더 **스킬 서버** 방식. 어르신이 카카오톡 채널에 보낸 메시지를 카카오가
`POST /kakao/skill` 로 전달 → 기존 `process_inbound_message`(감정분석·대화저장·퀴즈·알림) 재사용 → 카카오 응답(JSON v2.0)으로 반환.

> ⚠️ 카카오 채널은 **봇이 사용자에게 먼저 친구 추가를 걸 수 없다**(정책). 그래서 "봇이 먼저 다가오는"
> 경험은 **가족이 전달한 채널 추가 링크 + 연결코드**로 어르신을 자동 식별해 봇이 먼저 인사하는 방식으로 구현.

```
가족(대시보드) → '카카오톡으로 연결' 카드에서 채널 추가 링크 + 연결번호(6자리) + QR 확보 → 어르신에게 전달
어르신 → 링크로 채널 추가 → 연결번호 한 번 전송(또는 가족이 대신 입력)
→ POST /kakao/skill → 연결코드로 어르신 자동 인식 → kakao_user_id 저장
→ 봇이 호칭(페르소나)으로 먼저 인사 → 이후 일반 대화
```

**오픈빌더 설정**
1. 카카오톡 채널 생성 → 챗봇 만들기 → 채널 공개 ID(`_xxxx`)를 `.env` 의 `KAKAO_CHANNEL_PUBLIC_ID` 에 입력
2. 스킬 등록: URL = `{공개 BASE_URL}/kakao/skill` (배포 후 https 필요, ngrok 등으로 로컬 테스트 가능)
3. 폴백 블록(및 웰컴/채널추가 블록) 응답을 해당 스킬로 연결
4. (선택) 스킬 헤더에 `X-Bot-Secret` 추가 → `.env` 의 `KAKAO_BOT_SECRET` 와 일치 시에만 처리

**사용자 매핑** — 카카오 `user.id`(봇 단위 익명 해시) ↔ 어르신 연결
- **주 경로 — 연결코드:** 어르신별 6자리 `kakao_connect_code`(`get_or_create_connect_code`). 발화 또는
  오픈빌더 파라미터(`action.params.code` 등)에서 코드 추출 → 일치 어르신에 `kakao_user_id` 저장.
  어르신은 전화번호 입력 불필요 (가족이 코드를 전달).
- **보조 경로 — 전화번호:** 어르신이 전화번호를 보내면 등록 정보와 매칭(`010…`/`+8210…` 정규화).
- 연결 후에는 웹 채팅과 동일하게 대화 (`퀴즈`/`노래 추천` 빠른 명령 + quickReplies 버튼 지원).

**관련 API / 필드**
- `GET /users/elderly/{id}/kakao-link` → `{connect_code, channel_public_id, add_url, chat_url, linked}`
- 대시보드 '💬 카카오톡으로 연결' 카드: 연결번호·채널 링크·QR·안내문구 복사
- Elderly 필드: `kakao_user_id`(연결된 카카오 ID), `kakao_connect_code`(자동연결 코드)

**제약**
- 카카오 스킬 서버는 5초 내 응답 필요 (GPT-4o-mini는 보통 1~3초로 충분, 초과 시 콜백 방식 필요)
- 능동(push) 발송은 친구톡/알림톡 심사가 필요 → 아침 인사·선제 메시지 등 스케줄러 메시지는 기존처럼 웹 채팅에서 확인

---

### Elderly 스키마 필드 (models/schemas.py)

| 필드 | 기본값 | 설명 |
|------|--------|------|
| `name` | - | 어르신 실명 |
| `phone` | - | 전화번호 |
| `nickname` | "어르신" | 케어 도우미 페르소나일 때 AI 호칭 |
| `family_name` | "자녀" | 어르신이 가족을 부를 호칭 |
| `health_conditions` | [] | 건강 상태 태그 |
| `medication_times` | [] | 약 복용 알림 시간 목록 |
| `ai_persona` | "케어 도우미" | AI 역할 (손자/손녀/아들/딸/친구/케어 도우미) |
| `gender` | "여성" | 어르신 성별 (호칭 자동 결정에 사용) |
| `ai_display_name` | "따뜻한하루" | 채팅창에 표시되는 AI 이름 |
| `ai_avatar` | "💛" | 채팅창 AI 프로필 이모지 |
| `friend_name` | "" | 친구 페르소나일 때 AI가 부를 이름 |
| `proactive_enabled` | true | AI 선제 메시지 활성화 |
| `proactive_start_hour` | 10 | 선제 메시지 시작 시간 |
| `proactive_end_hour` | 20 | 선제 메시지 종료 시간 |
| `proactive_times_per_day` | 2 | 하루 선제 메시지 횟수 |
| `kakao_user_id` | "" | 연결된 카카오톡 봇 사용자 ID (연결 시 자동 저장) |
| `kakao_connect_code` | "" | 카카오 봇 자동연결용 6자리 코드 (가족이 어르신에게 전달) |

---

### AI 페르소나 시스템 (services/ai_service.py)

페르소나별 말투와 자동 호칭:

| 페르소나 | 여성 어르신 호칭 | 남성 어르신 호칭 | 말투 |
|---------|--------------|--------------|------|
| 손자 | 할머니 | 할아버지 | 밝고 귀엽게, 애교 넘치게 |
| 손녀 | 할머니 | 할아버지 | 사랑스럽고 설레게 |
| 아들 | 어머니 | 아버지 | 든든하고 친근하게 |
| 딸 | 어머니 | 아버지 | 살뜰하고 다정하게 |
| 친구 | friend_name 또는 실명 | 동일 | 반말, 허물없이 |
| 케어 도우미 | nickname | 동일 | 친절하고 전문적으로 |

- 페르소나 변경 시 `_memory_store` 자동 초기화 (이전 대화 맥락 리셋)
- 리마인더·아침 인사·선제 메시지 모두 페르소나 말투 적용

---

### 스케줄러 (main.py + routers/health.py)

| 작업 | 주기 | 설명 |
|------|------|------|
| `run_morning_messages` | 매일 09:00 | 전체 어르신에게 아침 인사 |
| `run_medication_reminders` | 30분마다 | 약 복용 시간 체크 (±15분, 중복 방지) |
| `run_no_response_check` | 1시간마다 | 24시간 무응답 시 가족 알림 생성 |
| `run_daily_summary` | 매일 23:30 | 오늘 대화 AI 요약 생성 |
| `run_proactive_messages` | 1시간마다 | 어르신별 설정 시간대·빈도로 선제 메시지 |

---

### 대시보드 기능 (dashboard/page.tsx)

- 어르신 목록 사이드바 (추가/삭제/수정)
- 요약 카드: 7일 응답률, 연속 응답일, 오늘 감정, 읽지 않은 알림
- 탭: 감정 트렌드(7일 꺾은선) / 건강 현황(4주 막대) / 대화 기록
- 리마인더 직접 발송: 약 복용 / 식사 / 혈압 측정 / 취미 콘텐츠
- 채팅 링크 복사
- 5분 자동 새로고침

---

### EditElderlyModal 설정 항목 (components/EditElderlyModal.tsx)

1. **채팅창 프로필**: AI 이름, 프로필 이모지(12종), 미리보기
2. **AI 역할**: 6종 페르소나 선택 + 성별 선택 + 호칭 자동 결정 미리보기
   - 케어 도우미: 직접 호칭 입력
   - 친구: 부를 이름 입력
   - 나머지: 자동 결정
3. **AI 선제 메시지**: 켜기/끄기 토글, 시간대(시작~종료), 빈도(자주/보통/살짝 뜸하게)
4. **약 복용 알림 시간**: 최대 6개 시간 추가/삭제
5. **건강 상태 태그**: 추가/삭제

---

### 채팅 페이지 기능 (chat/page.tsx)

- 3초 폴링 (스케줄러 메시지 수신)
- 스크롤 위치 감지: 위로 스크롤 중엔 자동 스크롤 차단, "새 메시지 ↓" 배지 표시
- 글씨 크게/작게 토글
- 빠른 버튼: 🎵 노래 추천 / 🧩 퀴즈 내줘
- AI 프로필(이름·이모지) Firestore에서 동적 로드

---

### 퀴즈 인터랙션 (ai_service.py + chat.py)

1. 🧩 퀴즈 내줘 버튼 → LLM이 QUESTION/ANSWER 분리 생성
2. 질문만 채팅에 전송, 정답은 `pending_quiz_answer` 로 Firestore 저장
3. 어르신이 답변 → 정답 평가 후 칭찬/격려 응답, pending_quiz_answer 초기화
4. 퀴즈 형식: 빈칸 채우기 / 속담 뜻 맞히기 / 노래 가사 빈칸

---

### 노래 추천 (ai_service.py)

- 🎵 노래 추천 버튼 → 페르소나 말투로 옛날 노래 1곡 추천 (제목·소개·가사 한 줄)
- 건강 질문 없이 추천으로만 종료

---

## API 엔드포인트 요약

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/users/family/register` | 가족 회원가입 |
| POST | `/users/family/login` | 가족 로그인 |
| GET | `/users/family/me` | 내 정보 |
| POST | `/users/elderly` | 어르신 등록 |
| GET | `/users/elderly` | 어르신 목록 |
| PATCH | `/users/elderly/{id}` | 어르신 정보 수정 |
| GET | `/users/elderly/{id}/kakao-link` | 카카오 연결코드·채널 링크 조회 |
| DELETE | `/users/elderly/{id}` | 어르신 삭제 |
| POST | `/chat/message` | 메시지 전송 → AI 응답 |
| POST | `/kakao/skill` | 카카오톡 챗봇 스킬 웹훅 → AI 응답 |
| GET | `/chat/history/{id}` | 대화 기록 + AI 프로필 조회 |
| POST | `/chat/hobby/{id}?content_type=song\|quiz` | 취미 콘텐츠 생성 |
| GET | `/dashboard/summary/{id}` | 대시보드 요약 |
| GET | `/dashboard/conversations/{id}` | 대화 기록 |
| GET | `/dashboard/alerts` | 알림 목록 |
| PATCH | `/dashboard/alerts/{id}/read` | 알림 읽음 처리 |
| POST | `/health/reminder/send/{id}` | 리마인더 수동 발송 |

---

## Firebase Firestore 컬렉션

| 컬렉션 | 키 | 설명 |
|--------|-----|------|
| `elderly` | doc_id | 어르신 프로필 (`kakao_user_id` 로 카카오 사용자 매핑) |
| `families` | doc_id | 가족 계정 |
| `conversations` | `{elderly_id}_{date}` | 일별 대화 (messages 배열, pending_quiz_answer) |
| `reminders` | doc_id | 리마인더 발송 이력 |
| `alerts` | doc_id | 가족 알림 |

> Firestore 복합 인덱스 미생성 → 단일 필드 필터 후 Python에서 정렬/범위 처리

---

## 주의사항

- `firebase-credentials.json` 은 git에 절대 포함하지 말 것
- `NEXT_PUBLIC_*` 환경변수 변경 시 Next.js 서버 재시작 필요
- 페르소나 변경 시 해당 어르신의 대화 메모리가 초기화됨
- Firestore 복합 인덱스 없이 운영 중 (대용량 시 성능 저하 가능)
