import os
import tempfile
import json
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from starlette.responses import FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from reportlab.lib.utils import ImageReader
from app.services.pokeapi_service import pokeapi_service, logger
from app.dependencies import get_current_active_user
from app.models import User

limiter = Limiter(key_func=get_remote_address)
pokemon_router = APIRouter(prefix="/pokemon", tags=["Pokemon Search (Proxy)"])


# ---------------------------
# Endpoint de detalles
# ---------------------------
@pokemon_router.get("/{id_or_name}")
@limiter.limit("60/minute")
async def get_pokemon_details(
    id_or_name: str,
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    try:
        result = await pokeapi_service.get_pokemon(id_or_name)
        if result is None:
            # Pokémon no encontrado
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pokémon no encontrado")
        if isinstance(result, str):
            result = json.loads(result)
        return result
    except HTTPException:
        # Re-lanzamos excepciones HTTP (como el 404)
        raise
    except Exception as e:
        logger.error(f"Error al obtener detalles del Pokémon: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al obtener detalles: {e}"
        )



# ---------------------------
# Endpoint de carta Pokémon (PDF o PNG)
# ---------------------------
@pokemon_router.get("/{id_or_name}/card")
@limiter.limit("30/minute")
async def generate_pokemon_card(
        id_or_name: str,
        request: Request,
        format: str = Query(..., description="Formato obligatorio: 'pdf' o 'png'"),
        current_user: User = Depends(get_current_active_user)
):
    tmp_path = None
    try:
        # -------------------
        # ✅ Validar formato primero
        # -------------------
        fmt = format.lower()
        if fmt not in {"png", "pdf"}:
            raise HTTPException(
                status_code=400,
                detail="Formato no válido. Debe ser 'pdf' o 'png'."
            )

        # -------------------
        # Obtener datos del Pokémon (solo si formato válido)
        # -------------------
        pokemon_data = await pokeapi_service.get_pokemon(id_or_name)
        if isinstance(pokemon_data, str):
            pokemon_data = json.loads(pokemon_data)

        pokemon_name = pokemon_data.get("name", "N/A").capitalize()
        sprite_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_data.get('id', 1)}.png"

        stats_list = pokemon_data.get("stats", [])
        stats = {
            s.get("stat", {}).get("name", "N/A"): s.get("base_stat", "N/A")
            for s in stats_list if isinstance(s, dict)
        }
        types_list = [
            t.get("type", {}).get("name", "Normal").capitalize()
            for t in pokemon_data.get("types", []) if isinstance(t, dict)
        ]
        primary_type = types_list[0] if types_list else "Normal"

        type_colors = {
            'Fire': '#f08030', 'Water': '#6890f0', 'Grass': '#78c850', 'Electric': '#f8d030',
            'Ice': '#98d8d8', 'Fighting': '#c03028', 'Poison': '#a040a0', 'Ground': '#e0c068',
            'Flying': '#a890f0', 'Psychic': '#f85888', 'Bug': '#a8b820', 'Rock': '#b8a038',
            'Ghost': '#705898', 'Dragon': '#7038f8', 'Steel': '#b8b8d0', 'Fairy': '#ee99ac',
            'Normal': '#a8a878', 'Dark': '#705848'
        }
        bg_color = type_colors.get(primary_type, '#f0f0f0')

        # -------------------
        # Descargar sprite
        # -------------------
        sprite_img = None
        response = requests.get(sprite_url)
        if response.status_code == 200:
            sprite_img = Image.open(BytesIO(response.content)).convert("RGBA")

        # -------------------
        # Formato PNG
        # -------------------
        if fmt == "png":
            card_width, card_height = 400, 600
            card = Image.new("RGBA", (card_width, card_height), "#f0f0f0")
            draw = ImageDraw.Draw(card)

            # Marco exterior
            border_color = "#333333"
            draw.rectangle([0, 0, card_width - 1, card_height - 1], outline=border_color, width=8)

            # Cuadro central blanco
            draw.rectangle([10, 10, card_width - 10, card_height - 10], fill="white", outline=border_color, width=2)

            # Cuadro superior nombre + HP
            draw.rectangle([20, 20, card_width - 20, 70], fill=bg_color)
            try:
                font_title = ImageFont.truetype("arialbd.ttf", 26)
                font_stats = ImageFont.truetype("arial.ttf", 18)
            except Exception:
                font_title = ImageFont.load_default()
                font_stats = ImageFont.load_default()

            draw.text((30, 25), pokemon_name, fill="white", font=font_title)
            hp = stats.get("hp", "N/A")
            draw.text((card_width - 100, 25), f"HP {hp}", fill="white", font=font_stats)

            # Cuadro central para imagen
            img_box_top, img_box_bottom = 90, 350
            draw.rectangle([40, img_box_top, card_width - 40, img_box_bottom], outline=border_color, width=2)

            if sprite_img:
                sprite_resized = sprite_img.resize((200, 200))
                sprite_x = (card_width - sprite_resized.width) // 2
                sprite_y = img_box_top + (img_box_bottom - img_box_top - sprite_resized.height) // 2
                card.paste(sprite_resized, (sprite_x, sprite_y), sprite_resized.split()[3])

            # Cuadro inferior para stats y tipos
            footer_top, footer_bottom = 360, card_height - 20
            draw.rectangle([20, footer_top, card_width - 20, footer_bottom], outline=border_color, width=2)

            # Tipos
            y_types = footer_top + 10
            for i, t in enumerate(types_list):
                badge_color = type_colors.get(t, "#777")
                draw.rectangle([30 + i * 90, y_types, 100 + i * 90, y_types + 30], fill=badge_color)
                draw.text((35 + i * 90, y_types + 5), t, fill="white", font=font_stats)

            # Stats
            y_stats = y_types + 40
            for i, (stat_name, value) in enumerate(stats.items()):
                draw.text((30, y_stats + i * 25), f"{stat_name.capitalize()}: {value}", fill="black", font=font_stats)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                tmp_path = tmp_file.name
                card.save(tmp_file, "PNG")

            return FileResponse(tmp_path, media_type="image/png", filename=f"{pokemon_name}_card.png")

        # -------------------
        # Formato PDF
        # -------------------
        elif fmt == "pdf":
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_path = tmp_file.name
                c = canvas.Canvas(tmp_path, pagesize=(400, 600))

                # Fondo blanco y borde exterior
                c.setFillColor("white")
                c.rect(0, 0, 400, 600, fill=1)
                c.setStrokeColorRGB(0.2, 0.2, 0.2)
                c.setLineWidth(3)
                c.rect(5, 5, 390, 590, fill=0)

                # Cuadro superior nombre + HP
                c.setFillColor(bg_color)
                c.rect(20, 530, 360, 50, fill=1)
                c.setFillColor("white")
                c.setFont("Helvetica-Bold", 24)
                c.drawString(30, 545, pokemon_name)
                hp = stats.get("hp", "N/A")
                c.setFont("Helvetica", 16)
                c.drawString(300, 545, f"HP {hp}")

                # Cuadro central para imagen
                c.setStrokeColorRGB(0, 0, 0)
                c.rect(40, 280, 320, 240, fill=0)

                if sprite_img:
                    sprite_reader = ImageReader(sprite_img)
                    c.drawImage(sprite_reader, int(100), int(300), width=int(200), height=int(200))

                # Cuadro inferior stats y tipos
                c.rect(20, 20, 360, 250, fill=0)

                # Tipos
                x, y = 30, 230
                for t in types_list:
                    badge_color = type_colors.get(t, "#777")
                    c.setFillColor(badge_color)
                    c.rect(x, y, 70, 20, fill=1)
                    c.setFillColor("white")
                    c.setFont("Helvetica", 12)
                    c.drawString(x + 5, y + 4, t)
                    x += 90

                # Stats
                y_stats = 200
                c.setFillColor("black")
                c.setFont("Helvetica", 12)
                for stat_name, value in stats.items():
                    c.drawString(30, y_stats, f"{stat_name.capitalize()}: {value}")
                    y_stats -= 18

                c.showPage()
                c.save()

            return FileResponse(tmp_path, media_type="application/pdf", filename=f"{pokemon_name}_card.pdf")

    except HTTPException:
        raise
    except Exception as e:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        logger.error(f"Error al generar carta: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al generar la carta: {e}")
