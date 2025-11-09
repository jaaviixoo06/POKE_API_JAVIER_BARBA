# app/config.py

from os import getenv
from dotenv import load_dotenv

# Cargar variables del archivo .env (si existe)
load_dotenv()

# Clave secreta en variable de entorno (Punto 2.2)
SECRET_KEY = getenv("SECRET_KEY", "CLAVE_DEFAULT_NO_SEGURA")
ALGORITHM = getenv("ALGORITHM", "HS256")

# Constantes de expiración (Punto 2.2)
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 horas
REFRESH_TOKEN_EXPIRE_DAYS = 7 # 7 días (Bonus)