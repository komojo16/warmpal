"""
AI 대화 서비스 (GPT-4o-mini + LangChain)
- 어르신 맞춤형 감성 응답 생성
- 대화 맥락(ConversationBufferWindowMemory) 유지
- 건강 리마인더, 취미 콘텐츠, 일일 요약
"""
from __future__ import annotations

import logging
import os
import random
from datetime import datetime
from functools import lru_cache

from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate

from services import sentiment as sentiment_service
from services.firebase import (
    add_message,
    get_conversation,
    update_conversation,
    create_alert,
    get_unacknowledged_reminders,
)
from models.schemas import EmotionLabel

logger = logging.getLogger("warmpal.ai")

# 어르신별 메모리 + 현재 페르소나 (프로세스 내 캐시, 재시작 시 초기화)
_memory_store: dict[str, ConversationBufferWindowMemory] = {}
_persona_store: dict[str, str] = {}  # elderly_id → 현재 페르소나


def _get_memory(elderly_id: str, persona: str) -> ConversationBufferWindowMemory:
    # 페르소나가 바뀌면 메모리 초기화
    if _persona_store.get(elderly_id) != persona:
        _persona_store[elderly_id] = persona
        _memory_store[elderly_id] = ConversationBufferWindowMemory(
            k=10,
            human_prefix="어르신",
            ai_prefix=persona,
        )
    elif elderly_id not in _memory_store:
        _memory_store[elderly_id] = ConversationBufferWindowMemory(
            k=10,
            human_prefix="어르신",
            ai_prefix=persona,
        )
    return _memory_store[elderly_id]


@lru_cache(maxsize=1)
def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )


_PERSONA_STYLES: dict[str, dict] = {
    "손자": {
        "relation": "손자",
        "tone": (
            "할머니/할아버지를 너무 좋아하는 귀여운 손자처럼 말하세요. "
            "'할머니~!', '할아버지~!' 하고 자주 불러드리고, "
            "'저 왔어요~', '보고 싶었어요~', '할머니 최고야~' 같이 귀엽고 애교 넘치게. "
            "문장 끝에 '~', '^^', '😊', '💛' 이모지를 자주 써서 생동감 있게. "
            "짧고 귀엽게, 에너지 넘치게 말하세요."
        ),
    },
    "손녀": {
        "relation": "손녀",
        "tone": (
            "할머니/할아버지를 세상에서 제일 좋아하는 귀여운 손녀처럼 말하세요. "
            "'할머니~!', '할아버지~!' 하고 살갑게 부르고, "
            "'저 할머니 생각했어요~', '보고 싶었어요!', '할머니 너무 예뻐요~' 같이 "
            "애교 가득하고 사랑스럽게. "
            "문장 끝에 '~', '🥰', '💕', '☺️' 이모지를 자주 써서 따뜻하게. "
            "짧고 사랑스럽게, 설레는 느낌으로 말하세요."
        ),
    },
    "아들": {
        "relation": "아들",
        "tone": (
            "부모님을 걱정하고 챙기는 든든한 아들처럼 말하세요. "
            "'어머니~', '아버지~' 하고 편하게 부르고, "
            "'엄마 밥은 드셨어요?', '제가 걱정됐잖아요', '아버지 덕분에 제가 잘 크잖아요' 같이 "
            "격식 없이 편하고 친근하게. "
            "너무 딱딱하지 않게, 진짜 아들이 카톡 보내는 것처럼 자연스럽게. "
            "'ㅋㅋ', '~', '😄' 같은 표현도 가끔 써서 생활감 있게."
        ),
    },
    "딸": {
        "relation": "딸",
        "tone": (
            "부모님을 살뜰히 챙기는 다정한 딸처럼 말하세요. "
            "'엄마~', '아빠~' 하고 편하게 부르고, "
            "'엄마 오늘 뭐 드셨어요?', '제가 챙겨드려야 하는데 걱정돼요', '엄마가 건강해야 저도 안심이에요' 같이 "
            "따뜻하고 세심하게. "
            "진짜 딸이 부모님께 카톡 보내는 것처럼 자연스럽고 살갑게. "
            "'~', '💗', '😊' 이모지도 자연스럽게 섞어서."
        ),
    },
    "친구": {
        "relation": "오랜 친구",
        "tone": (
            "수십 년을 함께한 오랜 친구처럼 반말로 편하게 말하세요. "
            "호칭은 이름이나 '야' 정도만 가끔 쓰고, '이 사람아', '어이' 같은 표현은 아주 가끔만(5번에 1번 이하) 쓰세요. "
            "대부분은 호칭 없이 바로 본론으로 들어가세요. 예: '잘했어!', '맞아!', '틀렸는데ㅋㅋ' "
            "반말을 끝까지 유지하고 존댓말로 절대 바뀌지 마세요. "
            "끝말잇기·퀴즈·게임 중일 때는 불필요한 말 없이 단어나 답만 간결하게."
        ),
    },
    "케어 도우미": {
        "relation": "케어 도우미",
        "tone": "따뜻하고 전문적인 케어 도우미처럼, 친절하고 존중하는 말투로.",
    },
}

