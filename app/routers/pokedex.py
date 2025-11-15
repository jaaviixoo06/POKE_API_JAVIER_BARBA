import csv
import io
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from reportlab.pdfgen import canvas
from sqlalchemy import func
from sqlmodel import Session, select
from typing import List, Optional, Counter
from app.database import get_session
from app.dependencies import get_current_active_user
from app.models import User, PokedexEntry, PokedexEntryCreate, PokedexEntryUpdate, PokedexEntryRead
from app.services.pokeapi_service import pokeapi_service
from fastapi.responses import Response

pokedex_router = APIRouter(prefix="/pokedex", tags=["Pokédex Personal (CRUD)"])

# ---------------- POST /pokedex ----------------
@pokedex_router.post("", response_model=PokedexEntryRead, status_code=status.HTTP_201_CREATED)
async def add_pokemon_to_pokedex(
        entry_data: PokedexEntryCreate,
        current_user: User = Depends(get_current_active_user),
        session: Session = Depends(get_session)
):
    # 1. Validar que el pokemon_id existe en PokeAPI
    try:
        pokemon_details = await pokeapi_service.get_pokemon(entry_data.pokemon_id)
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pokémon ID no válido en PokeAPI.")
        raise e

    # 2. No permitir duplicados
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

    # ---------------- Actualizar racha de captura ----------------
    if new_entry.is_captured:
        today = datetime.utcnow().date()

        # Última captura del usuario
        last_captured_entry = session.exec(
            select(PokedexEntry)
            .where(PokedexEntry.owner_id == current_user.id)
            .where(PokedexEntry.is_captured == True)
            .order_by(PokedexEntry.capture_date.desc())
        ).first()

        if last_captured_entry and last_captured_entry.capture_date:
            last_date = last_captured_entry.capture_date.date()
            delta_days = (today - last_date).days
            if delta_days == 0:
                # Ya capturó hoy → streak no cambia
                pass
            elif delta_days == 1:
                # Incrementar racha +1, máximo 7
                current_user.capture_streak = min((current_user.capture_streak or 0) + 1, 7)
            else:
                # Perdió la racha → reiniciamos a 1
                current_user.capture_streak = 1
        else:
            # Primera captura → iniciar streak
            current_user.capture_streak = 1

        session.add(current_user)
        session.commit()

    return new_entry


# ---------------- GET /pokedex ----------------
@pokedex_router.get("", response_model=List[PokedexEntryRead])
async def list_pokedex(
        captured: Optional[bool] = Query(None, description="Filtro por capturados"),
        favorite: Optional[bool] = Query(None, description="Filtro por favoritos"),
        sort: Optional[str] = Query("pokemon_id", description="Campo de ordenación (pokemon_id, capture_date, pokemon_name)"),
        order: Optional[str] = Query("asc", description="Dirección de ordenación (asc/desc)"),
        limit: int = Query(20, gt=0),
        offset: int = Query(0, ge=0),
        current_user: User = Depends(get_current_active_user),
        session: Session = Depends(get_session)
):
    query = select(PokedexEntry).where(PokedexEntry.owner_id == current_user.id)

    if captured is not None:
        query = query.where(PokedexEntry.is_captured == captured)
    if favorite is not None:
        query = query.where(PokedexEntry.favorite == favorite)

    sort_fields = {"pokemon_id": PokedexEntry.pokemon_id, "capture_date": PokedexEntry.capture_date,
                   "pokemon_name": PokedexEntry.pokemon_name}
    sort_column = sort_fields.get(sort, PokedexEntry.pokemon_id)

    if order.lower() == 'desc':
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    query = query.offset(offset).limit(limit)

    entries = session.exec(query).all()
    return entries


# ---------------- PATCH /pokedex/{entry_id} ----------------
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

    if entry.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para modificar esta entrada.")

    update_data = entry_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(entry, key, value)

    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


# ---------------- DELETE /pokedex/{entry_id} ----------------
@pokedex_router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pokedex_entry(
        entry_id: int,
        current_user: User = Depends(get_current_active_user),
        session: Session = Depends(get_session)
):
    entry = session.get(PokedexEntry, entry_id)

    if not entry:
        return

    if entry.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para eliminar esta entrada.")

    session.delete(entry)
    session.commit()
    return


