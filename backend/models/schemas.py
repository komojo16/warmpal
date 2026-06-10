from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class EmotionLabel(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"
    danger = "danger"


class HealthStatus(str, Enum):
    normal = "normal"
    warning = "warning"
    danger = "danger"


# ── Elderly User ────────────────────────────────────────────────────────────

class ElderlyBase(BaseModel):
    name: str
    phone: str                          # +821012345678
    nickname: str = "어르신"             # AI가 부를 호칭
    family_name: str = "자녀"            # 어르신이 가족을 부를 호칭
    health_conditions: list[str] = []   # ["당뇨", "고혈압"]
    medication_times: list[str] = []    # ["08:00", "20:00"]
    ai_persona: str = "케어 도우미"       # AI 역할 (예: 손자, 아들, 딸, 친구)
    gender: str = "여성"                  # 어르신 성별 ("남성" | "여성")
    ai_display_name: str = "warmpal"   # 채팅창에 표시되는 AI 이름
    ai_avatar: str = "💛"                # 채팅창 AI 프로필 이모지
    friend_name: str = ""                 # 친구 페르소나일 때 AI가 어르신을 부를 이름
    proactive_enabled: bool = True        # AI 선제 메시지 활성화
    proactive_start_hour: int = 10        # 선제 메시지 시작 시간 (0~23)
    proactive_end_hour: int = 20          # 선제 메시지 종료 시간 (0~23)
    proactive_times_per_day: int = 2      # 하루 최대 선제 메시지 횟수
    kakao_user_id: str = ""               # 카카오톡 봇 사용자 ID (연결 시 자동 저장)
    kakao_connect_code: str = ""          # 카카오 봇 자동연결용 코드 (가족이 어르신에게 전달)


class ElderlyCreate(ElderlyBase):
    family_id: str = ""  # 서버에서 JWT 토큰으로 덮어씀


class ElderlyUpdate(BaseModel):
    nickname: Optional[str] = None
    family_name: Optional[str] = None
    health_conditions: Optional[list[str]] = None
    medication_times: Optional[list[str]] = None
    ai_persona: Optional[str] = None
    gender: Optional[str] = None
    ai_display_name: Optional[str] = None
    ai_avatar: Optional[str] = None
    friend_name: Optional[str] = None
    proactive_enabled: Optional[bool] = None
    proactive_start_hour: Optional[int] = None
    proactive_end_hour: Optional[int] = None
    proactive_times_per_day: Optional[int] = None


class Elderly(ElderlyBase):
    id: str
    family_id: str
    created_at: datetime
    last_response_at: Optional[datetime] = None
    response_streak: int = 0            # 연속 응답 일수


# ── Family User ──────────────────────────────────────────────────────────────

class FamilyCreate(BaseModel):
    name: str
    email: str
    password: str


class FamilyLogin(BaseModel):
    email: str
    password: str


class Family(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Conversation ─────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: str                           # "ai" | "elderly"
    content: str
    timestamp: datetime
    emotion: Optional[EmotionLabel] = None
    emotion_score: Optional[float] = None


class ConversationLog(BaseModel):
    id: str
    elderly_id: str
    date: str                           # "2026-04-08"
    messages: list[Message]
    daily_emotion: Optional[EmotionLabel] = None
    summary: Optional[str] = None


# ── Health Reminder ───────────────────────────────────────────────────────────

class ReminderLog(BaseModel):
    id: str
    elderly_id: str
    reminder_type: str                  # "medication" | "meal" | "blood_pressure"
    scheduled_at: datetime
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DailyEmotionPoint(BaseModel):
    date: str
    emotion: EmotionLabel
    score: float
    message_count: int


class HealthTrendPoint(BaseModel):
    date: str
    medication_rate: float              # 0.0 ~ 1.0
    response_rate: float
    health_status: HealthStatus


class DashboardSummary(BaseModel):
    elderly: Elderly
    recent_emotion: list[DailyEmotionPoint]
    health_trend: list[HealthTrendPoint]
    unread_alerts: int
    last_7days_response_rate: float
    current_streak: int


class Alert(BaseModel):
    id: str
    elderly_id: str
    alert_type: str                     # "no_response" | "negative_emotion" | "medication_missed"
    message: str
    created_at: datetime
    is_read: bool = False


# ── Hobby Content ─────────────────────────────────────────────────────────────

class HobbyContent(BaseModel):
    content: str
    timestamp: str
