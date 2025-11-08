# app/services/pokeapi_service.py

import httpx
from typing import Dict, List, Optional
from fastapi import HTTPException, status
import logging

# Inicializar el logger para la trazabilidad de peticiones externas (Punto 1.1 & 2.6)
logger = logging.getLogger("pokedex_api.pokeapi")


class PokeAPIService:
    BASE_URL = "https://pokeapi.co/api/v2"

    def __init__(self):
        # Cliente persistente con timeout de 5.0s para mejor manejo de errores de red (Punto 1.1)
        self.client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=5.0)

    async def _fetch(self, endpoint: str) -> Dict | List:
        """Helper interno para manejar la lógica común de petición, errores y logging."""
        logger.info(f"Llamada externa a PokeAPI: GET {self.BASE_URL}{endpoint}")

        try:
            # Uso de async/await correctamente
            response = await self.client.get(endpoint)
            # Levantar HTTPException para 4xx/5xx (Manejo correcto de errores HTTP)
            response.raise_for_status()

            # Logging de todas las peticiones externas
            logger.info(
                f"Respuesta de PokeAPI: {response.status_code} | GET {endpoint} | Duración: {response.elapsed.total_seconds():.3f}s")

            return response.json()

        except httpx.TimeoutException:
            logger.error(f"PokeAPI: Timeout al intentar acceder a {endpoint}")
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                                detail="Error de red (Timeout) al consultar PokeAPI")
        except httpx.ConnectError:
            logger.error(f"PokeAPI: Error de conexión con la API externa en {endpoint}")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail="Error de conexión con la PokeAPI")
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code == 404:
                # Validación de respuesta 404 (Pokémon no encontrado) [cite: 77, 92]
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"Recurso no encontrado en PokeAPI: {endpoint}")

            logger.error(f"PokeAPI: Error HTTP {status_code} en {endpoint}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                                detail=f"Error en la API externa de Pokémon: código {status_code}")
        except Exception as e:
            logger.error(f"Error inesperado al consultar PokeAPI {endpoint}: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")

    async def get_pokemon(self, identifier: str | int) -> Dict:
        """Obtiene datos detallados de un Pokémon."""
        endpoint = f"/pokemon/{identifier}"
        data = await self._fetch(endpoint)

        # Transformación de datos (extracción de campos relevantes)
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "base_experience": data.get("base_experience"),
            "types": [t["type"]["name"] for t in data.get("types", [])],
            "sprites": data.get("sprites", {}).get("front_default"),
            "stats": data.get("stats", []),
            "abilities": data.get("abilities", [])
        }

    async def search_pokemon(self, limit: int = 20, offset: int = 0) -> Dict:
        """Lista Pokémon con paginación"""
        endpoint = f"/pokemon?limit={limit}&offset={offset}"
        data = await self._fetch(endpoint)

        #Transformación de datos
        simplified_results = [
            {"name": result["name"], "url": result["url"]}
            for result in data.get("results", [])
        ]

        return {
            "count": data.get("count"),
            "results": simplified_results
        }

    async def get_pokemon_by_type(self, type_name: str) -> List[Dict]:
        """Obtiene todos los Pokémon de un tipo específico"""
        endpoint = f"/type/{type_name.lower()}"
        data = await self._fetch(endpoint)

        #Transformación de datos
        pokemon_list = data.get("pokemon", [])
        simplified_list = [
            {"name": entry["pokemon"]["name"], "url": entry["pokemon"]["url"]}
            for entry in pokemon_list
        ]

        return simplified_list


#Inicializar el servicio para usarlo en otros módulos
pokeapi_service = PokeAPIService()