# tests/test_pokeapi_service.py
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException, status
import httpx

from app.services.pokeapi_service import PokeAPIService

pytestmark = pytest.mark.anyio


@pytest.fixture
def service():
    return PokeAPIService()


# -------------------------------
# Tests exitosos de _fetch
# -------------------------------
@pytest.mark.anyio
async def test_fetch_success(service):
    # Mock de respuesta de httpx
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"id": 1, "name": "bulbasaur"}
    mock_response.status_code = 200
    mock_response.elapsed.total_seconds.return_value = 0.123

    # Patch de AsyncClient.get con AsyncMock que acepta self y kwargs
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        data = await service._fetch("/pokemon/1")
        assert data["id"] == 1
        assert data["name"] == "bulbasaur"


# -------------------------------
# Tests de errores de _fetch
# -------------------------------
@pytest.mark.anyio
@pytest.mark.parametrize(
    "exc, status_code, detail_contains",
    [
        (
            httpx.TimeoutException("Timeout", request=httpx.Request("GET", "https://pokeapi.co")),
            status.HTTP_504_GATEWAY_TIMEOUT,
            "Timeout"
        ),
        (
            httpx.ConnectError("Connection failed", request=httpx.Request("GET", "https://pokeapi.co")),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "conexión"
        ),
        (
            httpx.HTTPStatusError(
                "Not found",
                request=httpx.Request("GET", "https://pokeapi.co"),
                response=MagicMock(status_code=404)
            ),
            status.HTTP_404_NOT_FOUND,
            "no encontrado"
        ),
        (
            Exception("fail"),
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Error interno"
        ),
    ]
)
async def test_fetch_errors(service, exc, status_code, detail_contains):
    # Patch AsyncClient.get con AsyncMock y side_effect
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = exc
        with pytest.raises(HTTPException) as e:
            await service._fetch("/pokemon/1")
        assert e.value.status_code == status_code
        assert detail_contains.lower() in str(e.value.detail).lower()

# -------------------------------
# Tests de get_pokemon
# -------------------------------
@pytest.mark.anyio
async def test_get_pokemon(service):
    mock_data = {
        "id": 1,
        "name": "bulbasaur",
        "base_experience": 64,
        "types": [{"type": {"name": "grass"}}],
        "sprites": {"front_default": "url"},
        "stats": [],
        "abilities": []
    }

    async def fake_fetch(endpoint):
        return mock_data

    service._fetch = fake_fetch
    result = await service.get_pokemon(1)
    assert result["id"] == 1
    assert result["name"] == "bulbasaur"
    assert result["types"] == ["grass"]
    assert result["sprites"] == "url"


# -------------------------------
# Tests de search_pokemon
# -------------------------------
@pytest.mark.anyio
async def test_search_pokemon(service):
    mock_data = {
        "count": 1118,
        "results": [{"name": "bulbasaur", "url": "url"}]
    }

    async def fake_fetch(endpoint):
        return mock_data

    service._fetch = fake_fetch
    result = await service.search_pokemon(limit=1, offset=0)
    assert result["count"] == 1118
    assert len(result["results"]) == 1
    assert result["results"][0]["name"] == "bulbasaur"


# -------------------------------
# Tests de get_pokemon_by_type
# -------------------------------
@pytest.mark.anyio
async def test_get_pokemon_by_type(service):
    mock_data = {
        "pokemon": [{"pokemon": {"name": "bulbasaur", "url": "url"}}]
    }

    async def fake_fetch(endpoint):
        return mock_data

    service._fetch = fake_fetch
    result = await service.get_pokemon_by_type("grass")
    assert len(result) == 1
    assert result[0]["name"] == "bulbasaur"
