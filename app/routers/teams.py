import json
import tempfile
from io import BytesIO
import requests
from PIL import Image
from fastapi import APIRouter, Depends, HTTPException, status
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy import delete
from sqlmodel import Session, select
from typing import List
from starlette.responses import FileResponse
from app.database import get_session
from app.dependencies import get_current_active_user
from app.models import User, Team, TeamMember, PokedexEntry, TeamCreate, TeamRead, TeamUpdate


from app.services.pokeapi_service import pokeapi_service

teams_router = APIRouter(prefix="/teams", tags=["Equipos de Batalla"])

MAX_TEAM_SIZE = 6  # Máximo 6 Pokémon [cite: 242]


# [cite_start]POST /api/v1/teams (Crear equipo) [cite: 238]
@teams_router.post("/", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
def create_team(
        team_data: TeamCreate,
        current_user: User = Depends(get_current_active_user),
        session: Session = Depends(get_session)
):
    # [cite_start]1. Validar tamaño del equipo (Máximo 6 Pokémon) [cite: 246]
    if len(team_data.pokemon_ids) > MAX_TEAM_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Un equipo no puede tener más de {MAX_TEAM_SIZE} Pokémon.")

    if not team_data.pokemon_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El equipo debe tener al menos un Pokémon.")

    # [cite_start]2. Validar que todos los Pokémon están en la Pokédex del usuario [cite: 245]
    pokedex_entries = session.exec(
        select(PokedexEntry).where(
            PokedexEntry.owner_id == current_user.id,
            # Aquí usamos PokedexEntry.id, asumiendo que pokemon_ids en TeamCreate son los IDs de la entrada de la Pokédex del usuario.
            PokedexEntry.id.in_(team_data.pokemon_ids)
        )
    ).all()

    if len(pokedex_entries) != len(team_data.pokemon_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Uno o más Pokémon no se encuentran en tu Pokédex personal.")

    # 3. Crear el equipo base
    new_team = Team(
        name=team_data.name,
        description=team_data.description,
        trainer_id=current_user.id
    )
    session.add(new_team)
    session.flush()

    # 4. Crear los miembros del equipo (TeamMember)
    for index, entry_id in enumerate(team_data.pokemon_ids):
        team_member = TeamMember(
            team_id=new_team.id,
            pokedex_entry_id=entry_id,
            position=index + 1  # Posición 1-6
        )
        session.add(team_member)

    session.commit()
    session.refresh(new_team)
    return new_team


# [cite_start]GET /api/v1/teams (Listar todos los equipos) [cite: 250]
@teams_router.get("/", response_model=List[TeamRead])
def list_teams(
        current_user: User = Depends(get_current_active_user),
        session: Session = Depends(get_session)
):
    # [cite_start]Lista todos los equipos del usuario [cite: 251]
    teams = session.exec(
        select(Team).where(Team.trainer_id == current_user.id)
    ).all()
    return teams


# [cite_start]PUT /api/v1/teams/{team_id} (Actualizar equipo) [cite: 252]
@teams_router.put("/{team_id}")
def update_team(
    team_id: int,
    team_data: TeamUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    # Obtener el equipo
    team = session.get(Team, team_id)
    if not team or team.trainer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipo no encontrado o no tienes permiso."
        )

    # 1️⃣ Actualizar nombre y descripción
    team.name = team_data.name
    team.description = team_data.description

    # 2️⃣ Validar miembros
    if len(team_data.pokemon_ids) > MAX_TEAM_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Un equipo no puede tener más de {MAX_TEAM_SIZE} Pokémon."
        )

    pokedex_entries = session.exec(
        select(PokedexEntry).where(
            PokedexEntry.owner_id == current_user.id,
            PokedexEntry.id.in_(team_data.pokemon_ids)
        )
    ).all()

    if len(pokedex_entries) != len(team_data.pokemon_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uno o más Pokémon no se encuentran en tu Pokédex personal."
        )

    # 3️⃣ Eliminar todos los miembros antiguos usando delete() correctamente
    delete_stmt = delete(TeamMember).where(TeamMember.team_id == team_id)
    session.exec(delete_stmt)
    session.flush()

    # 4️⃣ Añadir los nuevos miembros
    for index, entry_id in enumerate(team_data.pokemon_ids):
        new_member = TeamMember(
            team_id=team.id,
            pokedex_entry_id=entry_id,
            position=index + 1
        )
        session.add(new_member)

    # Guardar cambios
    session.add(team)
    session.commit()
    session.refresh(team)

    return team

# [cite_start]GET /api/v1/teams/{team_id}/export (Exportar equipo) [cite: 254]
@teams_router.get("/{team_id}/export", response_class=FileResponse)
async def export_team(
    team_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    team = session.get(Team, team_id)
    if not team or team.trainer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Equipo no encontrado o no tienes permiso.")

    members = session.exec(select(TeamMember).where(TeamMember.team_id == team_id)).all()
    if not members:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El equipo no tiene miembros.")

    # Crear PDF temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        pdf_path = tmp_file.name
        c = canvas.Canvas(pdf_path, pagesize=(600, 800))

        # Título del equipo
        c.setFont("Helvetica-Bold", 24)
        c.drawString(30, 770, f"Equipo: {team.name}")
        c.setFont("Helvetica", 16)
        c.drawString(30, 740, f"Descripción: {team.description}")

        y_position = 700
        combined_stats = {}

        type_colors = {
            'Fire': '#f08030', 'Water': '#6890f0', 'Grass': '#78c850', 'Electric': '#f8d030',
            'Ice': '#98d8d8', 'Fighting': '#c03028', 'Poison': '#a040a0', 'Ground': '#e0c068',
            'Flying': '#a890f0', 'Psychic': '#f85888', 'Bug': '#a8b820', 'Rock': '#b8a038',
            'Ghost': '#705898', 'Dragon': '#7038f8', 'Steel': '#b8b8d0', 'Fairy': '#ee99ac',
            'Normal': '#a8a878', 'Dark': '#705848'
        }

        for member in members:
            # Obtener datos reales del Pokémon
            entry_data = await pokeapi_service.get_pokemon(member.pokedex_entry_id)
            if isinstance(entry_data, str):
                entry_data = json.loads(entry_data)

            pokemon_name = entry_data.get("name", "N/A").capitalize()
            sprite_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{entry_data.get('id', 1)}.png"

            # Descargar imagen
            sprite_img = None
            response = requests.get(sprite_url)
            if response.status_code == 200:
                sprite_img = Image.open(BytesIO(response.content)).convert("RGBA")

            # Tipos
            types_list = [t.get("type", {}).get("name", "Normal").capitalize()
                          for t in entry_data.get("types", []) if isinstance(t, dict)]

            # Stats
            stats_list = entry_data.get("stats", [])
            stats = {s.get("stat", {}).get("name"): s.get("base_stat")
                     for s in stats_list if isinstance(s, dict)}

            # Combinar stats
            for stat_name, value in stats.items():
                combined_stats[stat_name] = combined_stats.get(stat_name, 0) + value

            # Dibujar sprite y datos
            c.setFont("Helvetica-Bold", 18)
            c.drawString(30, y_position, f"{pokemon_name} ({', '.join(types_list)})")

            if sprite_img:
                sprite_reader = ImageReader(sprite_img)
                c.drawImage(sprite_reader, 400, y_position - 50, width=80, height=80)

            c.setFont("Helvetica", 14)
            y_stats = y_position - 20
            for stat_name, value in stats.items():
                c.drawString(30, y_stats, f"{stat_name.capitalize()}: {value}")
                y_stats -= 15

            y_position -= 120
            if y_position < 100:
                c.showPage()
                y_position = 700

        # Estadísticas combinadas
        c.setFont("Helvetica-Bold", 20)
        c.drawString(30, y_position - 30, "Estadísticas combinadas del equipo:")
        y_stats = y_position - 60
        for stat_name, total in combined_stats.items():
            c.setFont("Helvetica", 16)
            c.drawString(30, y_stats, f"{stat_name.capitalize()}: {total}")
            y_stats -= 20

        c.save()

    return FileResponse(pdf_path, media_type="application/pdf",
                        filename=f"{team.name}_team.pdf")