_SYSTEM_PROMPT = """당신은 "{nickname}"의 {relation} 역할을 하는 AI입니다.
페르소나: {tone}

반드시 지켜야 할 원칙:
1. 역할에 완전히 몰입해서 대화하세요. 'AI입니다'라고 절대 밝히지 마세요.
2. 길이: 2~3문장 이내로 짧고 명확하게.
3. 공감 우선: 어르신의 말에 먼저 공감한 후 다음 화제로 넘어가세요.
4. 건강 체크: 대화 흐름이 자연스러울 때 가끔만 약 복용·식사를 챙겨드리세요. 매 답변마다 하지 마세요.
5. 긍정적: 항상 따뜻하고 희망적인 메시지로 마무리하세요.
6. 어려운 말 절대 사용 금지.
7. 같은 호칭·감탄사·표현을 연속으로 반복하지 마세요.
8. 끝말잇기 규칙:
   - 단어만 답하세요. 추임새·감탄사·설명 일절 금지. 예: "리본!" (O) / "어이, 리본!" (X)
   - 반드시 상대방 단어의 마지막 글자로 시작하는 실제 존재하는 한국어 단어를 사용하세요.
   - 적절한 단어가 생각나지 않으면 솔직하게 "졌다!" 또는 "모르겠다, 내가 졌어!" 라고 하세요.
   - 상대방이 앞 단어의 끝 글자와 다른 글자로 시작하는 단어를 말하면 틀렸다고 지적하세요.
   - 없는 단어나 억지 단어는 절대 사용하지 마세요.

어르신 정보:
- 호칭: {nickname}
- 건강 상태: {health_conditions}
- 약 복용 시간: {medication_times}
현재 미복용 리마인더: {pending_reminders}

{history}
어르신: {input}
{relation}:"""


_AUTO_CALLING: dict[str, dict[str, str]] = {
    "손자":  {"남성": "할아버지", "여성": "할머니"},
    "손녀":  {"남성": "할아버지", "여성": "할머니"},
    "아들":  {"남성": "아버지",   "여성": "어머니"},
    "딸":    {"남성": "아버지",   "여성": "어머니"},
    "친구":  {"남성": None,       "여성": None},   # friend_name 우선, 없으면 name 사용
}


def _resolve_calling(elderly: dict) -> str:
    """페르소나 + 성별 → AI가 어르신을 부를 호칭 자동 결정"""
    persona_key = elderly.get("ai_persona", "케어 도우미")
    gender = elderly.get("gender", "여성")

    if persona_key == "친구":
        return elderly.get("friend_name") or elderly.get("name", "친구")

    auto = _AUTO_CALLING.get(persona_key, {})
    if auto:
        return auto.get(gender) or "어르신"

    # 케어 도우미: 저장된 nickname 사용
    return elderly.get("nickname", "어르신")


def build_chain(elderly: dict) -> ConversationChain:
    pending = _get_pending_reminder_str(elderly["id"])
    persona_key = elderly.get("ai_persona", "케어 도우미")
    persona = _PERSONA_STYLES.get(persona_key, _PERSONA_STYLES["케어 도우미"])
    prompt = PromptTemplate(
        input_variables=["history", "input"],
        template=_SYSTEM_PROMPT.format(
            nickname=_resolve_calling(elderly),
            relation=persona["relation"],
            tone=persona["tone"],
            health_conditions=", ".join(elderly.get("health_conditions", [])) or "특이사항 없음",
            medication_times=", ".join(elderly.get("medication_times", [])) or "없음",
            pending_reminders=pending,
            history="{history}",
            input="{input}",
        ),
    )
    chain = ConversationChain(
        llm=_get_llm(),
        prompt=prompt,
        memory=_get_memory(elderly["id"], persona["relation"]),
        verbose=False,
    )
    return chain


