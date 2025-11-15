# tests/test_auth.py
from datetime import datetime, timedelta

import jwt
import pytest
from sqlalchemy import select
from starlette import status
from app.auth import create_access_token, create_refresh_token
from app.config import settings
from app.models import User

API_PREFIX = "/api/v1/auth"

@pytest.mark.anyio
def test_register_user_success(client):
    """Registro exitoso de usuario"""
    user_data = {
        "username": "new_trainer",
        "email": "new_trainer@ufv.es",
        "password": "SecurePass123!"
    }
    response = client.post(f"{API_PREFIX}/register", json=user_data)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["username"] == "new_trainer"
    assert "id" in data

@pytest.mark.anyio
def test_register_duplicate_username(client, test_user):
    """Error al registrar username duplicado"""
    user_data = {
        "username": test_user["username"],
        "email": "another@email.es",
        "password": "SecurePass123!"
    }
    response = client.post(f"{API_PREFIX}/register", json=user_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.anyio
def test_login_invalid_credentials(client):
    """Login con credenciales incorrectas retorna 401"""
    login_data = {"username": "nonexistent", "password": "wrong"}
    response = client.post(
        f"{API_PREFIX}/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.anyio
def test_me_success(client, test_user, db_session):
    """Acceso a /me con token válido"""
    from app.models import User

    # Obtener el usuario real
    user_in_db = db_session.exec(
        select(User).where(User.username == test_user["username"])
    ).one()[0]  # <- clave

    token = create_access_token(user_in_db.username, user_in_db.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"{API_PREFIX}/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]



@pytest.mark.anyio
def test_me_unauthenticated(client):
    """Acceso a /me sin token retorna 403"""
    response = client.get(f"{API_PREFIX}/me")
    assert response.status_code == 403


@pytest.mark.anyio
def test_refresh_token_success(client, test_user, db_session):
    """Refrescar access token con refresh token válido"""

    # Obtener el usuario real de la DB como objeto User
    result = db_session.exec(
        select(User).where(User.username == test_user["username"])
    ).first()

    if result is None:
        pytest.fail(f"Usuario {test_user['username']} no encontrado en la DB")

    # Si result devuelve un Row en lugar de User, extraemos el primer elemento
    user_in_db = result
    if not isinstance(result, User):
        user_in_db = result[0]

    # Crear refresh token usando datos reales
    refresh_token = create_refresh_token(user_in_db.username, user_in_db.id)

    # Hacer la petición al endpoint de refresh
    response = client.post(f"{API_PREFIX}/refresh", params={"refresh_token": refresh_token})


    # Verificar que la respuesta es correcta
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["refresh_token"] == refresh_token

# -------------------------------------------------------------------
@pytest.mark.anyio
def test_refresh_token_invalid(client):
    """Refresh token inválido retorna 401"""
    response = client.post(f"{API_PREFIX}/refresh", params={"refresh_token": "invalidtoken"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# -------------------------------------------------------------------
@pytest.mark.anyio
def test_refresh_token_expired(client, test_user, db_session):
    """Refresh token expirado retorna 401"""

    # Obtener usuario real de la DB
    result = db_session.exec(
        select(User).where(User.username == test_user["username"])
    ).first()

    if result is None:
        pytest.fail(f"Usuario {test_user['username']} no encontrado en la DB")

    # Asegurarnos de que user_in_db sea un objeto User
    user_in_db = result if isinstance(result, User) else result[0]

    # Crear refresh token expirado (1 minuto en el pasado)
    expired_refresh_token = jwt.encode(
        {
            "sub": user_in_db.username,
            "user_id": user_in_db.id,
            "type": "refresh",
            "exp": datetime.utcnow() - timedelta(minutes=1)
        },
        settings.secret_key,
        algorithm=settings.algorithm
    )

    # Hacer la petición al endpoint usando query param
    response = client.post(f"{API_PREFIX}/refresh", params={"refresh_token": expired_refresh_token})

    # Verificar que devuelve 401 por token expirado
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Refresh token expirado" in response.json()["detail"]
