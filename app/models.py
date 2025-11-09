# app/models.py

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from pydantic import EmailStr, conint


# -------------------------------------------------------------
# --- 1. Schemas de Pydantic (Request/Response) - Definidos primero
# -------------------------------------------------------------

class UserBase(SQLModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserRead(UserBase):
    id: int
    created_at: datetime
    is_active: bool


class PokedexEntryCreate(SQLModel):
    pokemon_id: int
    nickname: Optional[str] = Field(default=None, max_length=50)
    is_captured: Optional[bool] = Field(default=False)


class PokedexEntryUpdate(SQLModel):
    is_captured: Optional[bool] = None
    capture_date: Optional[datetime] = None
    nickname: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=500)
    favorite: Optional[bool] = None


class PokedexEntryRead(SQLModel):
    id: int
    pokemon_id: int
    pokemon_name: str
    pokemon_sprite: str
    is_captured: bool
    favorite: bool
    nickname: Optional[str]


class TeamCreate(SQLModel):
    name: str = Field(max_length=100)
    description: Optional[str] = None
    pokemon_ids: List[int]


class TeamRead(SQLModel):
    id: int
    name: str
    description: Optional[str]
    trainer_id: int


# -------------------------------------------------------------
# --- 2. Modelos SQLModel (table=True) - Definidos después
# -------------------------------------------------------------

class User(SQLModel, table=True):
    """Usuario del sistema"""
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, min_length=3, max_length=50)
    email: EmailStr = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

    #Relaciones
    pokedex_entries: List["PokedexEntry"] = Relationship(back_populates="owner")
    teams: List["Team"] = Relationship(back_populates="trainer")


class PokedexEntry(SQLModel, table=True):
    """Entrada en la Pokédex de un usuario"""
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id")
    pokemon_id: int = Field(index=True)  # ID en PokeAPI
    pokemon_name: str
    pokemon_sprite: str  #URL de la imagen
    is_captured: bool = Field(default=False)
    capture_date: Optional[datetime] = None
    nickname: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=500)
    favorite: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    #Relaciones
    owner: User = Relationship(back_populates="pokedex_entries")
    team_members: List["TeamMember"] = Relationship(back_populates="pokedex_entry")


class Team(SQLModel, table=True):
    """Equipo de batalla (máximo 6 Pokémon)"""
    id: Optional[int] = Field(default=None, primary_key=True)
    trainer_id: int = Field(foreign_key="user.id")
    name: str = Field(max_length=100)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    #Relaciones
    trainer: User = Relationship(back_populates="teams")
    members: List["TeamMember"] = Relationship(back_populates="team")


class TeamMember(SQLModel, table=True):
    """Relación muchos a muchos entre Team y PokedexEntry"""
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id")
    pokedex_entry_id: int = Field(foreign_key="pokedexentry.id")
    position: conint(ge=1, le=6) = Field(ge=1, le=6)  # Posición en el equipo (1-6)

    # Relaciones
    team: Team = Relationship(back_populates="members")
    pokedex_entry: PokedexEntry = Relationship(back_populates="team_members")


class TeamUpdate(SQLModel):
    # Usamos SQLModel (no TeamCreate) y todos los campos son Optional
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    # Esto es el payload de los IDs a actualizar, NO una relación SQLModel
    pokemon_ids: Optional[List[int]] = None