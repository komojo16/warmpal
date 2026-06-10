import os
import logging
from functools import lru_cache
from datetime import datetime, timezone, date as date_type

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

logger = logging.getLogger("warmpal.firebase")


def _init_app() -> None:
    if firebase_admin._apps:
        return
    # 클라우드(Render 등): 서비스계정 JSON 전체를 환경변수로 주입 → 파일 대신 dict 로 인증
    # 로컬: FIREBASE_CREDENTIALS_PATH 파일 사용 (기본값 ./firebase-credentials.json)
    cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    if cred_json:
        import json
        cred = credentials.Certificate(json.loads(cred_json))
    else:
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "./firebase-credentials.json")
        cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    })


@lru_cache(maxsize=1)
def get_db():
    _init_app()
    return firestore.client()


# ── Generic helpers ───────────────────────────────────────────────────────────

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def doc_to_dict(doc) -> dict:
    data = doc.to_dict() or {}
    data["id"] = doc.id
    return data


# ── Elderly ───────────────────────────────────────────────────────────────────

def create_elderly(data: dict) -> dict:
    db = get_db()
    data["created_at"] = now_utc()
    data["last_response_at"] = None
    data["response_streak"] = 0
    ref = db.collection("elderly").document()
    ref.set(data)
    return {**data, "id": ref.id}


def get_elderly_by_id(elderly_id: str) -> dict | None:
    db = get_db()
    doc = db.collection("elderly").document(elderly_id).get()
    return doc_to_dict(doc) if doc.exists else None


def get_elderly_by_phone(phone: str) -> dict | None:
    db = get_db()
    docs = (
        db.collection("elderly")
        .where(filter=FieldFilter("phone", "==", phone))
        .limit(1)
        .get()
    )
    return doc_to_dict(docs[0]) if docs else None


def get_elderly_by_kakao_id(kakao_user_id: str) -> dict | None:
    db = get_db()
    docs = (
        db.collection("elderly")
        .where(filter=FieldFilter("kakao_user_id", "==", kakao_user_id))
        .limit(1)
        .get()
    )
    return doc_to_dict(docs[0]) if docs else None


def get_elderly_by_connect_code(code: str) -> dict | None:
    db = get_db()
    docs = (
        db.collection("elderly")
        .where(filter=FieldFilter("kakao_connect_code", "==", code))
        .limit(1)
        .get()
    )
    return doc_to_dict(docs[0]) if docs else None


def get_or_create_connect_code(elderly_id: str) -> str:
    """어르신의 카카오 자동연결 코드를 반환(없으면 고유한 6자리 코드 생성·저장)"""
    import random
    elderly = get_elderly_by_id(elderly_id)
    if not elderly:
        return ""
    code = elderly.get("kakao_connect_code")
    if code:
        return code
    for _ in range(30):
        candidate = f"{random.randint(0, 999999):06d}"
        if not get_elderly_by_connect_code(candidate):
            update_elderly(elderly_id, {"kakao_connect_code": candidate})
            return candidate
    # 극히 드문 충돌 — elderly_id 일부로 대체
    candidate = elderly_id[:6]
    update_elderly(elderly_id, {"kakao_connect_code": candidate})
    return candidate


def get_elderly_by_family(family_id: str) -> list[dict]:
    db = get_db()
    docs = db.collection("elderly").where(filter=FieldFilter("family_id", "==", family_id)).get()
    return [doc_to_dict(d) for d in docs]


def update_elderly(elderly_id: str, data: dict) -> None:
    db = get_db()
    db.collection("elderly").document(elderly_id).update(data)


def update_response_streak(elderly_id: str) -> None:
    """연속 응답일(streak) 업데이트. last_response_at 갱신 전에 호출해야 함."""
    elderly = get_elderly_by_id(elderly_id)
    if not elderly:
        return

    last_resp = elderly.get("last_response_at")
    today = datetime.now(timezone.utc).date()

    if last_resp is None:
        new_streak = 1
    else:
        # Firestore에서 오면 datetime 또는 DatetimWithNanoseconds
        if hasattr(last_resp, "date"):
            last_date = last_resp.date()
        else:
            last_date = today  # 이미 오늘이면 streak 변경 없음

        diff = (today - last_date).days
        if diff == 0:
            return  # 오늘 이미 응답함 → streak 변경 없음
        elif diff == 1:
            new_streak = elderly.get("response_streak", 0) + 1
        else:
            new_streak = 1

    update_elderly(elderly_id, {"response_streak": new_streak})
    logger.info(f"streak 업데이트: {elderly_id} → {new_streak}일")


# ── Family ────────────────────────────────────────────────────────────────────

def create_family(data: dict) -> dict:
    db = get_db()
    data["created_at"] = now_utc()
    ref = db.collection("families").document()
    ref.set(data)
    return {**data, "id": ref.id}


