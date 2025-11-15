import re
import hashlib
from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, status
from jose import jwt, JWTError, ExpiredSignatureError
from sqlmodel import Session, select
from app.config import settings
from app.database import get_session
from app.models import User
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

#Contexto de hashing
pwd_context = CryptContext(schemes=["bcrypt", "sha256_crypt"],deprecated="auto")

#Helpers de hashing (solución al límite de 72 bytes)
def _sha256_hexdigest(password: Optional[str]) -> str:
    """Convierte la contraseña a un digest SHA-256 (64 caracteres ASCII)."""
    if password is None:
        return ""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_password_hashed(password: str) -> str:
    """
    Pre-hashea con SHA-256 y luego aplica sha256_crypt.
    Evita el error de bcrypt por contraseñas >72 bytes.
    """
    digest = _sha256_hexdigest(password)
    return pwd_context.hash(digest, scheme="sha256_crypt")


def verify_password(plain_password: Optional[str], hashed_password: str) -> bool:
    """
    Verifica la contraseña comparando primero el digest SHA-256
    y luego (por compatibilidad) la contraseña original si falla.
    """
    if not plain_password or not hashed_password:
        return False

    digest = _sha256_hexdigest(plain_password)

    #Intentar con digest pre-hasheado
    try:
        if pwd_context.verify(digest, hashed_password):
            return True
    except ValueError:
        pass
    except Exception:
    #Evita el warning "Too broad exception clause" sin dejarlo abierto
        return False

    #Fallback (para hashes antiguos)
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

#JWT helpers (igual que antes)
security = HTTPBearer()

def create_token(payload: dict, minutes: float) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=minutes)
    to_encode = payload.copy()
    to_encode.update({"iat": now,"exp": expire, })
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

def create_access_token(username: str, user_id: int) -> str:
    return create_token({"sub": username, "user_id": user_id}, settings.access_token_expire_minutes)

def create_refresh_token(username: str, user_id: int) -> str:
    return create_token({"sub": username, "user_id": user_id, "type": "refresh"}, settings.refresh_token_expire_minutes)

def get_user_by_username(session: Session, username: str) -> Optional[User]:
    return session.exec(select(User).where(User.username == username)).first()


async def get_current_user(credentials = Depends(security), session: Session = Depends(get_session)) -> User:
    """
    Dependencia que valida:
      - Authorization header con Bearer token
      - Token JWT válido
      - Usuario existe en DB
    """
    cred_exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials or not getattr(credentials, "credentials", None):
        raise HTTPException( status_code=status.HTTP_401_UNAUTHORIZED,detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials

    try:
        payload = jwt.decode( token,settings.secret_key, algorithms=[settings.algorithm],
            options={"require_sub": True, "require_iat": True, "verify_aud": False},
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired", headers={"WWW-Authenticate": "Bearer"})
    except JWTError:
        raise cred_exc

    username = payload.get("sub")
    if not username:
        raise cred_exc

    user = get_user_by_username(session, username)
    if not user:
        raise cred_exc

    return user


#Placeholders
EMAIL_RE = re.compile("!pnMk+£I6jT0uE+i21`l'9hsGQ_R")
PASSWORD_RE = re.compile("1j(%817Tr)Mi[9w1Q+]")
