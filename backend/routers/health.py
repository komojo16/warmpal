"""건강 리마인더 스케줄러 및 API"""
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends

from routers.users import get_current_family
from services import firebase as db
from services.ai_service import generate_reminder_message

logger = logging.getLogger("warmpal.health")
router = APIRouter(prefix="/health", tags=["Health"])


def _send_reminder(elderly: dict, reminder_type: str) -> None:
    """리마인더 메시지를 Firestore에 AI 메시지로 저장"""
    message = generate_reminder_message(elderly, reminder_type)
    today = datetime.now().strftime("%Y-%m-%d")
    db.add_message(elderly["id"], today, {
        "role": "ai",
        "content": message,
        "timestamp": datetime.now().isoformat(),
        "emotion": None,
        "emotion_score": None,
    })
    db.create_reminder({
        "elderly_id": elderly["id"],
        "reminder_type": reminder_type,
        "scheduled_at": db.now_utc().isoformat(),
        "acknowledged": False,
        "date": today,
    })


async def run_morning_messages() -> None:
    """매일 오전 9시 실행 — 전체 어르신에게 인사 메시지"""
    from services.ai_service import generate_morning_message
    all_elderly = db.get_db().collection("elderly").get()
    for doc in all_elderly:
        elderly = {**doc.to_dict(), "id": doc.id}
        try:
            message = await generate_morning_message(elderly)
            today = datetime.now().strftime("%Y-%m-%d")
            db.add_message(elderly["id"], today, {
                "role": "ai",
                "content": message,
                "timestamp": datetime.now().isoformat(),
                "emotion": None,
                "emotion_score": None,
            })
            logger.info(f"아침 인사 발송: {elderly['id']}")
        except Exception as e:
            logger.error(f"아침 인사 오류 {elderly['id']}: {e}")


async def run_medication_reminders() -> None:
    """약 복용 시간 체크 (30분마다 실행) — 중복 방지 포함"""
    now_str = datetime.now().strftime("%H:%M")
    today = datetime.now().strftime("%Y-%m-%d")
    all_elderly = db.get_db().collection("elderly").get()

    for doc in all_elderly:
        elderly = {**doc.to_dict(), "id": doc.id}
        med_times = elderly.get("medication_times", [])
        for t in med_times:
            try:
                scheduled = datetime.strptime(t, "%H:%M")
                now = datetime.strptime(now_str, "%H:%M")
                diff = abs((now - scheduled).total_seconds()) / 60
                if diff <= 15:
                    # 오늘 이 시간대에 이미 리마인더를 발송했는지 확인
                    hour_str = t[:2]
                    if not db.check_reminder_sent(elderly["id"], "medication", today, hour_str):
                        _send_reminder(elderly, "medication")
                        logger.info(f"약 복용 리마인더 발송: {elderly['id']} ({t})")
            except Exception as e:
                logger.error(f"리마인더 오류 {elderly['id']}: {e}")


async def run_no_response_check() -> None:
    """24시간 응답 없는 어르신 감지 → 가족 알림"""
    threshold = datetime.now(timezone.utc) - timedelta(hours=24)
    today = datetime.now().strftime("%Y-%m-%d")
    all_elderly = db.get_db().collection("elderly").get()

    for doc in all_elderly:
        elderly = {**doc.to_dict(), "id": doc.id}
        last_resp = elderly.get("last_response_at")
        if last_resp is None or last_resp < threshold:
            existing = (
                db.get_db()
                .collection("alerts")
                .where("elderly_id", "==", elderly["id"])
                .where("alert_type", "==", "no_response")
                .where("date", "==", today)
                .limit(1)
                .get()
            )
            if not existing:
                db.create_alert({
                    "elderly_id": elderly["id"],
                    "family_id": elderly.get("family_id"),
                    "alert_type": "no_response",
                    "date": today,
                    "message": f"{elderly.get('nickname', '어르신')}께서 24시간 동안 응답이 없습니다. 안부를 확인해 주세요.",
                })
                logger.warning(f"무응답 알림: {elderly['id']}")


async def run_proactive_messages() -> None:
    """매 시간 실행 — 각 어르신의 설정 범위·빈도에 맞춰 선제 메시지 발송"""
    from services.ai_service import generate_morning_message
    now = datetime.now()
    current_hour = now.hour
    today = now.strftime("%Y-%m-%d")
    all_elderly = db.get_db().collection("elderly").get()

    for doc in all_elderly:
        elderly = {**doc.to_dict(), "id": doc.id}
        try:
            if not elderly.get("proactive_enabled", True):
                continue

            start_h = elderly.get("proactive_start_hour", 10)
            end_h = elderly.get("proactive_end_hour", 20)
            max_times = elderly.get("proactive_times_per_day", 2)

            if not (start_h <= current_hour < end_h):
                continue

            # 오늘 이미 보낸 선제 메시지 횟수 확인
            sent_today = len([
                d for d in db.get_db().collection("reminders")
                .where("elderly_id", "==", elderly["id"])
                .where("reminder_type", "==", "proactive")
                .where("date", "==", today)
                .get()
            ])
            if sent_today >= max_times:
                continue

            # 시간 범위를 max_times 등분해서 현재 슬롯에 해당할 때만 발송
            total_hours = max(end_h - start_h, 1)
            slot_size = total_hours / max_times
            slot_index = int((current_hour - start_h) / slot_size)

            already_sent_slot = len([
                d for d in db.get_db().collection("reminders")
                .where("elderly_id", "==", elderly["id"])
                .where("reminder_type", "==", "proactive")
                .where("date", "==", today)
                .where("slot", "==", slot_index)
                .get()
            ])
            if already_sent_slot > 0:
                continue

            message = await generate_morning_message(elderly)
            db.add_message(elderly["id"], today, {
                "role": "ai",
                "content": message,
                "timestamp": now.isoformat(),
                "emotion": None,
                "emotion_score": None,
            })
            db.create_reminder({
                "elderly_id": elderly["id"],
                "reminder_type": "proactive",
                "scheduled_at": now.isoformat(),
                "acknowledged": False,
                "date": today,
                "slot": slot_index,
            })
            logger.info(f"선제 메시지 발송: {elderly['id']} (슬롯 {slot_index})")
        except Exception as e:
            logger.error(f"선제 메시지 오류 {elderly['id']}: {e}")


async def run_daily_summary() -> None:
    """매일 23:30 — 오늘 대화 요약 생성"""
    from services.ai_service import generate_daily_summary
    today = datetime.now().strftime("%Y-%m-%d")
    all_elderly = db.get_db().collection("elderly").get()

    for doc in all_elderly:
        elderly = {**doc.to_dict(), "id": doc.id}
        try:
            conv = db.get_conversation(elderly["id"], today)
            if conv and conv.get("messages"):
                summary = await generate_daily_summary(elderly, conv["messages"])
                db.update_conversation(elderly["id"], today, {"summary": summary})
                logger.info(f"일일 요약 생성: {elderly['id']}")
        except Exception as e:
            logger.error(f"일일 요약 오류 {elderly['id']}: {e}")


# ── API ────────────────────────────────────────────────────────────────────────

@router.post("/reminder/send/{elderly_id}")
def send_manual_reminder(
    elderly_id: str,
    reminder_type: str = "medication",
    family: dict = Depends(get_current_family),
):
    """수동으로 리마인더 발송"""
    elderly = db.get_elderly_by_id(elderly_id)
    if not elderly or elderly.get("family_id") != family["id"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="어르신을 찾을 수 없습니다.")
    _send_reminder(elderly, reminder_type)
    return {"message": f"{reminder_type} 리마인더를 발송했습니다."}


@router.get("/reminders/{elderly_id}")
def get_reminders(elderly_id: str, family: dict = Depends(get_current_family)):
    elderly = db.get_elderly_by_id(elderly_id)
    if not elderly or elderly.get("family_id") != family["id"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="어르신을 찾을 수 없습니다.")
    return db.get_unacknowledged_reminders(elderly_id)
