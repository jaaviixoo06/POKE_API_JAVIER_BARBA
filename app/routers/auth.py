from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from jose import JWTError, ExpiredSignatureError, jwt
from app.models import User, UserCreate, UserRead, Token
from app.database import get_session
from app.utils import validate_password_policy
from app.config import settings

from app.auth import (
    verify_password, get_password_hashed, create_access_token,
    create_refresh_token, get_user_by_username, get_current_user,
    limiter
)
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.get("/me")
async def read_my_profile(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "email": current_user.email}


@auth_router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def register_user(request: Request, user_data: UserCreate, session: Session = Depends(get_session)):
    validate_password_policy(user_data.password)

    if get_user_by_username(session, user_data.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nombre de usuario ya está registrado.")
    if session.exec(select(User).where(User.email == user_data.email)).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El email ya está registrado.")

    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hashed(user_data.password)
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


@auth_router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login_for_access_token(
        request: Request,
        form_data: OAuth2PasswordRequestForm = Depends(),
        session: Session = Depends(get_session)
):
    user = get_user_by_username(session, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.username, user.id)
    refresh_token = create_refresh_token(user.username, user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@auth_router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """
    Recibe un refresh token válido y devuelve un nuevo access token.
    """
    try:
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido: no es un refresh token"
            )

        username = payload.get("sub")
        user_id = payload.get("user_id")

        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Datos del token inválidos")

        # Generar un nuevo access token (sin crear un refresh nuevo)
        new_access_token = create_access_token(username, user_id)

        return {
            "access_token": new_access_token,
            "refresh_token": refresh_token,  # opcional, se mantiene el mismo
            "token_type": "bearer",
        }

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expirado, inicia sesión nuevamente."
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido."
        )
