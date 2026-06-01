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
| 채팅 | REST API (웹 채팅, Twilio 제거됨) |
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
| DELETE | `/users/elderly/{id}` | 어르신 삭제 |
| POST | `/chat/message` | 메시지 전송 → AI 응답 |
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
| `elderly` | doc_id | 어르신 프로필 |
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
