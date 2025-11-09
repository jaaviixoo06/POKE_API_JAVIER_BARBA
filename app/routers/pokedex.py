from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, func
from typing import List, Optional
from app.database import get_session
from app.dependencies import get_current_active_user
from app.models import User, PokedexEntry, PokedexEntryCreate, PokedexEntryUpdate, PokedexEntryRead
from app.services.pokeapi_service import pokeapi_service
from fastapi.responses import Response
from datetime import datetime


pokedex_router = APIRouter(prefix="/pokedex", tags=["Pokédex Personal (CRUD)"])


# [cite_start]POST /api/v1/pokedex (Añadir Pokémon) [cite: 192]
@pokedex_router.post("", response_model=PokedexEntryRead, status_code=status.HTTP_201_CREATED)
async def add_pokemon_to_pokedex(
        entry_data: PokedexEntryCreate,
        current_user: User = Depends(get_current_active_user),
        session: Session = Depends(get_session)
):
    # [cite_start]1. Validar que el pokemon_id existe en PokeAPI [cite: 200]
    try:
        pokemon_details = await pokeapi_service.get_pokemon(entry_data.pokemon_id)
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pokémon ID no válido en PokeAPI.")
        raise e

    # [cite_start]2. No permitir duplicados (mismo pokemon_id para el mismo usuario) [cite: 201]
    existing_entry = session.exec(
        select(PokedexEntry)
        .where(PokedexEntry.owner_id == current_user.id)
        .where(PokedexEntry.pokemon_id == entry_data.pokemon_id)
    ).first()

    if existing_entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este Pokémon ya existe en tu Pokédex.")

    # 3. Crear entrada
    new_entry = PokedexEntry(
        **entry_data.model_dump(exclude_unset=True),
        owner_id=current_user.id,
        pokemon_name=pokemon_details['name'],
        pokemon_sprite=pokemon_details['sprites']
    )

    session.add(new_entry)
    session.commit()
    session.refresh(new_entry)
    return new_entry


# [cite_start]GET /api/v1/pokedex (Listar Pokédex) [cite: 202]
@pokedex_router.get("", response_model=List[PokedexEntryRead])
async def list_pokedex(
        captured: Optional[bool] = Query(None, description="Filtro por capturados"),
        favorite: Optional[bool] = Query(None, description="Filtro por favoritos"),
        sort: Optional[str] = Query("pokemon_id",
                                    description="Campo de ordenación (pokemon_id, capture_date, pokemon_name)"),
        order: Optional[str] = Query("asc", description="Dirección de ordenación (asc/desc)"),
        limit: int = Query(20, gt=0),
        offset: int = Query(0, ge=0),
        current_user: User = Depends(get_current_active_user),
        session: Session = Depends(get_session)
):
    query = select(PokedexEntry).where(PokedexEntry.owner_id == current_user.id)

    #[cite_start]Filtros
    if captured is not None:
        query = query.where(PokedexEntry.is_captured == captured)
    if favorite is not None:
        query = query.where(PokedexEntry.favorite == favorite)

    # [cite_start]Ordenación
    sort_fields = {"pokemon_id": PokedexEntry.pokemon_id, "capture_date": PokedexEntry.capture_date,
                   "pokemon_name": PokedexEntry.pokemon_name}
    sort_column = sort_fields.get(sort, PokedexEntry.pokemon_id)

    if order.lower() == 'desc':
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # [cite_start]Paginación [cite: 206]
    query = query.offset(offset).limit(limit)

    entries = session.exec(query).all()
    return entries


# [cite_start]PATCH /api/v1/pokedex/{entry_id} (Actualizar entrada) [cite: 207]
@pokedex_router.patch("/{entry_id}", response_model=PokedexEntryRead)
def update_pokedex_entry(
        entry_id: int,
        entry_update: PokedexEntryUpdate,
        current_user: User = Depends(get_current_active_user),
        session: Session = Depends(get_session)
):
    entry = session.get(PokedexEntry, entry_id)

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrada no encontrada.")

    # [cite_start]Solo el propietario puede modificar [cite: 217]
    if entry.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="No tienes permiso para modificar esta entrada.")

    # Aplicar la actualización
    update_data = entry_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(entry, key, value)

    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


# [cite_start]DELETE /api/v1/pokedex/{entry_id} (Eliminar entrada) [cite: 218]
@pokedex_router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pokedex_entry(
        entry_id: int,
        current_user: User = Depends(get_current_active_user),
        session: Session = Depends(get_session)
):
    entry = session.get(PokedexEntry, entry_id)

    if not entry:
        return

        # [cite_start]Validar propiedad [cite: 220]
    if entry.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="No tienes permiso para eliminar esta entrada.")

    session.delete(entry)
    session.commit()
    return


# [cite_start]GET /api/v1/pokedex/export (Exportar) [cite: 221]
@pokedex_router.get("/export", response_class=Response)
def export_pokedex(
        format: str = Query("csv", description="Formato de exportación: pdf o csv"),
        captured: Optional[bool] = Query(None),
        favorite: Optional[bool] = Query(None),
        current_user: User = Depends(get_current_active_user),
        session: Session = Depends(get_session)
):
    # Lógica de filtros
    query = select(PokedexEntry).where(PokedexEntry.owner_id == current_user.id)
    if captured is not None:
        query = query.where(PokedexEntry.is_captured == captured)
    if favorite is not None:
        query = query.where(PokedexEntry.favorite == favorite)

    entries = session.exec(query).all()

    # Lógica de exportación
    if format.lower() == 'csv':
        csv_content = "ID,Pokemon ID,Nombre,Capturado,Favorito,Apodo\n"
        for e in entries:
            csv_content += f"{e.id},{e.pokemon_id},{e.pokemon_name},{e.is_captured},{e.favorite},{e.nickname if e.nickname else ''}\n"

        return Response(content=csv_content,
                        media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=pokedex_export.csv"})

    elif format.lower() == 'pdf':
        # [cite_start]Retorna archivo descargable [cite: 226]
        pdf_content = f"Exportación de Pokédex de {current_user.username} (PDF SIMULADO)\nTotal de entradas: {len(entries)}"
        return Response(content=pdf_content.encode('utf-8'),
                        media_type="application/pdf",
                        headers={"Content-Disposition": "attachment; filename=pokedex_export.pdf"})

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de exportación no válido.")


# [cite_start]GET /api/v1/pokedex/stats (Estadísticas) [cite: 228]
@pokedex_router.get("/stats")
async def get_pokedex_stats(
        current_user: User = Depends(get_current_active_user),
        session: Session = Depends(get_session)
):
    # Obtener totales del usuario
    total_entries = session.exec(select(PokedexEntry).where(PokedexEntry.owner_id == current_user.id)).all()

    captured_count = sum(1 for e in total_entries if e.is_captured)
    favorites_count = sum(1 for e in total_entries if e.favorite)

    # [cite_start]Asumimos que el total conocido es 150 para el cálculo del porcentaje [cite: 230]
    completion_percentage = (captured_count / 150) * 100 if 150 > 0 else 0

    return {
        "total_pokemon": len(total_entries),  # Total de entradas del usuario
        "captured": captured_count,
        "favorites": favorites_count,
        "completion_percentage": round(completion_percentage, 1),
        "most_common_type": "water (SIMULADO)",  # REQUIERE lógica de integración compleja
        "capture_streak_days": 7  # REQUIERE lógica de fechas
    }