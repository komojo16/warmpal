"""
감정 분석 서비스
- 한국어 감정 분석: snunlp/KR-FinBert-SC 또는 monologg/koelectra-base-finetuned-sentiment
- fallback: 키워드 기반 규칙
"""
from __future__ import annotations

import re
from functools import lru_cache

from models.schemas import EmotionLabel

# 감정 위험 키워드 (즉시 가족 알림)
DANGER_KEYWORDS = [
    "죽고 싶", "죽을 것 같", "사라지고 싶", "힘들어 죽겠", "못 살겠",
    "가슴이 너무 아파", "쓰러졌", "넘어졌", "병원", "119", "구급",
    "숨이 막혀", "가슴 통증", "두통이 너무",
]

NEGATIVE_KEYWORDS = [
    "외로워", "슬퍼", "우울", "힘들어", "아파", "무서워", "걱정돼",
    "못 잤", "잠을 못", "밥도 못", "안 먹었", "기운이 없",
]

POSITIVE_KEYWORDS = [
    "좋아", "행복", "즐거워", "기뻐", "감사", "고마워", "맛있어",
    "잘 잤어", "건강해", "괜찮아", "재미있어", "웃었어",
]


@lru_cache(maxsize=1)
def _load_model():
    """transformers 모델 지연 로드 (선택적)"""
    try:
        from transformers import pipeline
        classifier = pipeline(
            "text-classification",
            model="snunlp/KR-FinBert-SC",
            top_k=None,
        )
        return classifier
    except Exception:
        return None


def _keyword_analysis(text: str) -> tuple[EmotionLabel, float]:
    text_lower = text.lower()

    for kw in DANGER_KEYWORDS:
        if kw in text_lower:
            return EmotionLabel.danger, 0.95

    neg_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)
    pos_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)

    if neg_count > pos_count:
        score = min(0.5 + neg_count * 0.1, 0.9)
        return EmotionLabel.negative, score
    elif pos_count > 0:
        score = min(0.5 + pos_count * 0.1, 0.95)
        return EmotionLabel.positive, score
    return EmotionLabel.neutral, 0.5


def analyze(text: str) -> tuple[EmotionLabel, float]:
    """
    반환: (EmotionLabel, confidence_score)
    """
    # 위험 키워드는 항상 먼저 체크
    for kw in DANGER_KEYWORDS:
        if kw in text:
            return EmotionLabel.danger, 0.95

    classifier = _load_model()
    if classifier is None:
        return _keyword_analysis(text)

    try:
        results = classifier(text[:512])[0]
        # KR-FinBert-SC label mapping
        label_map = {
            "LABEL_0": EmotionLabel.negative,
            "LABEL_1": EmotionLabel.neutral,
            "LABEL_2": EmotionLabel.positive,
            "negative": EmotionLabel.negative,
            "neutral": EmotionLabel.neutral,
            "positive": EmotionLabel.positive,
        }
        top = max(results, key=lambda x: x["score"])
        label = label_map.get(top["label"], EmotionLabel.neutral)
        return label, round(top["score"], 4)
    except Exception:
        return _keyword_analysis(text)


def aggregate_daily_emotion(emotions: list[tuple[EmotionLabel, float]]) -> tuple[EmotionLabel, float]:
    """하루 메시지들의 감정을 종합"""
    if not emotions:
        return EmotionLabel.neutral, 0.5

    # danger가 하나라도 있으면 danger
    for label, score in emotions:
        if label == EmotionLabel.danger:
            return EmotionLabel.danger, score

    scores = {
        EmotionLabel.positive: 0.0,
        EmotionLabel.neutral: 0.0,
        EmotionLabel.negative: 0.0,
    }
    for label, score in emotions:
        scores[label] += score

    dominant = max(scores, key=lambda k: scores[k])
    total = sum(scores.values())
    confidence = scores[dominant] / total if total > 0 else 0.5
    return dominant, round(confidence, 4)
