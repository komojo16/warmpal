"""가족 대시보드 데이터 API (3주차)"""
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends

from routers.users import get_current_family
from services import firebase as db
from models.schemas import (
    DashboardSummary, DailyEmotionPoint, HealthTrendPoint,
    EmotionLabel, HealthStatus, Alert,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _date_range(days: int) -> tuple[str, str]:
    end = datetime.now()
    start = end - timedelta(days=days - 1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _calc_response_rate(conversations: list[dict], days: int) -> float:
    responded = sum(
        1 for c in conversations
        if any(m["role"] == "elderly" for m in c.get("messages", []))
    )
    return round(responded / days, 2) if days > 0 else 0.0


def _calc_medication_rate(conversations: list[dict]) -> float:
    """대화 중 약 복용 확인 응답 비율"""
    total, acknowledged = 0, 0
    for conv in conversations:
        for msg in conv.get("messages", []):
            if msg["role"] == "ai" and "약" in msg.get("content", ""):
                total += 1
            if msg["role"] == "elderly" and any(
                kw in msg.get("content", "") for kw in ["먹었", "챙겼", "드셨", "먹을게"]
            ):
                acknowledged += 1
    return round(acknowledged / total, 2) if total > 0 else 0.0


@router.get("/summary/{elderly_id}", response_model=DashboardSummary)
def get_dashboard_summary(elderly_id: str, family: dict = Depends(get_current_family)):
    import traceback, logging
    _log = logging.getLogger("warmpal.dashboard")
    try:
        return _get_dashboard_summary_impl(elderly_id, family)
    except HTTPException:
        raise
    except Exception as e:
        _log.error(f"dashboard summary error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


def _get_dashboard_summary_impl(elderly_id: str, family: dict):
    elderly = db.get_elderly_by_id(elderly_id)
    if not elderly or elderly.get("family_id") != family["id"]:
        raise HTTPException(status_code=404, detail="어르신을 찾을 수 없습니다.")

    start_date, end_date = _date_range(30)
    conversations = db.get_conversations_range(elderly_id, start_date, end_date)
    conv_map = {c["date"]: c for c in conversations}

    # 최근 7일 감정 데이터
    recent_emotion: list[DailyEmotionPoint] = []
    emotion_7d_start, _ = _date_range(7)

    for i in range(7):
        date = (datetime.now() - timedelta(days=6 - i)).strftime("%Y-%m-%d")
        conv = conv_map.get(date)
        if conv:
            emotion = conv.get("daily_emotion") or "neutral"
            messages = conv.get("messages", [])
            elderly_msgs = [m for m in messages if m["role"] == "elderly"]
            avg_score = (
                sum(m.get("emotion_score", 0.5) for m in elderly_msgs) / len(elderly_msgs)
                if elderly_msgs else 0.5
            )
            recent_emotion.append(DailyEmotionPoint(
                date=date,
                emotion=EmotionLabel(emotion),
                score=round(avg_score, 4),
                message_count=len(elderly_msgs),
            ))
        else:
            recent_emotion.append(DailyEmotionPoint(
                date=date,
                emotion=EmotionLabel.neutral,
                score=0.5,
                message_count=0,
            ))

    # 건강 트렌드 (주간 단위)
    health_trend: list[HealthTrendPoint] = []
    for week in range(4):
        week_end = datetime.now() - timedelta(days=week * 7)
        week_start = week_end - timedelta(days=6)
        w_start_str = week_start.strftime("%Y-%m-%d")
        w_end_str = week_end.strftime("%Y-%m-%d")

        week_convs = [c for c in conversations if w_start_str <= c["date"] <= w_end_str]
        med_rate = _calc_medication_rate(week_convs)
        resp_rate = _calc_response_rate(week_convs, 7)

        status = HealthStatus.normal
        if resp_rate < 0.5 or med_rate < 0.5:
            status = HealthStatus.warning
        if resp_rate < 0.3:
            status = HealthStatus.danger

        health_trend.append(HealthTrendPoint(
            date=w_start_str,
            medication_rate=med_rate,
            response_rate=resp_rate,
            health_status=status,
        ))
    health_trend.reverse()

    # 알림 개수
    alerts = db.get_alerts(family["id"], elderly_id, unread_only=True)

    # 7일 응답률
    last_7_convs = [c for c in conversations if c["date"] >= emotion_7d_start]
    response_rate_7d = _calc_response_rate(last_7_convs, 7)

    return DashboardSummary(
        elderly=elderly,
        recent_emotion=recent_emotion,
        health_trend=health_trend,
        unread_alerts=len(alerts),
        last_7days_response_rate=response_rate_7d,
        current_streak=elderly.get("response_streak", 0),
    )


@router.get("/conversations/{elderly_id}")
def get_conversations(
    elderly_id: str,
    date: str | None = None,
    family: dict = Depends(get_current_family),
):
    elderly = db.get_elderly_by_id(elderly_id)
    if not elderly or elderly.get("family_id") != family["id"]:
        raise HTTPException(status_code=404, detail="어르신을 찾을 수 없습니다.")

    if date:
        conv = db.get_conversation(elderly_id, date)
        return conv or {}

    start_date, end_date = _date_range(30)
    return db.get_conversations_range(elderly_id, start_date, end_date)


@router.get("/alerts", response_model=list[Alert])
def get_alerts(
    elderly_id: str | None = None,
    unread_only: bool = False,
    family: dict = Depends(get_current_family),
):
    alerts = db.get_alerts(family["id"], elderly_id, unread_only)
    return alerts


@router.patch("/alerts/{alert_id}/read")
def mark_alert_read(alert_id: str, family: dict = Depends(get_current_family)):
    db.mark_alert_read(alert_id)
    return {"message": "읽음 처리되었습니다."}