# ---------------- GET /pokedex/export ----------------
@pokedex_router.get("/export", response_class=Response)
def export_pokedex(
        format: str = Query("csv", description="Formato de exportación: pdf o csv"),
        captured: Optional[bool] = Query(None),
        favorite: Optional[bool] = Query(None),
        current_user: User = Depends(get_current_active_user),
        session: Session = Depends(get_session)
):
    query = select(PokedexEntry).where(PokedexEntry.owner_id == current_user.id)
    if captured is not None:
        query = query.where(PokedexEntry.is_captured == captured)
    if favorite is not None:
        query = query.where(PokedexEntry.favorite == favorite)

    entries = session.exec(query).all()

    if format.lower() == 'csv':
        # Usamos StringIO para crear un CSV en memoria
        output = io.StringIO()
        writer = csv.writer(output)
        # Cabecera
        writer.writerow(["ID", "Pokemon ID", "Nombre", "Capturado", "Favorito", "Apodo"])
        # Filas
        for e in entries:
            writer.writerow([
                e.id,
                e.pokemon_id,
                e.pokemon_name,
                e.is_captured,
                e.favorite,
                e.nickname or ""
            ])
        csv_content = output.getvalue()
        output.close()

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=pokedex_export.csv"}
        )


    elif format.lower() == 'pdf':

        # PDF sencillo usando reportlab

        pdf_buffer = io.BytesIO()

        c = canvas.Canvas(pdf_buffer)

        c.setFont("Helvetica", 14)

        c.drawString(50, 800, f"Exportación de Pokédex de {current_user.username}")

        c.setFont("Helvetica", 12)

        c.drawString(50, 780, f"Total de entradas: {len(entries)}")

        y = 750

        for e in entries:

            text = f"ID: {e.id}, Pokemon ID: {e.pokemon_id}, Nombre: {e.pokemon_name}, Capturado: {'Sí' if e.is_captured else 'No'}, Favorito: {'Sí' if e.favorite else 'No'}, Apodo: {e.nickname or ''}"

            c.drawString(50, y, text)

            y -= 20

            if y < 50:
                c.showPage()

                c.setFont("Helvetica", 12)

                y = 800

        c.save()

        pdf_buffer.seek(0)

        return Response(

            content=pdf_buffer.read(),

            media_type="application/pdf",

            headers={"Content-Disposition": "attachment; filename=pokedex_export.pdf"}

        )

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de exportación no válido.")


# ---------------- GET /pokedex/stats ----------------
@pokedex_router.get("/stats")
async def get_pokedex_stats(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    # Obtener todas las entradas del usuario
    entries = session.exec(
        select(PokedexEntry).where(PokedexEntry.owner_id == current_user.id)
    ).all()

    if not entries:
        return {
            "total_pokemon": 0,
            "captured": 0,
            "favorites": 0,
            "completion_percentage": 0.0,
            "most_common_type": None,
            "capture_streak_days": 0
        }

    captured_entries = [e for e in entries if e.is_captured]
    favorites_entries = [e for e in entries if e.favorite]

    # Completion percentage
    total_pokemon_db = session.exec(select(func.count(PokedexEntry.id))).one()
    completion_percentage = (len(captured_entries) / total_pokemon_db) * 100 if total_pokemon_db > 0 else 0

    # Obtener tipos de Pokémon usando PokeAPI
    types_list = []
    for e in captured_entries:
        try:
            poke_data = await pokeapi_service.get_pokemon(e.pokemon_id)
            poke_types = [t["type"]["name"].capitalize() for t in poke_data.get("types", [])]
            types_list.extend(poke_types)
        except Exception:
            continue

    most_common_type = Counter(types_list).most_common(1)[0][0] if types_list else None

    # ----------------------------------------
    # CALCULAR LA RAZA DIARIA (streak)
    # ----------------------------------------
    today = datetime.utcnow().date()
    last_capture_date = current_user.last_capture_date.date() if current_user.last_capture_date else None
    streak = current_user.capture_streak or 0

    # Caso: primer Pokémon capturado o streak reseteada
    if last_capture_date is None or last_capture_date < today - timedelta(days=1):
        streak = 0

    # Si capturó hoy, la racha no se incrementa (ya se contó). Si capturó ayer, se suma 1
    if last_capture_date == today - timedelta(days=1):
        streak = min(streak + 1, 7)  # max 7
    elif last_capture_date is None or last_capture_date < today:
        streak = 1  # primer Pokémon de la nueva racha

    # Guardar los valores actualizados en la DB si han cambiado
    if streak != current_user.capture_streak or last_capture_date != current_user.last_capture_date:
        current_user.capture_streak = streak
        current_user.last_capture_date = datetime.utcnow()
        session.add(current_user)
        session.commit()
        session.refresh(current_user)

    return {
        "total_pokemon": len(entries),
        "captured": len(captured_entries),
        "favorites": len(favorites_entries),
        "completion_percentage": round(completion_percentage, 1),
        "most_common_type": most_common_type,
        "capture_streak_days": streak
    }