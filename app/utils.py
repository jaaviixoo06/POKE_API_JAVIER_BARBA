# app/utils.py - CÓDIGO FINAL

from fastapi import HTTPException, status
import re
from typing import Optional

def validate_password_policy(password: str):
    """Valida la política de contraseña: min 8 caracteres, 1 mayúscula, 1 número."""
    # 1. Mínimo 8 caracteres
    if len(password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contraseña debe tener al menos 8 caracteres.")
    # 2. Mínimo 1 mayúscula
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contraseña debe contener al menos 1 letra mayúscula.")
    # 3. Mínimo 1 número
    if not re.search(r"\d", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contraseña debe contener al menos 1 número.")
    return True