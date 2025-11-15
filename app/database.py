#app/database.py

from sqlmodel import create_engine, Session, SQLModel
from typing import Generator


#Nombre de la base de datos SQLite (se crea en la raíz del proyecto)
sqlite_file_name = "database.db"

#URL de conexión, usando la ruta relativa del archivo
sqlite_url = f"sqlite:///{sqlite_file_name}"

# Configuración del motor de la base de datos
# El 'connect_args' es necesario para que SQLite funcione con múltiples hilos de FastAPI
engine = create_engine(sqlite_url, echo=True, connect_args={"check_same_thread": False})

def create_db_and_tables():
    """
    Función que se llama al iniciar la aplicación (en el 'lifespan' de main.py).
    Crea la base de datos y todas las tablas definidas en los modelos (User, PokedexEntry, etc.).
    """
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """
    Generador de sesión de base de datos para usar como dependencia en FastAPI.
    Asegura que la sesión se cierra automáticamente después de cada solicitud.
    """
    with Session(engine) as session:
        yield session

