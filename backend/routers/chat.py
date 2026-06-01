"""웹 채팅 라우터 — REST API로 메시지 송수신 + 취미 콘텐츠"""
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from services.firebase import (
    get_elderly_by_id,
    update_elderly,
    update_response_streak,
    update_conversation,
    now_utc,
    get_conversation,
)
from services.ai_service import process_inbound_message, generate_hobby_content

logger = logging.getLogger("warmpal.chat")
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    elderly_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    emotion: str
    timestamp: str


@router.post("/message", response_model=ChatResponse)
@limiter.limit("30/minute")
async def send_message(request: Request, req: ChatRequest):
    """어르신 메시지 수신 → AI 응답 반환"""
    elderly = get_elderly_by_id(req.elderly_id)
    if not elderly:
        raise HTTPException(status_code=404, detail="어르신 정보를 찾을 수 없습니다")

    # 응답 연속일 업데이트 → last_response_at 갱신 전에 streak 계산
    update_response_streak(req.elderly_id)
    update_elderly(elderly["id"], {"last_response_at": now_utc()})

    ai_reply, emotion = await process_inbound_message(elderly, req.message.strip())
    logger.info(f"메시지 처리: elderly={req.elderly_id} emotion={emotion}")

    return ChatResponse(
        reply=ai_reply,
        emotion=emotion,
        timestamp=datetime.now().isoformat(),
    )


@router.get("/history/{elderly_id}")
def get_history(elderly_id: str, date: str = None):
    """오늘(또는 특정 날짜)의 대화 기록 + AI 프로필 정보 반환"""
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    conv = get_conversation(elderly_id, target_date)
    elderly = get_elderly_by_id(elderly_id)
    profile = {
        "ai_display_name": (elderly or {}).get("ai_display_name", "따뜻한하루"),
        "ai_avatar": (elderly or {}).get("ai_avatar", "💛"),
    }
    if not conv:
        return {"date": target_date, "messages": [], **profile}
    return {"date": target_date, "messages": conv.get("messages", []), **profile}


@router.post("/hobby/{elderly_id}")
@limiter.limit("10/minute")
async def get_hobby_content(request: Request, elderly_id: str, content_type: str = "random"):
    """취미 콘텐츠(퀴즈/노래 추천) 생성 및 저장"""
    elderly = get_elderly_by_id(elderly_id)
    if not elderly:
        raise HTTPException(status_code=404, detail="어르신 정보를 찾을 수 없습니다")

    content, quiz_answer = await generate_hobby_content(elderly, content_type)
    today = datetime.now().strftime("%Y-%m-%d")

    from services.firebase import add_message
    add_message(elderly_id, today, {
        "role": "ai",
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "emotion": None,
        "emotion_score": None,
    })

    # 퀴즈인 경우 정답을 대화 문서에 저장해두었다가 다음 메시지에서 평가
    if quiz_answer:
        update_conversation(elderly_id, today, {"pending_quiz_answer": quiz_answer})

    return {"content": content, "timestamp": datetime.now().isoformat()}
