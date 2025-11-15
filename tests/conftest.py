# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlmodel import create_engine, Session, SQLModel, delete
from sqlalchemy.pool import StaticPool
from app.main import app
from app.models import User, PokedexEntry, Team, TeamMember
from app.auth import create_access_token, limiter
from app.database import get_session

# -------------------------------------------------------------------
# CONFIGURACIÓN GLOBAL
# -------------------------------------------------------------------
def pytest_configure(config):
    config.option.anyio_backend = "asyncio"

@pytest.fixture(autouse=True)
def disable_rate_limit():
    from app.auth import limiter
    limiter.enabled = False
    yield
    limiter.enabled = True


# -------------------------------------------------------------------
# Motor de base de datos en memoria para tests
# -------------------------------------------------------------------
@pytest.fixture(scope="function")
def engine():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool  # <- clave para compartir la misma conexión
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)

# -------------------------------------------------------------------
# Sesión de base de datos por test
# -------------------------------------------------------------------
@pytest.fixture(scope="function")
def db_session(engine):
    with Session(engine) as session:
        yield session
        session.rollback()
# -------------------------------------------------------------------
# Cliente FastAPI con DB de test
# -------------------------------------------------------------------
@pytest.fixture(scope="function")
def client(engine):
    """Cliente de prueba de FastAPI usando DB de test."""

    def get_test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

# -------------------------------------------------------------------
# Limpieza de datos entre tests
# -------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clean_db(db_session):
    """Elimina todos los datos antes de cada test."""
    db_session.exec(delete(TeamMember))
    db_session.exec(delete(Team))
    db_session.exec(delete(PokedexEntry))
    db_session.exec(delete(User))
    db_session.commit()

    # Reiniciar autoincrement de SQLite



# -------------------------------------------------------------------
# Usuario de prueba
# -------------------------------------------------------------------

@pytest.fixture(scope="function")
def test_user(client, db_session):
    """Crea un usuario de prueba si no existe y devuelve dict con username/password."""

    # Datos del usuario de prueba
    user_data = {
        "username": "test_user",
        "email": "test@example.com",
        "password": "TestPassword123!"
    }

    # Revisar si el usuario ya existe en la DB
    existing_user = db_session.exec(
        select(User).where(User.username == user_data["username"])
    ).first()

    if existing_user:
        # Devuelve los datos para login si ya existe
        return user_data

    # Desactivar temporalmente el limitador para registrar el usuario
    limiter.enabled = False
    try:
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code in (200, 201), f"Error al crear usuario: {response.text}"
        return user_data
    finally:
        limiter.enabled = True
# -------------------------------------------------------------------
# Token y headers de autenticación
# -------------------------------------------------------------------
@pytest.fixture(scope="function")
def access_token(test_user):
    """Genera un token JWT válido sin depender del endpoint /login."""
    token = create_access_token(
        username=test_user["username"],
        user_id=1  # Usamos id=1 ficticio para tests
    )
    return token

@pytest.fixture(scope="function")
def auth_headers(client, test_user):
    """Genera headers de autorización para el usuario de prueba."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}