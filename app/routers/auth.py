# app/routers/auth.py - REGISTRO Y LOGIN (Parte 2.2) - VERSIÓN MEJORADA

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from app.models import User, UserCreate, UserRead
from app.database import get_session
from app.auth import hash_password, verify_password, create_access_token  # Funciones de auth
from app.utils import validate_password_policy  # Validación de contraseñas
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# Definición del Rate Limiter
limiter = Limiter(key_func=get_remote_address)

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


# POST /api/v1/auth/register (Registro de usuarios)
@limiter.limit("5/hour")  # Rate limit: 5 registros/hora por IP
@auth_router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    request: Request,
    user_data: UserCreate,
    session: Session = Depends(get_session)
):
    # 1. Validación de política de contraseña
    try:
        validate_password_policy(user_data.password)
    except Exception as e:
        # Asumimos que validate_password_policy lanza excepciones con mensaje descriptivo.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 2. Verificar duplicidad (username y email)
    existing_user_by_username = session.exec(
        select(User).where(User.username == user_data.username)
    ).first()
    if existing_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya está registrado."
        )

    existing_user_by_email = session.exec(
        select(User).where(User.email == user_data.email)
    ).first()
    if existing_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado."
        )

    # 3. Hashear y crear el usuario
    try:
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            # hash_password maneja internamente el esquema (bcrypt_sha256 / argon2, lo que tengas)
            hashed_password=hash_password(user_data.password)
        )

        session.add(db_user)
        session.commit()
        session.refresh(db_user)

    except IntegrityError as ie:
        # Error de integridad (p.ej. constraint unique que se coló por race condition)
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo crear el usuario (conflicto de datos)."
        )
    except SQLAlchemyError as sae:
        # Otros errores de BD
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear el usuario."
        )

    # 4. Retornar usuario (UserRead debería omitir hashed_password)
    return db_user


# POST /api/v1/auth/login (Login)
@limiter.limit("10/minute")  # Rate limit: 10 intentos/minuto
@auth_router.post("/login")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    # Buscar usuario por username
    user = session.exec(select(User).where(User.username == form_data.username)).first()

    # Verificar credenciales
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Crear token (puedes ajustar payload según tus necesidades)
    access_token = create_access_token(data={"sub": user.username, "user_id": user.id})

    # Retornar JWT
    return {"access_token": access_token, "token_type": "bearer"}