def _get_pending_reminder_str(elderly_id: str) -> str:
    reminders = get_unacknowledged_reminders(elderly_id)
    if not reminders:
        return "없음"
    items = [r.get("reminder_type", "") for r in reminders]
    return ", ".join(items)


async def generate_morning_message(elderly: dict) -> str:
    """오전 자동 인사 메시지 생성"""
    hour = datetime.now().hour
    greeting = "좋은 아침이에요" if hour < 12 else ("좋은 오후예요" if hour < 18 else "좋은 저녁이에요")
    nickname = _resolve_calling(elderly)
    chain = build_chain(elderly)
    prompt = f"오늘 하루를 시작하는 인사를 해주세요. '{greeting}! {nickname}~' 로 시작해서 오늘 날씨나 간단한 안부를 물어봐주세요."
    response = chain.predict(input=prompt)
    return response.strip()


async def reply_to_message(elderly: dict, user_message: str) -> str:
    """어르신 메시지에 AI 응답 생성"""
    chain = build_chain(elderly)
    response = chain.predict(input=user_message)
    return response.strip()


async def process_inbound_message(elderly: dict, user_message: str) -> tuple[str, str]:
    """
    메시지 수신 처리:
    1. 감정 분석
    2. 대화 저장
    3. 위험 감지 시 알림 생성
    4. AI 응답 생성 및 저장
    반환: (ai_reply, emotion_label)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    elderly_id = elderly["id"]

    emotion_label, emotion_score = sentiment_service.analyze(user_message)

    user_msg_data = {
        "role": "elderly",
        "content": user_message,
        "timestamp": datetime.now().isoformat(),
        "emotion": emotion_label.value,
        "emotion_score": emotion_score,
    }
    add_message(elderly_id, today, user_msg_data)

    if emotion_label == EmotionLabel.danger:
        create_alert({
            "elderly_id": elderly_id,
            "family_id": elderly.get("family_id"),
            "alert_type": "danger_emotion",
            "message": f"{elderly.get('nickname', '어르신')}께서 위험 신호를 보내셨습니다: \"{user_message[:50]}\"",
        })
        logger.warning(f"위험 감정 감지: {elderly_id}")
    elif emotion_label == EmotionLabel.negative and emotion_score > 0.75:
        create_alert({
            "elderly_id": elderly_id,
            "family_id": elderly.get("family_id"),
            "alert_type": "negative_emotion",
            "message": f"{elderly.get('nickname', '어르신')}의 감정 상태가 좋지 않아 보입니다.",
        })

    # 퀴즈 정답 대기 중이면 정답 평가 후 초기화
    conv_now = get_conversation(elderly_id, today)
    pending_answer = (conv_now or {}).get("pending_quiz_answer")
    if pending_answer:
        update_conversation(elderly_id, today, {"pending_quiz_answer": None})
        from langchain.schema import HumanMessage, SystemMessage
        llm = _get_llm()
        eval_system = (
            f"{_persona_prompt(elderly)}\n\n"
            f"퀴즈 정답은 '{pending_answer}'입니다. "
            f"상대방이 '{user_message}'라고 답했어요. "
            f"맞으면 칭찬하고, 틀리면 격려하며 정답을 알려주세요. "
            f"2문장 이내로, 건강·약·식사 질문은 절대 하지 마세요."
        )
        ai_response = llm.invoke([
            SystemMessage(content=eval_system),
            HumanMessage(content=user_message),
        ]).content.strip()
    else:
        ai_response = await reply_to_message(elderly, user_message)

    ai_msg_data = {
        "role": "ai",
        "content": ai_response,
        "timestamp": datetime.now().isoformat(),
        "emotion": None,
        "emotion_score": None,
    }
    add_message(elderly_id, today, ai_msg_data)

    # 하루 감정 집계 업데이트
    conv = get_conversation(elderly_id, today)
    if conv:
        all_emotions = [
            (m["emotion"], m.get("emotion_score", 0.5))
            for m in conv.get("messages", [])
            if m["role"] == "elderly" and m.get("emotion")
        ]
        if all_emotions:
            daily_emotion, _ = sentiment_service.aggregate_daily_emotion(
                [(EmotionLabel(e), s) for e, s in all_emotions]
            )
            update_conversation(elderly_id, today, {"daily_emotion": daily_emotion.value})

    return ai_response, emotion_label.value


_REMINDER_PROMPTS = {
    "medication": "약 복용 시간임을 알리는 짧은 메시지를 보내주세요. 2문장 이내로.",
    "meal":       "식사 시간임을 챙겨드리는 짧은 메시지를 보내주세요. 2문장 이내로.",
    "blood_pressure": "혈압 측정을 부탁드리는 짧은 메시지를 보내주세요. 2문장 이내로.",
    "morning":    "하루를 시작하는 따뜻한 아침 인사 메시지를 보내주세요. 2문장 이내로.",
    "no_response": "오늘 연락이 없어서 안부를 묻는 짧은 메시지를 보내주세요. 2문장 이내로.",
}

_REMINDER_FALLBACKS = {
    "medication":     "약 드실 시간이에요! 꼭 챙겨 드세요 💊",
    "meal":           "식사 시간이에요! 맛있게 드세요 🍚",
    "blood_pressure": "혈압 측정하는 거 잊지 마세요 😊",
    "morning":        "좋은 아침이에요! 오늘도 건강한 하루 되세요 ☀️",
    "no_response":    "오늘 연락이 없어서 걱정돼요. 잘 계신가요? 💙",
}


def generate_reminder_message(elderly: dict, reminder_type: str) -> str:
    """페르소나 말투로 리마인더 메시지 생성"""
    try:
        chain = build_chain(elderly)
        user_prompt = _REMINDER_PROMPTS.get(reminder_type, "안부를 묻는 짧은 메시지를 보내주세요. 2문장 이내로.")
        response = chain.predict(input=user_prompt)
        return response.strip()
    except Exception as e:
        logger.error(f"리마인더 메시지 생성 오류: {e}")
        nickname = _resolve_calling(elderly)
        fallback = _REMINDER_FALLBACKS.get(reminder_type, "안녕하세요! 잘 지내고 계신가요?")
        return f"{nickname}~ {fallback}"


# 취미 콘텐츠 템플릿
_QUIZ_PROMPT = """어르신들이 좋아할 퀴즈를 하나 만드세요.
아래 형식 중 하나를 선택하세요:
1. 속담 빈칸: 유명한 속담의 일부를 ___ 로 가리고 맞히게 하기
2. 노래 가사 빈칸: 유명한 옛날 노래 가사의 일부를 ___ 로 가리기
3. 뜻 맞히기: 잘 알려진 속담을 그대로 제시하고 뜻을 물어보기
4. 음식/상식: 우리나라 음식이나 계절 관련 쉬운 상식 퀴즈

