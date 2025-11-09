# app/main.py - CÓDIGO CONSOLIDADO COMPLETO

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, Request, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.database import create_db_and_tables
from app.routers.auth import auth_router 
from app.routers.pokemon import pokemon_router 
from app.routers.pokedex import pokedex_router
from app.routers.teams import teams_router


# Configuración del Logger (Opcional, pero bueno para depuración)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE RATE LIMITING (SLOWAPI) ---
limiter = Limiter(key_func=get_remote_address)


# --- LIFESPAN CONTEXT MANAGER (Manejo de Ciclo de Vida) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Función que se ejecuta al inicio y fin de la aplicación.
    Inicializa la base de datos al arrancar.
    """
    logger.info("Starting up...")
    create_db_and_tables()
    logger.info("Database initialized.")
    yield # Aquí se ejecuta la aplicación
    logger.info("Shutting down...")


# --- INICIALIZACIÓN DE LA APP (Instancia FastAPI) ---
# Se pasa el lifespan a la instancia 'app'
app = FastAPI(
    title="Pokédex Personal API",
    version="v1.0.0",
    description="API REST para la gestión de Pokédex y Equipos de Batalla.",
    lifespan=lifespan 
)

# Manejador de errores para Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# --- MIDDLEWARE DE CORS (Parte 2.1) ---
# Ajustar en entorno productivo
origins = [
    "http://localhost:8080",  # Frontend local (ejemplo)
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MIDDLEWARE DE TOKEN/SESIÓN (Parte 2.1, si se implementó) ---
@app.middleware("http")
async def token_check_middleware(request: Request, call_next):
    """Middleware para verificar el token en cabeceras de respuesta (si aplica)."""
    # Lógica de verificación o manejo de sesión (opcional, pero útil para la práctica)
    response = await call_next(request)
    # Ejemplo de acción post-request:
    # if response.status_code == status.HTTP_200_OK:
    #     fastapi_session_token_check(request, response)
    return response


# --- CONFIGURACIÓN DE RUTAS Y VERSIONADO (Parte 2.3) ---

v1_router = APIRouter(prefix="/api/v1")

# ⬅️ IMPORTANTE: Incluir la instancia del APIRouter sin paréntesis.
v1_router.include_router(auth_router, tags=["Authentication"]) 
v1_router.include_router(pokemon_router, tags=["Pokemon Search (Proxy)"]) 
v1_router.include_router(pokedex_router, tags=["Pokédex Personal (CRUD)"])
v1_router.include_router(teams_router, tags=["Equipos de Batalla"])

app.include_router(v1_router)

# --- RUTA DE SALUD (OPCIONAL) ---
@app.get("/")
def read_root():
    return {"message": "Pokédex Personal API is running. Access /docs for documentation."}