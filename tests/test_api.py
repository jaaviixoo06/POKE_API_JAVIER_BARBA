# tests/test_auth_rate_limit.py
from fastapi.testclient import TestClient
import pytest
from limits.storage.memory import MemoryStorage
from app.main import limiter  # tu Limiter de FastAPI/SlowAPI

@pytest.fixture
def reset_limiter():
    """
    Fixture que reemplaza temporalmente el storage del limiter por uno limpio.
    Esto asegura que el test de rate limit comience desde cero.
    """
    original_storage = limiter._storage  # guardamos el storage original
    limiter._storage = MemoryStorage()   # nuevo storage limpio

    yield  # aquí se ejecuta el test

    limiter._storage = original_storage  # restauramos el storage original


def test_rate_limit_exceeded(client: TestClient, test_user, reset_limiter):
    """
    Test que comprueba que se respeta el límite de intentos de login.
    """
    login_data = {
        "username": test_user["username"],
        "password": test_user["password"]
    }

    # Las primeras 10 solicitudes deben pasar
    for i in range(10):
        r = client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert r.status_code == 200, f"Error en intento {i+1}: {r.text}"

    # La 11ª solicitud debe devolver 429
    r = client.post(
        "/api/v1/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert r.status_code == 429, f"Rate limit no funcionó: {r.text}"