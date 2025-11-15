# app/utils.py - CÓDIGO FINAL CONSOLIDADO

from fastapi import HTTPException, status
import re
from passlib.context import CryptContext


# --- CONFIGURACIÓN DE HASHING ---
# Contexto para hashing y verificación de contraseñas (Solución de estabilidad)
#schemes=["bcrypt_sha256"]
pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt", "sha256_crypt"],
    deprecated="auto"
)


# --------------------------------------------------------------------------
# --- 1. Lógica de Validación (Parte 2.2) ---
# --------------------------------------------------------------------------

def validate_password_policy(password: str):
    """
    Valida que la contraseña cumpla:
    - Mínimo una mayúscula
    - Mínimo un número
    - Mínimo un carácter especial
    - Mínimo 8 caracteres (opcional pero recomendado)
    """

    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 8 caracteres."
        )

    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe contener al menos una letra mayúscula."
        )

    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe contener al menos un número."
        )

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=/\\\[\]]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe contener al menos un carácter especial."
        )
