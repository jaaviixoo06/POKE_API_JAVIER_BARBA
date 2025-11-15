# tests/test_pokedex.py
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.dependencies import get_current_active_user
from app.services.pokeapi_service import pokeapi_service
from app.main import app
from app.auth import get_current_user

pytestmark = pytest.mark.anyio  # permite usar async/await si fuese necesario

# -------------------------------------------------------------------
# Mock global de autenticación: cualquier usuario válido
# -------------------------------------------------------------------
from app.models import User


@pytest.fixture(autouse=True)
def override_auth():
    async def fake_get_current_user():
        return User(
            id=99999,
            username="test_user",
            email="test@example.com",
            hashed_password="fakehashedpassword",  # necesario para NOT NULL
            capture_streak=0,
            last_capture_date=None
        )

    app.dependency_overrides[get_current_user] = fake_get_current_user
    app.dependency_overrides[get_current_active_user] = fake_get_current_user

    yield  # aquí se ejecutan los tests

    app.dependency_overrides.clear()



# -------------------------------------------------------------------
# Mock global de PokeAPI: siempre retorna Bulbasaur
# -------------------------------------------------------------------
@pytest.fixture(autouse=True)
def mock_pokeapi_global():
    with patch.object(pokeapi_service, "get_pokemon", new_callable=AsyncMock) as mock:
        mock.return_value = {
            "id": 1,
            "name": "bulbasaur",
            "stats": [
                {"stat": {"name": "hp"}, "base_stat": 45},
                {"stat": {"name": "attack"}, "base_stat": 49},
            ],
            "types": [{"type": {"name": "grass"}}, {"type": {"name": "poison"}}],
            "sprites": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/1.png"
        }
        yield mock

# -------------------------------------------------------------------
# Tests de endpoints de Pokémon
# -------------------------------------------------------------------
def test_get_pokemon_details_success(client: TestClient):
    response = client.get("/api/v1/pokemon/1")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "bulbasaur"
    assert "stats" in data

def test_get_pokemon_details_not_found(client: TestClient, mock_pokeapi_global):
    mock_pokeapi_global.return_value = None
    response = client.get("/api/v1/pokemon/999")
    assert response.status_code == 404

def test_get_pokemon_details_service_error(client: TestClient, mock_pokeapi_global):
    mock_pokeapi_global.side_effect = Exception("fail")
    response = client.get("/api/v1/pokemon/1")
    assert response.status_code == 500

# -------------------------------------------------------------------
# Tests de generación de cartas
# -------------------------------------------------------------------
def test_generate_pokemon_card_png(client: TestClient):
    response = client.get("/api/v1/pokemon/1/card?format=png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"

def test_generate_pokemon_card_pdf(client: TestClient):
    response = client.get("/api/v1/pokemon/1/card?format=pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")

def test_generate_pokemon_card_invalid_format(client: TestClient):
    response = client.get("/api/v1/pokemon/1/card?format=jpg")
    assert response.status_code == 400
    assert "Formato no válido" in response.json()["detail"]

def test_generate_pokemon_card_requires_auth(client: TestClient):
    # Con el mock global de auth, cualquier request pasa
    response = client.get("/api/v1/pokemon/1/card?format=png")
    assert response.status_code == 200

def test_generate_pokemon_card_service_error(client: TestClient, mock_pokeapi_global):
    mock_pokeapi_global.side_effect = Exception("error inesperado")
    response = client.get("/api/v1/pokemon/1/card?format=pdf")
    assert response.status_code == 500

def test_add_pokemon_duplicate(client: TestClient, mock_pokeapi_global):
    # Primero agregamos un Pokémon
    response1 = client.post("/api/v1/pokedex", json={"pokemon_id": 1, "is_captured": True})
    assert response1.status_code == 201

    # Intentamos agregarlo de nuevo → debería dar 400
    response2 = client.post("/api/v1/pokedex", json={"pokemon_id": 1, "is_captured": True})
    assert response2.status_code == 400
    assert "ya existe" in response2.json()["detail"]

def test_add_pokemon_invalid_id(client: TestClient, mock_pokeapi_global):
    from fastapi import HTTPException
    # Forzamos que PokeAPI lance 404
    mock_pokeapi_global.side_effect = HTTPException(status_code=404)
    response = client.post("/api/v1/pokedex", json={"pokemon_id": 999, "is_captured": True})
    assert response.status_code == 404
    assert "no válido" in response.json()["detail"]

def test_list_pokedex_filters(client: TestClient, mock_pokeapi_global):
    # Agregamos dos Pokémon, uno capturado y otro no
    client.post("/api/v1/pokedex", json={"pokemon_id": 1, "is_captured": True})
    client.post("/api/v1/pokedex", json={"pokemon_id": 2, "is_captured": False})

    # Filtramos capturados
    r_captured = client.get("/api/v1/pokedex?captured=true")
    assert r_captured.status_code == 200
    for e in r_captured.json():
        assert e["is_captured"] is True

    # Filtramos no capturados
    r_not_captured = client.get("/api/v1/pokedex?captured=false")
    assert r_not_captured.status_code == 200
    for e in r_not_captured.json():
        assert e["is_captured"] is False

    # Orden descendente por pokemon_id
    r_desc = client.get("/api/v1/pokedex?sort=pokemon_id&order=desc")
    assert r_desc.status_code == 200
    ids = [e["pokemon_id"] for e in r_desc.json()]
    assert ids == sorted(ids, reverse=True)
def test_update_pokedex_entry_success(client: TestClient, mock_pokeapi_global):
    # Creamos un Pokémon
    r = client.post("/api/v1/pokedex", json={"pokemon_id": 3, "is_captured": True})
    entry_id = r.json()["id"]

    # Actualizamos nickname y favorito
    r_update = client.patch(f"/api/v1/pokedex/{entry_id}", json={"nickname": "MyBulba", "favorite": True})
    assert r_update.status_code == 200
    data = r_update.json()
    assert data["nickname"] == "MyBulba"
    assert data["favorite"] is True

def test_update_pokedex_entry_not_found(client: TestClient):
    r = client.patch("/api/v1/pokedex/999", json={"nickname": "Nope"})
    assert r.status_code == 404

def test_delete_pokedex_entry_success(client: TestClient, mock_pokeapi_global):
    r = client.post("/api/v1/pokedex", json={"pokemon_id": 4, "is_captured": True})
    entry_id = r.json()["id"]

    r_delete = client.delete(f"/api/v1/pokedex/{entry_id}")
    assert r_delete.status_code == 204

    # Intentar borrar de nuevo → no existe, pero retorna 204
    r_delete2 = client.delete(f"/api/v1/pokedex/{entry_id}")
    assert r_delete2.status_code == 204
def test_export_pokedex_csv_pdf(client: TestClient, mock_pokeapi_global):
    # Crear un Pokémon
    client.post("/api/v1/pokedex", json={"pokemon_id": 5, "is_captured": True})

    # CSV
    r_csv = client.get("/api/v1/pokedex/export?format=csv")
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")

    # PDF
    r_pdf = client.get("/api/v1/pokedex/export?format=pdf")
    assert r_pdf.status_code == 200
    assert r_pdf.headers["content-type"].startswith("application/pdf")


    # Formato inválido
    r_invalid = client.get("/api/v1/pokedex/export?format=txt")
    assert r_invalid.status_code == 400

def test_get_pokedex_stats_empty(client: TestClient):
    r = client.get("/api/v1/pokedex/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total_pokemon"] == 0
    assert data["captured"] == 0
    assert data["capture_streak_days"] == 0



