# app/auth.py - USANDO ARGON2 (RECOMENDADO)
from passlib.context import CryptContext
from fastapi import HTTPException
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import os

from app.config import ACCESS_TOKEN_EXPIRE_MINUTES

# --- Configuración ---
SECRET_KEY = os.environ.get("SECRET_KEY", "CLAVE_DEFAULT_NO_SEGURA")
ALGORITHM = "HS256"

# Usamos Argon2: moderno y sin límite de 72 bytes.
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hashea una contraseña usando Argon2 y devuelve el hash.
    """
    if password is None:
        raise ValueError("La contraseña no puede ser None")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica la contraseña usando Argon2.
    """
    if plain_password is None:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


# --------------------------------------------------------------------------
# JWT helpers (igual que antes)
# --------------------------------------------------------------------------
def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, credentials_exception: HTTPException) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        user_id = payload.get("user_id")
        if username is None or user_id is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception
