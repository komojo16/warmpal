"""Twilio SMS 송수신 서비스"""
import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException


def _get_client() -> Client:
    return Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN"),
    )


def send_sms(to: str, body: str) -> str:
    """
    SMS 발송
    반환: message SID
    """
    client = _get_client()
    from_number = os.getenv("TWILIO_PHONE_NUMBER")
    try:
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=to,
        )
        return message.sid
    except TwilioRestException as e:
        raise RuntimeError(f"SMS 발송 실패: {e.msg}") from e


def send_sms_safe(to: str, body: str) -> str | None:
    """예외를 삼키고 None 반환 (스케줄러용)"""
    try:
        return send_sms(to, body)
    except Exception as e:
        print(f"[SMS] 발송 오류 {to}: {e}")
        return None
