from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import Response
from typing import Optional
from app.services.pokeapi_service import pokeapi_service, logger
from app.dependencies import get_current_active_user
from app.models import User
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi.responses import HTMLResponse

limiter = Limiter(key_func=get_remote_address)

pokemon_router = APIRouter(prefix="/pokemon", tags=["Pokemon Search (Proxy)"])


# GET /api/v1/pokemon/search (Busca o lista paginado)
@pokemon_router.get("/{id_or_name}/card",
                    response_class=HTMLResponse)
async def generate_pokemon_card(
        id_or_name: str,
        current_user: User = Depends(get_current_active_user)
):
    """
    Genera y devuelve una ficha estilizada en formato HTML/CSS que simula una carta Pokémon.
    """
    try:
        # 1. Obtener detalles completos
        pokemon_data = await pokeapi_service.get_pokemon(id_or_name)

        # Extracción de datos clave
        name = pokemon_data['name'].capitalize()
        poke_id = pokemon_data['id']
        sprite_url = pokemon_data['sprites']

        # Obtenemos el tipo principal para el color de fondo
        types = [t.capitalize() for t in pokemon_data['types']]
        primary_type = types[0] if types else 'Normal'

        # Mapeo de colores basado en tipos comunes de Pokémon
        type_colors = {
            'Fire': '#f08030', 'Water': '#6890f0', 'Grass': '#78c850', 'Electric': '#f8d030',
            'Ice': '#98d8d8', 'Fighting': '#c03028', 'Poison': '#a040a0', 'Ground': '#e0c068',
            'Flying': '#a890f0', 'Psychic': '#f85888', 'Bug': '#a8b820', 'Rock': '#b8a038',
            'Ghost': '#705898', 'Dragon': '#7038f8', 'Steel': '#b8b8d0', 'Fairy': '#ee99ac',
            'Normal': '#a8a878', 'Dark': '#705848', 'N/A': '#68a090'
        }
        card_color = type_colors.get(primary_type, '#a8a878')

        hp_stat = next((s['base_stat'] for s in pokemon_data['stats'] if s['stat']['name'] == 'hp'), 'N/A')
        attack_stat = next((s['base_stat'] for s in pokemon_data['stats'] if s['stat']['name'] == 'attack'), 'N/A')
        defense_stat = next((s['base_stat'] for s in pokemon_data['stats'] if s['stat']['name'] == 'defense'), 'N/A')

        # Simulación de descripción
        description = f"Este es el Pokémon #{poke_id} de tipo {', '.join(types)}. Su ataque base es {attack_stat} y defensa {defense_stat}."

        # 2. Generación del HTML con CSS para simular la carta
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Pokémon Card: {name}</title>
            <style>
                body {{ background-color: #f0f0f0; display: flex; justify-content: center; padding-top: 50px; }}
                .pokemon-card {{
                    width: 350px;
                    height: 500px;
                    background: linear-gradient(to bottom, {card_color} 0%, #fff 40%, {card_color} 100%); /* Fondo degradado */
                    border: 8px solid #333;
                    border-radius: 20px;
                    box-shadow: 0 10px 20px rgba(0, 0, 0, 0.4);
                    font-family: 'Poppins', sans-serif; /* Usamos una fuente común */
                    padding: 15px;
                    position: relative;
                    color: #222;
                    display: flex;
                    flex-direction: column;
                }}
                .card-frame {{
                    flex-grow: 1;
                    border: 2px solid #555;
                    border-radius: 10px;
                    background-color: #fff;
                    padding: 10px;
                    display: flex;
                    flex-direction: column;
                }}
                .top-info {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 5px; }}
                .name {{ font-size: 1.8em; font-weight: 800; color: #111; }}
                .hp {{ font-weight: bold; color: red; font-size: 1.5em; border: 3px solid #333; border-radius: 5px; padding: 2px 5px; background: white; }}
                .image-box {{ 
                    background-color: #f5f5f5; 
                    border: 1px solid #ddd;
                    border-radius: 8px; 
                    padding: 5px; 
                    text-align: center;
                    min-height: 250px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    margin-bottom: 10px;
                }}
                .sprite {{ max-width: 250%; height: auto; }}

                .stats-box {{
                    background: {card_color};
                    color: white;
                    border-radius: 5px;
                    padding: 10px;
                    margin-top: 10px;
                    font-size: 0.9em;
                }}
                .stats-box strong {{ font-weight: bold; color: black; }}
            </style>
        </head>
        <body>
            <div class="pokemon-card">
                <div class="card-frame">
                    <div class="top-info">
                        <span class="name">{name}</span>
                        <span class="hp">{hp_stat} HP</span>
                    </div>

                    <div style="font-size: 1em; color: #555; margin-bottom: 5px;">
                        No. {poke_id} | Tipo: 
                        {''.join([f'<span class="type-badge" style="background-color: {card_color}; color: white;">{t}</span>' for t in types])}
                    </div>

                    <div class="image-box">
                        <img src="{sprite_url}" alt="{name} sprite" class="sprite"/>
                    </div>

                    <div class="description" style="font-size: 0.9em; border-top: 1px solid #ccc; padding-top: 8px;">
                        {description}
                    </div>

                    <div class="stats-box">
                        <div style="font-weight: bold;">Estadísticas Base:</div>
                        <p style="margin: 3px 0;">
                            Ataque: {attack_stat} | Defensa: {defense_stat}
                        </p>
                    </div>

                </div>
                <small style="text-align: center; margin-top: 5px; font-size: 0.7em;">API UFV - Pokédex Personal</small>
            </div>
        </body>
        </html>
        """

        # Retornamos el contenido HTML
        return HTMLResponse(content=html_content)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error al generar la ficha HTML: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al generar la ficha HTML.")
    """
    Busca Pokémon en PokeAPI o lista con paginación.
    Retorna lista simplificada: {id, name, sprite, types}
    """
    try:
        if name:
            result = await pokeapi_service.get_pokemon(name)

            # Retorna lista simplificada
            return [{
                "id": result.get("id"),
                "name": result.get("name"),
                "sprite": result.get("sprites"),
                "types": result.get("types")
            }]
        else:
            result = await pokeapi_service.search_pokemon(limit, offset)
            return result

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Error interno al buscar Pokémon: {e}")


# GET /api/v1/pokemon/{id_or_name} (Detalles completos)
@pokemon_router.get("/{id_or_name}")
async def get_pokemon_details(
        id_or_name: str,
        current_user: User = Depends(get_current_active_user)
):
    """Obtiene detalles completos de un Pokémon (stats, abilities, types, sprites)."""
    try:
        # get_pokemon debe retornar stats, abilities, types, sprites
        result = await pokeapi_service.get_pokemon(id_or_name)
        return result

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Error interno al obtener detalles: {e}")



@pokemon_router.get("/{id_or_name}/card",
                    response_class=Response,
                    responses={200: {"content": {"application/pdf": {}}}})
async def generate_pokemon_card(
        id_or_name: str,
        current_user: User = Depends(get_current_active_user)  # Requiere autenticación
):
    """Genera y descarga una ficha en formato PDF o imagen."""
    try:
        # 1. Obtener detalles completos (stats, abilities, types, sprites)
        pokemon_data = await pokeapi_service.get_pokemon(id_or_name)

        # 2. Lógica de generación del PDF (Placeholder ya que la generación real requiere librerías)

        pdf_content = f"--- FICHA POKÉMON: {pokemon_data['name'].upper()} ---\n"
        pdf_content += f"ID: {pokemon_data['id']}\n"
        pdf_content += f"Tipos: {', '.join(pokemon_data['types'])}\n"
        pdf_content += f"HP: {next((s['base_stat'] for s in pokemon_data['stats'] if s['stat']['name'] == 'hp'), 'N/A')}\n"
        pdf_content += f"Descripción de la especie (SIMULADA)\n"

        # Retorna archivo descargable
        return Response(content=pdf_content.encode('utf-8'),
                        media_type="application/pdf",
                        headers={"Content-Disposition": f"attachment; filename={id_or_name}_card.pdf"})

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al generar la ficha PDF.")