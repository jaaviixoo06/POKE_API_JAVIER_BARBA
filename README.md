# 🐾 Pokédex Personal – POKE_API_JAVIER_BARBA


## Video explicativo mostrando funcionalidad 

--> https://www.loom.com/share/e08f7cac7d0f4306a32fb1e87a64ac1b <--
## 📖 Descripción

Pokédex Personal que combina:

- Cliente REST que consume información de la PokeAPI pública.

- Servidor propio que expone API REST para gestionar colecciones de Pokémon por usuario.

Incluye funcionalidades clave:

- Autenticación JWT

- CORS

- Rate limiting

- Logging

- Versionado de API

- Buenas prácticas de seguridad

- Testing automatizado

---

## 🌟 Contexto

Esta aplicación simula un entorno interactivo para entrenadores Pokémon, permitiendo:

-  Explorar Pokémon

-  Buscar Pokémon usando la PokeAPI oficial.

-  Gestión de la Pokédex

-  Construir y administrar tu Pokédex personal.

-  Marcar Pokémon como capturados.

-  Compartir y comparar

-  Compartir estadísticas de colección con otros usuarios.

-  Equipos de batalla

- Crear y gestionar equipos de hasta 6 Pokémon.

---

## 🏗️ Estructura del Proyecto

📦 **POKE_API_JAVIER_BARBA/**  
 ┣ 📂 **.venv/** – Entorno virtual  
 ┣ 📂 **app/** – Código principal  
 ┃ ┣ 📂 **routers/** – Endpoints de la API (`auth`, `pokedex`, `pokemon`, `teams`)  
 ┃ ┣ 📂 **services/** – Servicios externos (PokeAPI)  
 ┃ ┣ `main.py` – Entrada FastAPI  
 ┃ ┣ `models.py` – Modelos SQLModel  
 ┃ ┣ `database.py` – Conexión DB  
 ┃ ┣ `config.py` – Variables de configuración  
 ┃ ┣ `auth.py` – Funciones de hashing y JWT  
 ┃ ┗ `utils.py` – Funciones auxiliares  
 ┣ 📂 **Tests/** – Tests con pytest y coverage  
 ┣ `.env.example` – Variables de entorno  
 ┣ `requirements.txt` – Dependencias pip  
 ┣ `README.md` – Documentación  
 ┗ `database.db` – Base de datos SQLite  

> ✅ Estructura completa más detallada disponible en el bloque de proyecto.

---

## ⚙️ Tecnologías Principales

- FastAPI  
- SQLAlchemy + MySQL/SQLite  
- JWT para autenticación  
- SlowAPI para rate limiting  
- Pytest para testing  
- ReportLab y PIL para generación de cartas PDF/PNG  

---

## 💻 Requisitos del Sistema

- Python >= 3.14  
- SQLite o MySQL  
- pip  

---

## 🛠️ Instalación

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/pokedex-api.git
cd pokedex-api

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

```

## 🔧 Configuración
```bash
DATABASE_URL=sqlite:///./database.db
SECRET_KEY="1';4Z8H_gf!]T~!pG+.EV`;46yoGEaZRSje,>#mF;l"
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_MINUTES=43200
```
## 🚀 Ejecución del Servidor
```bash
uvicorn app.main:app --reload
#(Accede a la documentación interactiva en http://localhost:8000/docs .)
````
## 🧪 Testing
```bash
#Ejecutar tests con pytest y generar cobertura:
pytest --cov=app tests/
```
## 🔐 Autenticación API

| Endpoint         | Método | Auth | Descripción                                   |
| ---------------- | ------ | ---- | --------------------------------------------- |
| `/auth/register` | POST   | No   | Registrar un usuario nuevo.                   |
| `/auth/login`    | POST   | No   | Login y obtención de access & refresh tokens. |
| `/auth/me`       | GET    | Sí   | Obtener perfil del usuario autenticado.       |
| `/auth/refresh`  | POST   | No   | Renovar access token usando refresh token.    |

❗**Ejemplo:**

1º Registro de usuario
```bash
#cURL:

- curl -X POST http://localhost:8000/auth/register \
 -  -H "Content-Type: application/json" \
 -  -d '{"username": "ash", "email": "ash@pokemon.com", "password": "pikachu123"}'
```
```bash
#Python requests:

import requests
data = {"username": "ash", "email": "ash@pokemon.com", "password": "pikachu123"}
resp = requests.post("http://localhost:8000/auth/register", json=data)
print(resp.json())
```
2ºLogin
```bash
#cURL:
- curl -X POST http://localhost:8000/auth/login \
 -  -F "username=ash" -F "password=pikachu123"
```
```bash
#Python requests:

import requests
resp = requests.post( "http://localhost:8000/auth/login",data={"username": "ash", "password": "pikachu123"})
tokens = resp.json()
print(tokens)
```
## 🗂️ Pokédex API
| Endpoint                           | Método | Descripción                                  |
| --------------------------------- | ------ | -------------------------------------------- |
| `/pokedex`                         | POST   | Añadir Pokémon a la Pokédex del usuario      |
| `/pokedex`                         | GET    | Listar entradas con filtros (capturados, favoritos) |
| `/pokedex/{entry_id}`              | PATCH  | Actualizar entrada (capturado, favorito, apodo) |
| `/pokedex/{entry_id}`              | DELETE | Eliminar entrada                             |
| `/pokedex/export?format=csv|pdf`   | GET    | Exportar Pokédex                             |
| `/pokedex/stats`                    | GET    | Obtener estadísticas de colección            |


❗**Ejemplo:**

1º **Añadir Pokémon**
```bash
#cURL:
curl -X POST http://localhost:8000/pokedex \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-H "Content-Type: application/json" \
-d '{"pokemon_id": 25, "is_captured": true, "favorite": true, "nickname": "Pika"}'
```
```bash
#Python requests:
import requests
headers = {"Authorization": f"Bearer {token}"}
data = {"pokemon_id": 25, "is_captured": True, "favorite": True, "nickname": "Pika"}
resp = requests.post("http://localhost:8000/pokedex", json=data, headers=headers)
print(resp.json())
```
2º **Exportar CSV**
```bash
curl -X GET "http://localhost:8000/pokedex/export?format=csv" \
-H "Authorization: Bearer $ACCESS_TOKEN"
```
### 🔎 Pokémon Search (Proxy PokeAPI)

| Endpoint                                    | Método | Auth | Descripción                    |                                    |
|---------------------------------------------| - | ---- | ------------------------------ | ---------------------------------- |
| `/pokemon/{id_or_name}`                     | GET | Sí   | Obtener detalles de un Pokémon |                                    |
| `/pokemon/{id_or_name}/card?format=pdf(png)` |   GET  | Sí                             | Generar carta Pokémon en PDF o PNG |


❗**Ejemplo:**

1º **Obtener detalles**
```bash
resp = requests.get(f"http://localhost:8000/pokemon/25", headers={"Authorization": f"Bearer {token}"})
print(resp.json())
```
2º **Carta Pokémon PDF**
```bash
resp = requests.get("http://localhost:8000/pokemon/25/card?format=pdf",
                    headers={"Authorization": f"Bearer {token}"})
with open("pikachu_card.pdf", "wb") as f: f.write(resp.content)
```

3º **Carta Pokémon PNG**
```bash
resp = requests.get("http://localhost:8000/pokemon/25/card?format=png",
                    headers={"Authorization": f"Bearer {token}"})
with open("pikachu_card.png", "wb") as f: f.write(resp.content)
```

## ⚔️ Equipos de Batalla

| Endpoint                  | Método | Auth | Descripción                                 |
| ------------------------- | ------ | ---- | ------------------------------------------- |
| `/teams`                  | POST   | Sí   | Crear un equipo de batalla (máx. 6 Pokémon) |
| `/teams`                  | GET    | Sí   | Listar equipos del usuario                  |
| `/teams/{team_id}`        | PUT    | Sí   | Actualizar un equipo existente              |
| `/teams/{team_id}/export` | GET    | Sí   | Exportar equipo en PDF                      |


❗**Ejemplo:**

1º Crear equipo
```bash
- data = {"name": "Team Ash", "description": "Mi equipo", "pokemon_ids": [1, 4, 7]}
- resp = requests.post("http://localhost:8000/teams", json=data, headers={"Authorization": f"Bearer {token}"})
- print(resp.json())
```
## 🛡️ Seguridad
| Medida de Seguridad        | Descripción                                                             |
| -------------------------- | ----------------------------------------------------------------------- |
| **JWT**                    | Autenticación con tokens JWT, con expiración configurable               |
| **Hasheo seguro**          | SHA-256 + bcrypt/sha256_crypt para proteger contraseñas                 |
| **Rate limiting**          | Protege endpoints críticos: `/auth/register`, `/auth/login`, `/pokemon` |
| **Validaciones**           | Regex para emails y passwords, política de contraseñas estricta         |
| **Control de permisos**    | Cada acción verifica que el recurso pertenece al usuario                |
| **CORS y headers seguros** | Configuración de CORS y headers seguros habilitada en FastAPI           |


## 🚀 Mejoras Futuras
| Mejora Futuras                  | Descripción                                                |
| ------------------------------- | ---------------------------------------------------------- |
| **OAuth2 Social Login**         | Integrar login social con Google o Discord                 |
| **Webhooks en tiempo real**     | Añadir webhooks para estadísticas y eventos en tiempo real |
| **Generación avanzada de PDFs** | Mejorar PDFs con gráficos y visualización de estadísticas  |
| **Notificaciones push**         | Alertas cuando se capturan Pokémon raros                   |
| **Soporte multilenguaje**       | UI y mensajes de error disponibles en varios idiomas       |
























