# app/auth.py

from passlib.context import CryptContext
from fastapi import HTTPException, status
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

#Contexto para hashing y verificación de contraseñas (bcrypt) [cite: 37, 156]
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


#--- Utilidades de Seguridad ---

def hash_password(password: str) -> str:
    """Hashea una contraseña para almacenamiento seguro ."""
    # Contraseñas hasheadas (NUNCA en texto plano) [cite: 165]
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña plana contra su hash."""
    return pwd_context.verify(plain_password, hashed_password)


# --- Utilidades JWT ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crea un token JWT con claims: sub (username), user_id, exp, iat ."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Token válido por 24 horas
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    #Claims obligatorios
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, credentials_exception: HTTPException) -> Dict:
    """Valida el token JWT, retorna el payload o lanza la excepción."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        #Validación de claims
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")

        if username is None or user_id is None:
            raise credentials_exception

        return {"sub": username, "user_id": user_id}

    except JWTError:
        #Si el token es inválido, ha expirado, o la firma no coincide
        raise credentials_exception