def get_family_by_email(email: str) -> dict | None:
    db = get_db()
    docs = (
        db.collection("families")
        .where(filter=FieldFilter("email", "==", email))
        .limit(1)
        .get()
    )
    return doc_to_dict(docs[0]) if docs else None


def get_family_by_id(family_id: str) -> dict | None:
    db = get_db()
    doc = db.collection("families").document(family_id).get()
    return doc_to_dict(doc) if doc.exists else None


# ── Conversations ─────────────────────────────────────────────────────────────

def add_message(elderly_id: str, date: str, message: dict) -> None:
    db = get_db()
    doc_id = f"{elderly_id}_{date}"
    ref = db.collection("conversations").document(doc_id)
    doc = ref.get()
    if doc.exists:
        data = doc.to_dict()
        messages = data.get("messages", [])
        messages.append(message)
        ref.update({"messages": messages})
    else:
        ref.set({
            "elderly_id": elderly_id,
            "date": date,
            "messages": [message],
            "daily_emotion": None,
            "summary": None,
        })


def get_conversation(elderly_id: str, date: str) -> dict | None:
    db = get_db()
    doc_id = f"{elderly_id}_{date}"
    doc = db.collection("conversations").document(doc_id).get()
    if not doc.exists:
        return None
    data = doc_to_dict(doc)
    data["id"] = doc_id
    return data


def get_conversations_range(elderly_id: str, start_date: str, end_date: str) -> list[dict]:
    db = get_db()
    # 복합 인덱스 없이도 동작: elderly_id만 필터링 후 Python에서 날짜 범위 필터
    docs = (
        db.collection("conversations")
        .where(filter=FieldFilter("elderly_id", "==", elderly_id))
        .get()
    )
    result = [doc_to_dict(d) for d in docs]
    result = [r for r in result if start_date <= r.get("date", "") <= end_date]
    result.sort(key=lambda x: x.get("date", ""))
    return result


def update_conversation(elderly_id: str, date: str, data: dict) -> None:
    db = get_db()
    doc_id = f"{elderly_id}_{date}"
    db.collection("conversations").document(doc_id).update(data)


# ── Reminders ─────────────────────────────────────────────────────────────────

def create_reminder(data: dict) -> dict:
    db = get_db()
    data["created_at"] = now_utc()
    ref = db.collection("reminders").document()
    ref.set(data)
    return {**data, "id": ref.id}


def get_unacknowledged_reminders(elderly_id: str) -> list[dict]:
    db = get_db()
    docs = (
        db.collection("reminders")
        .where(filter=FieldFilter("elderly_id", "==", elderly_id))
        .get()
    )
    return [doc_to_dict(d) for d in docs if not d.to_dict().get("acknowledged", False)]


def acknowledge_reminder(reminder_id: str) -> None:
    db = get_db()
    db.collection("reminders").document(reminder_id).update({
        "acknowledged": True,
        "acknowledged_at": now_utc(),
    })


def check_reminder_sent(elderly_id: str, reminder_type: str, date: str, hour_str: str) -> bool:
    """특정 날짜·시간대에 리마인더가 이미 발송되었는지 확인 (중복 방지)"""
    db = get_db()
    docs = (
        db.collection("reminders")
        .where(filter=FieldFilter("elderly_id", "==", elderly_id))
        .where(filter=FieldFilter("reminder_type", "==", reminder_type))
        .where(filter=FieldFilter("date", "==", date))
        .get()
    )
    for doc in docs:
        data = doc.to_dict()
        scheduled_at = data.get("scheduled_at", "")
        # scheduled_at은 ISO 문자열 "2026-06-01T08:05:00" 형태
        if isinstance(scheduled_at, str) and len(scheduled_at) >= 13:
            if scheduled_at[11:13] == hour_str:
                return True
    return False


# ── Alerts ────────────────────────────────────────────────────────────────────

def create_alert(data: dict) -> dict:
    db = get_db()
    data["created_at"] = now_utc()
    data["is_read"] = False
    ref = db.collection("alerts").document()
    ref.set(data)
    return {**data, "id": ref.id}


def get_alerts(family_id: str, elderly_id: str | None = None, unread_only: bool = False) -> list[dict]:
    db = get_db()
    elderly_ids = [e["id"] for e in get_elderly_by_family(family_id)]
    if elderly_id:
        elderly_ids = [elderly_id] if elderly_id in elderly_ids else []

    all_alerts = []
    for eid in elderly_ids:
        # 복합 인덱스 없이 동작: elderly_id만 필터링 후 Python에서 처리
        docs = (db.collection("alerts")
            .where(filter=FieldFilter("elderly_id", "==", eid))
            .limit(100).get())
        alerts = [doc_to_dict(d) for d in docs]
        if unread_only:
            alerts = [a for a in alerts if not a.get("is_read", False)]
        all_alerts.extend(alerts[:50])

    all_alerts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return all_alerts


def mark_alert_read(alert_id: str) -> None:
    db = get_db()
    db.collection("alerts").document(alert_id).update({"is_read": True})
