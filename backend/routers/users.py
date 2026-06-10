"""가족/어르신 사용자 관리 API (2주차)"""
import hashlib
import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models.schemas import (
    ElderlyCreate, ElderlyUpdate, Elderly,
    FamilyCreate, FamilyLogin, Family, TokenResponse,
)
from services import firebase as db

router = APIRouter(prefix="/users", tags=["Users"])
security = HTTPBearer()

SECRET_KEY = os.getenv("APP_SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24 * 7  # 7일


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _create_token(family_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {"sub": family_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_family(creds: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        family_id = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
    family = db.get_family_by_id(family_id)
    if not family:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    return family


# ── Family 회원가입/로그인 ──────────────────────────────────────────────────────

@router.post("/family/register", response_model=TokenResponse)
def register_family(body: FamilyCreate):
    existing = db.get_family_by_email(body.email)
    if existing:
        raise HTTPException(status_code=409, detail="이미 등록된 이메일입니다.")
    family = db.create_family({
        "name": body.name,
        "email": body.email,
        "password_hash": _hash_password(body.password),
    })
    return TokenResponse(access_token=_create_token(family["id"]))


@router.post("/family/login", response_model=TokenResponse)
def login_family(body: FamilyLogin):
    family = db.get_family_by_email(body.email)
    if not family or family.get("password_hash") != _hash_password(body.password):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
    return TokenResponse(access_token=_create_token(family["id"]))


@router.get("/family/me", response_model=Family)
def get_me(family: dict = Depends(get_current_family)):
    return Family(
        id=family["id"],
        name=family["name"],
        email=family["email"],
        created_at=family["created_at"],
    )


# ── Elderly CRUD ──────────────────────────────────────────────────────────────

@router.post("/elderly", response_model=dict)
def register_elderly(body: ElderlyCreate, family: dict = Depends(get_current_family)):
    data = body.model_dump()
    data["family_id"] = family["id"]
    elderly = db.create_elderly(data)
    return {"id": elderly["id"], "message": "어르신이 등록되었습니다."}


@router.get("/elderly", response_model=list[dict])
def list_elderly(family: dict = Depends(get_current_family)):
    return db.get_elderly_by_family(family["id"])


@router.get("/elderly/{elderly_id}", response_model=dict)
def get_elderly(elderly_id: str, family: dict = Depends(get_current_family)):
    elderly = db.get_elderly_by_id(elderly_id)
    if not elderly or elderly.get("family_id") != family["id"]:
        raise HTTPException(status_code=404, detail="어르신을 찾을 수 없습니다.")
    return elderly


@router.get("/elderly/{elderly_id}/kakao-link", response_model=dict)
def get_kakao_link(elderly_id: str, family: dict = Depends(get_current_family)):
    """카카오톡 봇 자동연결용 정보(연결코드 + 채널 추가 링크) 반환"""
    elderly = db.get_elderly_by_id(elderly_id)
    if not elderly or elderly.get("family_id") != family["id"]:
        raise HTTPException(status_code=404, detail="어르신을 찾을 수 없습니다.")

    code = db.get_or_create_connect_code(elderly_id)
    public_id = os.getenv("KAKAO_CHANNEL_PUBLIC_ID", "").strip()
    add_url = f"http://pf.kakao.com/{public_id}" if public_id else ""
    chat_url = f"http://pf.kakao.com/{public_id}/chat" if public_id else ""
    return {
        "connect_code": code,
        "channel_public_id": public_id,
        "add_url": add_url,
        "chat_url": chat_url,
        "linked": bool(elderly.get("kakao_user_id")),
    }


@router.patch("/elderly/{elderly_id}")
def update_elderly(elderly_id: str, body: ElderlyUpdate, family: dict = Depends(get_current_family)):
    elderly = db.get_elderly_by_id(elderly_id)
    if not elderly or elderly.get("family_id") != family["id"]:
        raise HTTPException(status_code=404, detail="어르신을 찾을 수 없습니다.")
    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    db.update_elderly(elderly_id, update_data)
    return {"message": "업데이트되었습니다."}


@router.delete("/elderly/{elderly_id}")
def delete_elderly(elderly_id: str, family: dict = Depends(get_current_family)):
    elderly = db.get_elderly_by_id(elderly_id)
    if not elderly or elderly.get("family_id") != family["id"]:
        raise HTTPException(status_code=404, detail="어르신을 찾을 수 없습니다.")
    db.get_db().collection("elderly").document(elderly_id).delete()
    return {"message": "삭제되었습니다."}
