# app/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from app.database import get_session
from app.auth import verify_token  # Importamos la función de verificación de token
from app.models import User  # Necesario para buscar el usuario en la DB

# Definición del esquema de seguridad. Le dice a FastAPI dónde buscar el token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user_data(token: str = Depends(oauth2_scheme)) -> dict:
    """Verifica el token JWT y retorna los datos del payload (sub, user_id)."""

    # Excepción para credenciales inválidas (401 Unauthorized)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # ⬅️ IMPLEMENTACIÓN COMPLETA DE LA LLAMADA A verify_token
    return verify_token(token, credentials_exception)


def get_current_active_user(
        session: Session = Depends(get_session),
        user_data: dict = Depends(get_current_user_data)
) -> User:
    """Obtiene el objeto User activo desde la base de datos."""

    # Buscar el usuario por el user_id del token (claim user_id)
    user = session.exec(
        select(User).where(User.id == user_data.get("user_id"))
    ).first()

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    # Verificar si el usuario está activo (is_active)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario inactivo")

    return user