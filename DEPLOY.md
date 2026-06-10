# warmpal 배포 가이드 (MVP)

구조: **프론트엔드 → Vercel**, **백엔드(FastAPI + 스케줄러) → Render**, **DB → Firebase Firestore**

```
[사용자 브라우저] → Vercel(Next.js) → Render(FastAPI) → Firebase / OpenAI
```

> ⚠️ 비밀값(`.env`, `firebase-credentials.json`)은 git에 올라가지 않습니다(.gitignore). 모든 키는 각 플랫폼 대시보드에 직접 입력합니다.

---

## 0. 사전 준비 (한 번만)
- [x] GitHub 저장소: `komojo16/warmpal` (이미 있음)
- [x] OpenAI API 키, Firebase 프로젝트 + `firebase-credentials.json` (로컬에 보유)
- [ ] Render 계정: https://render.com (GitHub 로그인)
- [x] Vercel 계정

먼저 변경사항을 push 합니다 (이미 했다면 생략):
```bash
git push origin main
```

---

## 1. 백엔드 배포 — Render

1. Render 대시보드 → **New → Blueprint** → `komojo16/warmpal` 선택 → `render.yaml` 자동 인식
2. 아래 환경변수(secret)를 입력:

   | 키 | 값 |
   |----|----|
   | `OPENAI_API_KEY` | 로컬 `backend/.env` 의 `sk-...` 값 |
   | `FIREBASE_PROJECT_ID` | `warmpal...` (로컬 .env 값) |
   | `FIREBASE_CREDENTIALS_JSON` | `firebase-credentials.json` **파일 내용 전체**를 복사해 붙여넣기 |
   | `FRONTEND_URL` | 일단 비워두거나 `https://example.com` → 2단계 후 실제 Vercel 주소로 수정 |
   | `APP_BASE_URL` | 배포되면 생기는 주소 (예: `https://warmpal-backend.onrender.com`) |
   | `KAKAO_CHANNEL_PUBLIC_ID` | `_VwXnX` (선택) |

   > `FIREBASE_CREDENTIALS_JSON` 한 줄 변환:
   > PowerShell — `Get-Content backend\firebase-credentials.json -Raw | Set-Clipboard` 후 붙여넣기

3. **Create** → 빌드 완료까지 2~4분. 끝나면 `https://warmpal-backend.onrender.com` 같은 주소 발급.
4. 동작 확인: 브라우저로 `<백엔드주소>/health` → `{"status":"ok"}` 보이면 성공.

---

## 2. 프론트엔드 배포 — Vercel

1. Vercel → **Add New → Project** → `komojo16/warmpal` import
2. **Root Directory** 를 반드시 `frontend` 로 설정 (Next.js 자동 감지됨)
3. **Environment Variables** 에 추가:

   | 키 | 값 |
   |----|----|
   | `NEXT_PUBLIC_API_URL` | 1단계에서 받은 Render 백엔드 주소 (끝에 `/` 없이) |

4. **Deploy** → 완료되면 `https://warmpal.vercel.app` 같은 주소 발급.

---

## 3. 두 서비스 연결 (CORS)

1. Render 대시보드 → `warmpal-backend` → Environment → `FRONTEND_URL` 을 **실제 Vercel 주소**로 수정 → 자동 재배포.
   - (코드에 `*.vercel.app` 정규식이 이미 허용돼 있어 프리뷰 URL도 동작하지만, 프로덕션 주소를 명시해두는 것이 안전)
2. Vercel 주소로 접속 → 회원가입/로그인 → 어르신 등록 → 채팅까지 동작 확인.

---

## 4. 알아둘 점 (MVP 한계)

- **Render 무료 티어는 15분 미사용 시 슬립.** 첫 요청 시 10~30초 깨어나는 지연이 있고, 깨어난 동안만 스케줄러(아침인사·약알림)가 동작합니다. 채팅·대시보드 등 요청-응답 기능은 정상.
- 스케줄러를 항상 돌리려면: ① Render 유료($7/월) 업그레이드, 또는 ② 외부 cron(예: cron-job.org)이 5~10분마다 `<백엔드주소>/health` 를 호출해 깨워두기.
- 감정분석은 무료 배포에서 **키워드 기반**으로 동작(정확 모델은 `requirements.txt` 의 transformers 주석 해제 + 유료 플랜 필요).
- 카카오톡 봇 스킬 URL 은 이제 ngrok 대신 `https://warmpal-backend.onrender.com/kakao/skill` 로 고정 가능.
