"""
카카오톡 챗봇 스킬 서버 라우터

카카오 i 오픈빌더(채널 챗봇)의 "스킬"이 사용자 발화를 이 엔드포인트로 전달하고,
우리는 카카오 스킬 응답(JSON v2.0) 포맷으로 답을 돌려준다.

연동 흐름 (봇이 "먼저 다가가는" 자동연결 방식)
  1. [오픈빌더] 카카오톡 채널 + 챗봇 생성 → 폴백 블록 스킬을 POST {BASE_URL}/kakao/skill 로 설정
  2. [가족] 대시보드에서 어르신별 '카카오 연결'(채널 추가 링크 + 6자리 연결코드 + QR)을 어르신에게 전달
  3. [어르신] 링크로 채널을 추가하고 연결코드만 한 번 보내면(또는 가족이 대신 입력) →
     봇이 연결코드로 어르신을 자동 인식하여 kakao_user_id 를 저장하고 이름을 부르며 먼저 인사
  4. 이후: process_inbound_message 로 기존 웹 채팅과 동일하게 AI 응답·감정분석·퀴즈 처리

주의
  - 카카오 스킬 서버는 응답을 5초 안에 돌려줘야 한다. GPT-4o-mini는 보통 1~3초라 동기 처리로 충분하지만,
    지연 시 콜백(useCallback) 방식이 필요할 수 있다.
  - 카카오 채널은 봇이 사용자에게 먼저 '친구 추가'를 걸 수 없다(정책). 그래서 가족이 전달한 링크로
    어르신이 채널을 추가하게 하고, 연결코드로 누구인지 자동 식별해 "봇이 먼저 인사"하는 경험을 만든다.
  - 연결코드는 가족이 어르신에게 전달하므로 어르신은 전화번호를 직접 입력할 필요가 없다
    (전화번호 입력도 보조 수단으로 계속 지원).
  - 카카오는 능동(push) 발송에 별도 심사(친구톡/알림톡)가 필요하므로, 아침 인사·선제 메시지 등
    스케줄러 메시지는 기존처럼 Firestore에 저장되어 웹 채팅에서 확인된다.
"""
import logging
import os
import re

from fastapi import APIRouter, Request, Header
from fastapi.responses import JSONResponse

from services.firebase import (
    get_elderly_by_phone,
    get_elderly_by_kakao_id,
    get_elderly_by_connect_code,
    update_elderly,
    update_response_streak,
    update_conversation,
    add_message,
    now_utc,
)
from services.ai_service import (
    process_inbound_message,
    generate_hobby_content,
    _resolve_calling,
)
from datetime import datetime

logger = logging.getLogger("warmpal.kakao")
router = APIRouter(prefix="/kakao", tags=["KakaoTalk"])

# 선택적 공유 시크릿 — 설정 시 오픈빌더 스킬 헤더(X-Bot-Secret)와 대조해 외부 호출 차단
_BOT_SECRET = os.getenv("KAKAO_BOT_SECRET", "")


# ── 카카오 응답 포맷 헬퍼 ──────────────────────────────────────────────────────

_QUICK_REPLIES = [
    {"label": "🧩 퀴즈", "action": "message", "messageText": "퀴즈 내줘"},
    {"label": "🎵 노래 추천", "action": "message", "messageText": "노래 추천해줘"},
]


def _skill_text(text: str, with_quick_replies: bool = True) -> JSONResponse:
    """카카오 스킬 v2.0 simpleText 응답"""
    template: dict = {"outputs": [{"simpleText": {"text": text}}]}
    if with_quick_replies:
        template["quickReplies"] = _QUICK_REPLIES
    return JSONResponse({"version": "2.0", "template": template})


# ── 연결코드 자동연결(최초 연결, 주 경로) ─────────────────────────────────────────

def _extract_connect_codes(body: dict, utterance: str) -> list[str]:
    """스킬 페이로드의 파라미터 + 발화에서 연결코드 후보(4~8자리 숫자)를 추출"""
    candidates: list[str] = []
    user_request = body.get("userRequest", {}) or {}
    action = body.get("action", {}) or {}

    # 1) 오픈빌더 파라미터로 코드가 전달된 경우 (블록·엔트리 파라미터)
    for src in (action.get("params"), action.get("detailParams"), user_request.get("params")):
        if not isinstance(src, dict):
            continue
        for key in ("code", "connect_code", "connectCode", "연결코드"):
            val = src.get(key)
            if isinstance(val, dict):          # detailParams 는 {"value": ...} 형태
                val = val.get("value") or val.get("origin")
            if val:
                candidates.append(re.sub(r"\D", "", str(val)))

    # 2) 발화에서 4~8자리 숫자 추출 (어르신이 코드만 보낸 경우)
    candidates += re.findall(r"\d{4,8}", utterance)
    # 중복 제거(순서 유지)
    seen: set[str] = set()
    return [c for c in candidates if c and not (c in seen or seen.add(c))]


def _try_link_by_connect_code(kakao_user_id: str, body: dict, utterance: str) -> dict | None:
    """연결코드로 어르신을 찾아 kakao_user_id 연결. 성공 시 elderly 반환."""
    for code in _extract_connect_codes(body, utterance):
        elderly = get_elderly_by_connect_code(code)
        if elderly:
            update_elderly(elderly["id"], {"kakao_user_id": kakao_user_id})
            logger.info(f"카카오 연결(코드): kakao_user={kakao_user_id} → elderly={elderly['id']}")
            return elderly
    return None


