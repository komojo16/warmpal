"""Twilio SMS 웹훅 라우터 (1주차)"""
from fastapi import APIRouter, Form, Response, HTTPException
from twilio.request_validator import RequestValidator
from fastapi import Request
import os

from services.firebase import get_elderly_by_phone, update_elderly
from services.ai_service import process_inbound_sms
from services.sms_service import send_sms_safe
from services.firebase import now_utc

router = APIRouter(prefix="/sms", tags=["SMS"])


def _validate_twilio(request: Request, body: bytes) -> bool:
    """Twilio 서명 검증"""
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    validator = RequestValidator(auth_token)
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    # Form 데이터는 이미 파싱된 값으로 검증
    return True  # 개발 중에는 pass; 프로덕션에서 활성화 필요


@router.post("/webhook")
async def sms_webhook(
    request: Request,
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...),
):
    """
    Twilio가 SMS 수신 시 호출하는 웹훅
    1. 발신 번호로 어르신 조회
    2. AI 응답 생성
    3. 응답 SMS 발송
    """
    # Twilio 서명 검증 (프로덕션)
    # raw_body = await request.body()
    # if not _validate_twilio(request, raw_body):
    #     raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    # 어르신 조회
    elderly = get_elderly_by_phone(From)
    if not elderly:
        # 등록되지 않은 번호 — 무시
        return Response(content="<?xml version='1.0' encoding='UTF-8'?><Response/>", media_type="text/xml")

    # 마지막 응답 시각 업데이트
    update_elderly(elderly["id"], {"last_response_at": now_utc()})

    # AI 응답 생성 (감정 분석 + 대화 저장 포함)
    ai_reply = await process_inbound_sms(elderly, Body.strip())

    # SMS 발송
    send_sms_safe(From, ai_reply)

    # Twilio는 TwiML 응답을 기대함 (빈 응답으로 중복 발송 방지)
    return Response(
        content="<?xml version='1.0' encoding='UTF-8'?><Response/>",
        media_type="text/xml",
    )


@router.post("/send-test")
async def send_test_sms(to: str, message: str):
    """테스트용 SMS 직접 발송"""
    sid = send_sms_safe(to, message)
    return {"success": sid is not None, "sid": sid}
