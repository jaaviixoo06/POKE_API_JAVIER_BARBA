# tests/test_teams.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth import get_current_user
from app.dependencies import get_current_active_user
from app.models import User, PokedexEntry
from app.services.pokeapi_service import pokeapi_service
from app.main import app
import io
from PIL import Image
from unittest.mock import AsyncMock

pytestmark = pytest.mark.anyio
API_PREFIX = "/api/v1/teams"

# -------------------------------------------------------------------
# Mock global de autenticación: cualquier usuario válido
# -------------------------------------------------------------------
@pytest.fixture(autouse=True)
def override_auth_for_teams():
    async def fake_user():
        return User(
            id=99999,
            username="test_user",
            email="test@example.com",
            hashed_password="fakehashedpassword",
            capture_streak=0,
            last_capture_date=None
        )

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_current_active_user] = fake_user

    yield
    app.dependency_overrides.clear()


# -------------------------------------------------------------------
# Helper: añadir Pokémon a la Pokédex
# -------------------------------------------------------------------
def add_pokemon_to_pokedex(session: Session, owner_id: int, pokemon_id: int) -> int:
    entry = PokedexEntry(
        owner_id=owner_id,
        pokemon_id=pokemon_id,
        pokemon_name=f"Pokemon{pokemon_id}",
        pokemon_sprite=f"url_{pokemon_id}",
        is_captured=True
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry.id


# -------------------------------------------------------------------
# Mock pokeapi_service
# -------------------------------------------------------------------
@pytest.fixture
def mock_pokeapi_service(monkeypatch):
    async def fake_get_pokemon(pokedex_entry_id):
        return {
            "id": pokedex_entry_id,
            "name": f"pokemon{pokedex_entry_id}",
            "types": [{"type": {"name": "Normal"}}],
            "stats": [{"stat": {"name": "hp"}, "base_stat": 50}],
            "sprite": f"url_{pokedex_entry_id}"
        }
    monkeypatch.setattr(pokeapi_service, "get_pokemon", AsyncMock(side_effect=fake_get_pokemon))


# -------------------------------------------------------------------
# Mock requests.get para PDF
# -------------------------------------------------------------------
@pytest.fixture
def mock_requests_get(monkeypatch):
    class FakeResponse:
        def __init__(self):
            img = Image.new("RGBA", (80, 80), color=(255, 0, 0, 255))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            self.content = buf.getvalue()
            self.status_code = 200

        def raise_for_status(self):
            pass

    import requests
    monkeypatch.setattr(requests, "get", lambda url, *args, **kwargs: FakeResponse())


# -------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------

def test_create_team_success(client: TestClient, db_session: Session):
    user_id = 99999
    entry_ids = [add_pokemon_to_pokedex(db_session, user_id, pid) for pid in [1, 2]]

    r = client.post(
        API_PREFIX,
        json={"name": "Equipo Test", "description": "Mi primer equipo", "pokemon_ids": entry_ids}
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Equipo Test"
    assert data["description"] == "Mi primer equipo"
    assert data["trainer_id"] == user_id
    assert "id" in data


def test_create_team_too_many(client: TestClient, db_session: Session):
    user_id = 99999
    entry_ids = [add_pokemon_to_pokedex(db_session, user_id, pid) for pid in range(1, 8)]

    r = client.post(
        API_PREFIX,
        json={"name": "Equipo Largo", "description": "Demasiados Pokémon", "pokemon_ids": entry_ids}
    )
    assert r.status_code == 400
    assert "no puede tener más de 6" in r.json()["detail"]


def test_create_team_pokemon_not_in_pokedex(client: TestClient, db_session: Session):
    user_id = 99999
    add_pokemon_to_pokedex(db_session, user_id, 1)
    entry_ids = [1, 999]  # Pokémon 999 no está en Pokédex

    r = client.post(
        API_PREFIX,
        json={"name": "Equipo Inválido", "description": "Pokémon no en Pokédex", "pokemon_ids": entry_ids}
    )
    assert r.status_code == 400
    assert "no se encuentran en tu Pokédex" in r.json()["detail"]


def test_list_teams_with_data(client: TestClient, db_session: Session):
    user_id = 99999
    entry_ids = [add_pokemon_to_pokedex(db_session, user_id, 1)]

    r_create = client.post(
        API_PREFIX,
        json={"name": "Equipo Listado", "description": "Prueba list", "pokemon_ids": entry_ids}
    )
    assert r_create.status_code == 201

    r_list = client.get(API_PREFIX)
    assert r_list.status_code == 200
    data = r_list.json()
    assert any(team["name"] == "Equipo Listado" for team in data)


def test_update_team_success(client: TestClient, db_session: Session):
    user_id = 99999
    entry_ids = [add_pokemon_to_pokedex(db_session, user_id, pid) for pid in [1, 2]]

    r_create = client.post(
        API_PREFIX,
        json={"name": "Equipo Update", "description": "Antes", "pokemon_ids": entry_ids}
    )
    assert r_create.status_code == 201
    team_id = r_create.json()["id"]

    new_entry_ids = [add_pokemon_to_pokedex(db_session, user_id, 3)]

    r_update = client.put(
        f"{API_PREFIX}/{team_id}",
        json={"name": "Equipo Actualizado", "description": "Después", "pokemon_ids": new_entry_ids}
    )
    assert r_update.status_code == 200
    data = r_update.json()
    assert data["id"] == team_id
    assert data["name"] == "Equipo Actualizado"
    assert data["description"] == "Después"
    assert data["trainer_id"] == user_id

def test_update_team_not_found(client: TestClient, db_session: Session):
    # Intentar actualizar un equipo inexistente
    r = client.put(f"{API_PREFIX}/99999", json={"name": "X", "description": "Y", "pokemon_ids": []})
    assert r.status_code == 404
    assert "Equipo no encontrado" in r.json()["detail"]


def test_update_team_too_many_pokemon(client: TestClient, db_session: Session):
    user_id = 99999
    entry_ids = [add_pokemon_to_pokedex(db_session, user_id, pid) for pid in range(1, 7)]
    r_create = client.post(API_PREFIX, json={"name": "Equipo Max", "description": "", "pokemon_ids": entry_ids})
    team_id = r_create.json()["id"]

    new_entry_ids = [add_pokemon_to_pokedex(db_session, user_id, pid) for pid in range(7)]
    r_update = client.put(f"{API_PREFIX}/{team_id}", json={"name": "Overflow", "description": "", "pokemon_ids": new_entry_ids})
    assert r_update.status_code == 400
    assert "no puede tener más de 6" in r_update.json()["detail"]


def test_update_team_pokemon_not_in_pokedex(client: TestClient, db_session: Session):
    user_id = 99999
    entry_ids = [add_pokemon_to_pokedex(db_session, user_id, 1)]
    r_create = client.post(API_PREFIX, json={"name": "Equipo Test", "description": "", "pokemon_ids": entry_ids})
    team_id = r_create.json()["id"]

    # Pokémon 999 no existe en Pokédex
    r_update = client.put(f"{API_PREFIX}/{team_id}", json={"name": "Invalid", "description": "", "pokemon_ids": [999]})
    assert r_update.status_code == 400
    assert "no se encuentran en tu Pokédex" in r_update.json()["detail"]


def test_create_team_empty_pokemon(client: TestClient):
    r = client.post(API_PREFIX, json={"name": "Equipo Vacio", "description": "", "pokemon_ids": []})
    assert r.status_code == 400
    assert "al menos un Pokémon" in r.json()["detail"]


def test_export_team_success(client: TestClient, db_session: Session, mock_pokeapi_service, mock_requests_get):
    user_id = 99999
    entry_id = add_pokemon_to_pokedex(db_session, user_id, 1)
    r_create = client.post(API_PREFIX, json={"name": "Equipo PDF", "description": "", "pokemon_ids": [entry_id]})
    team_id = r_create.json()["id"]

    r_export = client.get(f"{API_PREFIX}/{team_id}/export")
    assert r_export.status_code == 200
    assert r_export.headers["content-type"] == "application/pdf"
    assert r_export.content.startswith(b"%PDF")

def test_export_team_not_found(client: TestClient):
    r_export = client.get(f"{API_PREFIX}/99999/export")
    assert r_export.status_code == 404
    assert "Equipo no encontrado" in r_export.json()["detail"]
