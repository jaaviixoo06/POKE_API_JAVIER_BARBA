# app/main.py - CÓDIGO CONSOLIDADO COMPLETO Y PARTE 2.5 READY

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
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('pokedex_api.log'),logging.StreamHandler()]) # Log a consola # Log a archivo [cite: 309]
logger = logging.getLogger("pokedex_api")  # ⬅️ Usar nombre del logger global

# --- CONFIGURACIÓN DE RATE LIMITING (SLOWAPI) ---
limiter = Limiter(key_func=get_remote_address)


# --- LIFESPAN CONTEXT MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    create_db_and_tables()
    logger.info("Database initialized.")
    yield
    logger.info("Shutting down...")


# --- INICIALIZACIÓN DE LA APP (Instancia FastAPI) ---
app = FastAPI(
    title="Pokédex Personal API",
    version="v1.0.0",
    description="API REST para la gestión de Pokédex y Equipos de Batalla.",
    lifespan=lifespan
)

# Manejador de errores para Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- MIDDLEWARE DE CORS (Parte 2.4 - Configuración Requerida) ---
# Orígenes permitidos [cite: 265-269]
origins = [
    "http://localhost:3000",  # React dev
    "http://localhost:5173",  # Vite dev
    "https://tu-dominio.com"  # Producción
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],  # ⬅️ Métodos especificados [cite: 271]
    allow_headers=["Authorization", "Content-Type"],  # ⬅️ Headers especificados [cite: 272]
    max_age=3600,
)


# --- MIDDLEWARE DE LOGGING (Ejemplo de Middleware de Logging - Parte 2.6) ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Registra todas las peticiones HTTP entrantes y salientes."""

    start_time = datetime.utcnow()

    # Logs requeridos: Peticiones HTTP (método, path)
    logger.info(f"Request: {request.method} {request.url.path}")

    response = await call_next(request)

    duration = (datetime.utcnow() - start_time).total_seconds()

    # Logs requeridos: Respuesta HTTP (status, duración)
    logger.info(  f"Response: {response.status_code} |" f"Duration: {duration:.3f}s")

    return response


# --- CONFIGURACIÓN DE RUTAS Y VERSIONADO (Parte 2.7) ---

v1_router = APIRouter(prefix="/api/v1")

# Versión 2 Router
v2_router = APIRouter(prefix="/api/v2")

v1_router.include_router(auth_router, tags=["Authentication"])
v1_router.include_router(pokemon_router, tags=["Pokemon Search (Proxy)"])
v1_router.include_router(pokedex_router, tags=["Pokédex Personal (CRUD)"])
v1_router.include_router(teams_router, tags=["Equipos de Batalla"])

app.include_router(v1_router)
app.include_router(v2_router) # La v2 no tiene rutas funcionales aún, pero su estructura está lista.


# --- RUTA DE SALUD (OPCIONAL) ---
@app.get("/")
def read_root():
    return {"message": "Pokédex Personal API is running. Access /docs for documentation."}