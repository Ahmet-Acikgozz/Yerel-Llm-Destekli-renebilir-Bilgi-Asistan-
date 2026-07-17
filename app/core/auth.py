"""
auth.py (core)  — JWT Token Yönetimi

JWT (JSON Web Token) nasıl çalışır?
  1. Kullanıcı login olur → sunucu token üretir ve verir
  2. Kullanıcı her istekte token'ı header'da gönderir
     Authorization: Bearer <token>
  3. Sunucu token'ı doğrular → içindeki rolü okur → erişime izin ver/ver

Token yapısı:
  Header.Payload.Signature
  Payload: {"sub": "admin", "role": "admin", "exp": 1234567890}
"""

from datetime import datetime, timedelta, timezone
from typing import Literal

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings

# OAuth2: Token'ı Authorization: Bearer header'dan okur
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

Role = Literal["admin", "user"]
USERS_DB: dict[str, dict] = {}


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _init_users():
    USERS_DB[settings.admin_username] = {
        "username": settings.admin_username,
        "hashed_password": _hash_password(settings.admin_password),
        "role": "admin",
    }
    USERS_DB[settings.user_username] = {
        "username": settings.user_username,
        "hashed_password": _hash_password(settings.user_password),
        "role": "user",
    }


_init_users()


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def authenticate_user(username: str, password: str) -> dict | None:
    """Kullanıcı adı ve şifre doğruysa kullanıcı dict'i döndürür."""
    user = USERS_DB.get(username)
    if not user:
        return None
    if not _verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(username: str, role: str) -> str:
    """JWT token oluşturur."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_expire_minutes
    )
    payload = {
        "sub": username,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def _decode_token(token: str) -> dict:
    """Token'ı decode eder, geçersizse HTTPException fırlatır."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gecersiz veya suresi dolmus token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ─── DEPENDENCY'LER ────────────────────────────────────────────
# FastAPI endpoint'lerinde Depends() ile kullanılır.

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Token'dan kullanıcıyı çıkarır. Geçersizse 401 fırlatır."""
    payload = _decode_token(token)
    username = payload.get("sub")
    role = payload.get("role", "user")
    if not username:
        raise HTTPException(status_code=401, detail="Token gecersiz.")
    return {"username": username, "role": role}


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Sadece admin rolüne izin verir. Değilse 403 fırlatır."""
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu islemi yapmak icin admin yetkisi gereklidir.",
        )
    return current_user


def require_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Hem user hem admin rolüne izin verir."""
    return current_user
