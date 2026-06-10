"""warmpal — FastAPI 백엔드 진입점"""
from dotenv import load_dotenv
load_dotenv()

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from routers import chat, users, dashboard, health as health_router, kakao

# ── 로깅 설정 ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("warmpal")

# ── Rate Limiter ───────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# ── 스케줄러 ──────────────────────────────────────────────────────────────────

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("warmpal 서버 시작")
    scheduler.add_job(
        health_router.run_morning_messages,
        "cron",
        hour=int(os.getenv("DAILY_MESSAGE_HOUR", 9)),
        minute=int(os.getenv("DAILY_MESSAGE_MINUTE", 0)),
        id="morning_messages",
        replace_existing=True,
    )
    scheduler.add_job(
        health_router.run_medication_reminders,
        "interval",
        minutes=int(os.getenv("REMINDER_CHECK_INTERVAL_MINUTES", 30)),
        id="medication_reminders",
        replace_existing=True,
    )
    scheduler.add_job(
        health_router.run_no_response_check,
        "interval",
        hours=1,
        id="no_response_check",
        replace_existing=True,
    )
    scheduler.add_job(
        health_router.run_proactive_messages,
        "interval",
        hours=1,
        id="proactive_messages",
        replace_existing=True,
    )
    scheduler.add_job(
        health_router.run_daily_summary,
        "cron",
        hour=23,
        minute=30,
        id="daily_summary",
        replace_existing=True,
    )
    scheduler.start()
    yield
    logger.info("warmpal 서버 종료")
    scheduler.shutdown()


# ── 앱 설정 ───────────────────────────────────────────────────────────────────

app = FastAPI(
    title="warmpal API",
    description="문자로 가족이 되는 AI 케어 서비스",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
_cors_origins = list({
    frontend_url,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
})
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    # LAN IP 접속 + Vercel 배포 도메인(프로덕션/프리뷰 *.vercel.app) 허용
    allow_origin_regex=r"(http://\d+\.\d+\.\d+\.\d+:\d+|https://.*\.vercel\.app)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"{request.method} {request.url.path}")
    try:
        response = await call_next(request)
    except Exception as exc:
        import traceback
        logger.error(f"Unhandled exception: {traceback.format_exc()}")
        raise
    if response.status_code >= 500:
        logger.error(f"{request.method} {request.url.path} → {response.status_code}")
    elif response.status_code >= 400:
        logger.warning(f"{request.method} {request.url.path} → {response.status_code}")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    logger.error(f"500 at {request.url.path}: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={"Access-Control-Allow-Origin": request.headers.get("origin", "*")},
    )


# ── 라우터 등록 ───────────────────────────────────────────────────────────────

app.include_router(chat.router)
app.include_router(users.router)
app.include_router(dashboard.router)
app.include_router(health_router.router)
app.include_router(kakao.router)


@app.get("/")
def root():
    return {"service": "warmpal", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
