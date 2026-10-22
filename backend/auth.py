"""Opaque cookie sessions; no tokens or password hashes in API JSON."""
from datetime import timedelta
import hashlib
import os
import re
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pwdlib import PasswordHash
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth_schemas import AuthUserResponse, LoginRequest, SignupRequest
from .database import get_db
from .db_models import AuthSession, User, utc_now

COOKIE_NAME = "smartenergy_session"
password_hasher = PasswordHash.recommended()
# Unknown accounts still execute the same password verifier work.
DUMMY_HASH = password_hasher.hash(secrets.token_urlsafe(32))
router = APIRouter(prefix="/auth", tags=["authentication"])


def allowed_origins():
    return [o.strip().rstrip("/") for o in os.getenv("SMARTENERGY_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:8080").split(",") if o.strip() and o.strip() != "*"]


def secure_cookie():
    value = os.getenv("SMARTENERGY_COOKIE_SECURE", "false").lower()
    if value not in ("true", "false"):
        raise ValueError("SMARTENERGY_COOKIE_SECURE must be true or false")
    return value == "true"


def session_hours():
    hours = int(os.getenv("SMARTENERGY_SESSION_HOURS", "24"))
    if not 1 <= hours <= 720:
        raise ValueError("SMARTENERGY_SESSION_HOURS must be between 1 and 720")
    return hours


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hasher.verify(password, encoded)
    except Exception:
        # Malformed legacy hashes are invalid credentials, never a login bypass.
        return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def clear_cookie(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=secure_cookie(), samesite="lax")


def unauthorized():
    response = Response()
    clear_cookie(response)
    return HTTPException(401, "Session expired or account unavailable. Sign in again.",
                         headers={"Set-Cookie": response.headers["set-cookie"], "Cache-Control": "no-store"})


def csrf_guard(request: Request, csrf: str | None = Header(default=None, alias="X-SmartEnergy-CSRF")):
    # Non-simple header forces a CORS preflight. Explicit Origin checking also
    # rejects same-site but untrusted browser origins (including other ports).
    if csrf != "1":
        raise HTTPException(403, "Authentication request requires CSRF header")
    origin = request.headers.get("origin")
    if origin is not None and origin not in [*allowed_origins(), str(request.base_url).rstrip("/")]:
        raise HTTPException(403, "Authentication request origin is not allowed")


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME, "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise unauthorized()
    row = db.execute(select(AuthSession, User).join(User).where(AuthSession.token_hash == token_digest(token))).first()
    if row is None:
        raise unauthorized()
    session, user = row
    if not user.is_active:
        db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
        db.commit()
        raise unauthorized()
    if session.expires_at <= utc_now():
        db.delete(session)
        db.commit()
        raise unauthorized()
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "ADMIN":
        raise HTTPException(403, "Administrator access required")
    return user


def establish_session(request: Request, response: Response, db: Session, user: User):
    secure = secure_cookie()
    old = request.cookies.get(COOKIE_NAME)
    if old:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == token_digest(old)))
    token = secrets.token_urlsafe(32)
    now = utc_now()
    seconds = session_hours() * 3600
    db.add(AuthSession(user_id=user.id, token_hash=token_digest(token), created_at=now,
                       expires_at=now + timedelta(seconds=seconds)))
    db.commit()
    response.set_cookie(COOKIE_NAME, token, max_age=seconds, expires=seconds,
                        path="/", httponly=True, secure=secure, samesite="lax")


@router.post("/signup", response_model=AuthUserResponse, status_code=201, dependencies=[Depends(csrf_guard)])
def signup(body: SignupRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    if db.scalar(select(User.id).where(func.lower(func.trim(User.email)) == body.email)) is not None:
        raise HTTPException(409, "An account with this email already exists")
    user = User(email=body.email, password_hash=hash_password(body.password.get_secret_value()),
                full_name=body.full_name, role="USER", is_active=True)
    try:
        db.add(user)
        db.flush()
        establish_session(request, response, db, user)
    except IntegrityError:
        db.rollback()
        if db.scalar(select(User.id).where(func.lower(func.trim(User.email)) == body.email)) is not None:
            raise HTTPException(409, "An account with this email already exists") from None
        raise HTTPException(503, "Unable to establish authentication session") from None
    return user


@router.post("/login", response_model=AuthUserResponse, dependencies=[Depends(csrf_guard)])
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(func.trim(User.email)) == body.email))
    valid = verify_password(body.password.get_secret_value(), user.password_hash if user else DUMMY_HASH)
    if not valid or user is None or not user.is_active:
        if user is not None and not user.is_active:
            db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
            db.commit()
        raise HTTPException(401, "Invalid email or password, or account inactive")
    establish_session(request, response, db, user)
    return user


@router.get("/me", response_model=AuthUserResponse)
def current_user(user: User = Depends(get_current_user)):
    return user


@router.post("/logout", dependencies=[Depends(csrf_guard)])
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == token_digest(token)))
        db.commit()
    clear_cookie(response)
    return {"detail": "Signed out"}