# ── 전화번호 인증(보조 연결) ────────────────────────────────────────────────────

def _phone_candidates(raw: str) -> list[str]:
    """입력 전화번호를 등록 포맷(+82…)과 국내 포맷(010…) 등으로 정규화한 후보 목록"""
    digits = re.sub(r"\D", "", raw)
    candidates = {raw.strip(), digits}
    if digits.startswith("82"):
        candidates.add("+" + digits)            # +821012345678
        candidates.add("0" + digits[2:])        # 01012345678
    elif digits.startswith("0"):
        candidates.add(digits)                  # 01012345678
        candidates.add("+82" + digits[1:])      # +821012345678
    return [c for c in candidates if c]


def _looks_like_phone(text: str) -> bool:
    digits = re.sub(r"\D", "", text)
    return 9 <= len(digits) <= 13 and bool(re.fullmatch(r"[\d\-\+\s()]+", text.strip()))


def _try_link_by_phone(kakao_user_id: str, utterance: str) -> dict | None:
    """발화를 전화번호로 보고 어르신을 찾아 kakao_user_id 를 연결. 성공 시 elderly 반환."""
    for candidate in _phone_candidates(utterance):
        elderly = get_elderly_by_phone(candidate)
        if elderly:
            update_elderly(elderly["id"], {"kakao_user_id": kakao_user_id})
            logger.info(f"카카오 연결 완료: kakao_user={kakao_user_id} → elderly={elderly['id']}")
            return elderly
    return None


# ── 취미 콘텐츠(퀴즈/노래) 빠른 명령 ────────────────────────────────────────────

async def _handle_hobby(elderly: dict, content_type: str) -> str:
    """웹 채팅 /chat/hobby 와 동일하게 콘텐츠 생성 + 저장 (퀴즈 정답은 pending 으로 보관)"""
    content, quiz_answer = await generate_hobby_content(elderly, content_type)
    today = datetime.now().strftime("%Y-%m-%d")
    add_message(elderly["id"], today, {
        "role": "ai",
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "emotion": None,
        "emotion_score": None,
    })
    if quiz_answer:
        update_conversation(elderly["id"], today, {"pending_quiz_answer": quiz_answer})
    return content


# ── 스킬 웹훅 ────────────────────────────────────────────────────────────────────

@router.post("/skill")
async def kakao_skill(request: Request, x_bot_secret: str | None = Header(default=None)):
    """카카오 i 오픈빌더 스킬 서버 엔드포인트"""
    if _BOT_SECRET and x_bot_secret != _BOT_SECRET:
        return _skill_text("인증되지 않은 요청입니다.", with_quick_replies=False)

    try:
        body = await request.json()
    except Exception:
        return _skill_text("요청을 이해하지 못했어요. 다시 보내주세요.", with_quick_replies=False)

    user_request = body.get("userRequest", {}) or {}
    utterance = (user_request.get("utterance") or "").strip()
    kakao_user_id = ((user_request.get("user") or {}).get("id")) or ""

    if not kakao_user_id:
        return _skill_text("사용자 정보를 확인할 수 없어요.", with_quick_replies=False)

    # 1) 이미 연결된 어르신 조회
    elderly = get_elderly_by_kakao_id(kakao_user_id)

    # 2) 미연결 → 연결코드(주 경로) → 전화번호(보조) → 안내
    if not elderly:
        elderly = _try_link_by_connect_code(kakao_user_id, body, utterance)
        if not elderly and _looks_like_phone(utterance):
            elderly = _try_link_by_phone(kakao_user_id, utterance)

        if elderly:
            calling = _resolve_calling(elderly)
            return _skill_text(
                f"{calling}~ 반가워요! 💛 warmpal이에요.\n"
                f"이제부터 매일 이야기 나눠요. 오늘 하루는 어떠셨어요?"
            )

        # 코드/번호가 아니거나 매칭 실패 → 연결 안내
        return _skill_text(
            "안녕하세요, warmpal이에요 💛\n"
            "처음 오셨네요! 가족분이 알려주신 6자리 연결번호를 보내주세요.\n"
            "(연결번호가 없으면 등록하신 전화번호를 입력해 주세요. 예: 010-1234-5678)",
            with_quick_replies=False,
        )

    # 3) 연결된 어르신 — 정상 대화 처리
    elderly_id = elderly["id"]
    update_response_streak(elderly_id)
    update_elderly(elderly_id, {"last_response_at": now_utc()})

    try:
        # 빠른 명령: 퀴즈 / 노래 추천
        if "퀴즈" in utterance:
            reply = await _handle_hobby(elderly, "quiz")
        elif "노래" in utterance and ("추천" in utterance or utterance == "노래"):
            reply = await _handle_hobby(elderly, "song")
        else:
            reply, _emotion = await process_inbound_message(elderly, utterance)
    except Exception as e:
        logger.error(f"카카오 메시지 처리 오류 elderly={elderly_id}: {e}")
        reply = "잠시 후 다시 말씀해 주시겠어요? 제가 잠깐 멍했네요 😅"

    return _skill_text(reply)
