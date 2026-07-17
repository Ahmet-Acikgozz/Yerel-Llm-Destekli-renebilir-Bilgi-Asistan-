"""
auth.py (api)  — Login Endpoint

POST /auth/login  → kullanıcı adı+şifre → JWT token
GET  /auth/me     → token'dan mevcut kullanıcıyı göster
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.core.auth import authenticate_user, create_access_token, get_current_user

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Giriş yap — JWT token al",
    description="""
Kullanıcı adı ve şifre ile giriş yapın, JWT token alın.

**Test kullanıcıları:**
- Admin: `admin` / `admin123`
- Kullanıcı: `user` / `user123`

Aldığınız token'ı Swagger'da sağ üstteki **Authorize** butonuna girin.
    """,
)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 form ile login → JWT token döndür."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanici adi veya sifre yanlis.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        username=user["username"],
        role=user["role"],
    )

    return TokenResponse(
        access_token=token,
        username=user["username"],
        role=user["role"],
    )


@router.get(
    "/me",
    summary="Mevcut kullanıcı bilgisi",
    description="Token'dan mevcut kullanıcı adını ve rolünü gösterir.",
)
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "username": current_user["username"],
        "role": current_user["role"],
        "yetki": "Admin paneline erisim var" if current_user["role"] == "admin" else "Sadece soru sorabilir",
    }