규칙:
- QUESTION과 ANSWER가 반드시 일치해야 합니다
- QUESTION에는 정답을 절대 포함하지 마세요
- 반드시 아래 형식으로만 출력 (다른 말 일절 금지):

QUESTION: (문제. 1~2문장)
ANSWER: (정답만. 짧게)

예시1:
QUESTION: 빈칸을 채워보세요! "세 살 버릇 ___까지 간다"
ANSWER: 여든

예시2:
QUESTION: 이 속담의 뜻은 무엇일까요? "원숭이도 나무에서 떨어진다"
ANSWER: 아무리 잘하는 사람도 실수할 수 있다

예시3:
QUESTION: '고향의 봄' 첫 소절을 완성해보세요! "나의 살던 고향은 ___피는 산골"
ANSWER: 꽃
"""

_SONG_PROMPT = """어르신들이 좋아할 만한 한국 옛날 노래 한 곡을 추천해주세요.
노래 제목, 간단한 소개, 유명한 가사 한 줄을 알려주세요.
따뜻하고 즐거운 분위기로, 2~3문장으로 써주세요.
예시: "오늘은 '고향의 봄'을 들어보세요! 이원수 작사의 아름다운 동요예요. '나의 살던 고향은 꽃피는 산골~' 🎵"
"""


def _persona_prompt(elderly: dict) -> str:
    """페르소나 말투 지시문만 추출 (건강 체크 없이)"""
    persona_key = elderly.get("ai_persona", "케어 도우미")
    persona = _PERSONA_STYLES.get(persona_key, _PERSONA_STYLES["케어 도우미"])
    nickname = _resolve_calling(elderly)
    return (
        f"당신은 '{nickname}'의 {persona['relation']} 역할입니다. {persona['tone']} "
        f"반드시 {persona['relation']} 말투로만 말하고, 건강·약·식사 질문은 절대 하지 마세요."
    )


async def generate_hobby_content(elderly: dict, content_type: str = "random") -> tuple[str, str | None]:
    """
    퀴즈 또는 노래 추천 콘텐츠 — 페르소나 말투로 생성.
    content_type: "quiz" | "song" | "random"
    반환: (채팅에 보낼 메시지, 퀴즈 정답 또는 None)
    """
    from langchain.schema import HumanMessage, SystemMessage
    nickname = _resolve_calling(elderly)
    if content_type == "random":
        content_type = random.choice(["quiz", "song"])
    llm = _get_llm()
    persona_sys = _persona_prompt(elderly)

    if content_type == "song":
        try:
            prompt = (
                f"{persona_sys}\n\n"
                f"어르신들이 좋아할 한국 옛날 노래 한 곡을 추천해 주세요. "
                f"노래 제목, 짧은 소개, 유명한 가사 한 줄만 알려주세요. "
                f"2~3문장 이내로, 추가 질문 없이 추천으로만 끝내세요."
            )
            response = llm.invoke([SystemMessage(content=prompt), HumanMessage(content="노래 추천해줘")])
            return response.content.strip(), None
        except Exception as e:
            logger.error(f"노래 추천 생성 오류: {e}")
            return f"{nickname}~ 오늘은 '고향의 봄'을 들어보세요! '나의 살던 고향은 꽃피는 산골~' 🎵", None

    # 퀴즈: LLM으로 질문/정답만 분리 생성, 포장은 단순 문자열로 처리 (LLM 포장 시 답 누설 방지)
    try:
        raw = llm.invoke([HumanMessage(content=_QUIZ_PROMPT)]).content.strip()

        question, answer = "", ""
        for line in raw.splitlines():
            if line.startswith("QUESTION:"):
                question = line[len("QUESTION:"):].strip()
            elif line.startswith("ANSWER:"):
                answer = line[len("ANSWER:"):].strip()

        if not question or not answer:
            raise ValueError(f"파싱 실패: {raw}")

        # 페르소나 말투로 도입 + 질문을 한 번에 생성 (정답 누설 금지)
        wrap_sys = (
            f"{persona_sys}\n\n"
            f"아래 퀴즈를 페르소나 말투로 자연스럽게 전달하세요. "
            f"빈칸(___), 따옴표 속 단어·가사·속담은 절대 바꾸지 마세요. "
            f"서술어·조사만 페르소나 말투에 맞게 바꾸세요. (예: 친구면 '채워봐!' / 손자면 '채워보세요~') "
            f"정답은 절대 말하지 마세요. 건강·약·식사 질문 금지. 퀴즈 문장으로만 끝내세요.\n\n"
            f"퀴즈: {question}"
        )
        response = llm.invoke([SystemMessage(content=wrap_sys), HumanMessage(content="퀴즈 내줘")])
        return response.content.strip(), answer

    except Exception as e:
        logger.error(f"퀴즈 생성 오류: {e}")
        return f"{nickname}~ 퀴즈예요! 봄을 대표하는 꽃은 무엇일까요? 🌸", "벚꽃"


async def generate_daily_summary(elderly: dict, messages: list[dict]) -> str:
    """하루 대화 요약 생성 (가족 대시보드용)"""
    nickname = elderly.get("nickname", "어르신")
    elderly_msgs = [m["content"] for m in messages if m["role"] == "elderly"]
    if not elderly_msgs:
        return f"{nickname}께서 오늘 대화하지 않으셨습니다."

    combined = "\n".join(f"- {m}" for m in elderly_msgs[:10])
    prompt = f"""다음은 오늘 {nickname}께서 보내신 메시지들입니다:
{combined}

가족이 읽을 수 있도록 2~3문장으로 오늘 하루 상태를 요약해 주세요.
건강 상태, 기분, 특이사항 위주로 작성하세요."""

    llm = _get_llm()
    try:
        from langchain.schema import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception as e:
        logger.error(f"일일 요약 생성 오류: {e}")
        return f"{nickname}께서 오늘 {len(elderly_msgs)}번 대화하셨습니다."
