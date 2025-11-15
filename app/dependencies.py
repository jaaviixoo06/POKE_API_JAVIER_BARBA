# app/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session
from jose import JWTError, ExpiredSignatureError, jwt
from app.database import get_session
from app.models import User
from app.config import settings
from typing import Optional, Any


# 1. SCHEMA DE AUTENTICACIÓN (HTTP Bearer)
# auto_error=False para poder manejar el error y devolver 401 en lugar de 403
bearer_scheme = HTTPBearer(auto_error=False)

# 2. DECODIFICAR Y VALIDAR TOKEN
def verify_token_data(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict[str, Any]:
    """
    Decodifica el JWT recibido en el encabezado Authorization: Bearer <token>.
    """
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Token ausente",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: Optional[int] = payload.get("user_id")
        username: Optional[str] = payload.get("sub")

        if user_id is None or username is None:
            raise credentials_exception

        return {"user_id": user_id, "username": username}

    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise credentials_exception

# 3. DEPENDENCIA PRINCIPAL PARA ENDPOINTS PROTEGIDOS
def get_current_active_user(token_data: dict = Depends(verify_token_data),session: Session = Depends(get_session),
) -> User:
    """
    Devuelve el usuario autenticado basado en los datos del token.
    """
    user = session.get(User, token_data["user_id"])

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Usuario no encontrado")

    if hasattr(user, "is_active") and not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Usuario inactivo")

    return user
