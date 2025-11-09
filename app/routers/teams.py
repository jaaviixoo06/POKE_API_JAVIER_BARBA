# app/routers/teams.py - PARTE 2.3 GRUPO 4

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from typing import List, Optional
from app.database import get_session
from app.dependencies import get_current_active_user
from app.models import User, Team, TeamMember, PokedexEntry, TeamCreate, TeamRead, TeamUpdate
from fastapi.responses import Response

teams_router = APIRouter(prefix="/teams", tags=["Equipos de Batalla"])

MAX_TEAM_SIZE = 6  # Máximo 6 Pokémon [cite: 242]


# [cite_start]POST /api/v1/teams (Crear equipo) [cite: 238]
@teams_router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
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
@teams_router.get("", response_model=List[TeamRead])
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
@teams_router.put("/{team_id}") # Eliminamos response_model=TeamRead
def update_team(
    team_id: int,
    team_data: TeamUpdate,
        current_user: User = Depends(get_current_active_user),
        session: Session = Depends(get_session)
):
    team = session.get(Team, team_id)

    if not team or team.trainer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipo no encontrado o no tienes permiso.")

    # [cite_start]1. Actualizar nombre y descripción [cite: 253]
    team.name = team_data.name
    team.description = team_data.description

    # 2. Validar miembros (lógica similar a POST)
    if len(team_data.pokemon_ids) > MAX_TEAM_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Un equipo no puede tener más de {MAX_TEAM_SIZE} Pokémon.")

    pokedex_entries = session.exec(
        select(PokedexEntry).where(
            PokedexEntry.owner_id == current_user.id,
            PokedexEntry.id.in_(team_data.pokemon_ids)
        )
    ).all()

    if len(pokedex_entries) != len(team_data.pokemon_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Uno o más Pokémon no se encuentran en tu Pokédex personal.")

    # 3. Eliminar miembros viejos
    session.exec(select(TeamMember).where(TeamMember.team_id == team_id)).delete()
    session.flush()

    # 4. Añadir miembros nuevos
    for index, entry_id in enumerate(team_data.pokemon_ids):
        team_member = TeamMember(
            team_id=team.id,
            pokedex_entry_id=entry_id,
            position=index + 1
        )
        session.add(team_member)

    session.add(team)
    session.commit()
    session.refresh(team)
    return team


# [cite_start]GET /api/v1/teams/{team_id}/export (Exportar equipo) [cite: 254]
@teams_router.get("/{team_id}/export", response_class=Response)
def export_team(
        team_id: int,
        current_user: User = Depends(get_current_active_user),
        session: Session = Depends(get_session)
):
    team = session.get(Team, team_id)

    if not team or team.trainer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipo no encontrado o no tienes permiso.")

    # Lógica de exportación (Placeholder)
    pdf_content = f"--- EQUIPO DE BATALLA: {team.name.upper()} ---\n"
    pdf_content += f"Descripción: {team.description}\n"

    pdf_content += f"Miembros (Simulados - Fichas de los 6 Pokémon): [cite: 257]\n"

    pdf_content += f"Estadísticas Combinadas del equipo (Simulado): [cite: 258]\n"

    return Response(content=pdf_content.encode('utf-8'),
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={team.name}_team.pdf"})