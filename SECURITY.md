## 🔐 Consideraciones de Seguridad – Pokédex Personal
### 1️⃣ Autenticación

La aplicación utiliza JWT (JSON Web Tokens) para autenticación, con las siguientes características:

- Access token: válido 24 horas (configurable vía `ACCESS_TOKEN_EXPIRE_MINUTES`).  
- Refresh token: válido 30 días (configurable vía `REFRESH_TOKEN_EXPIRE_MINUTES`).  
- Tokens firmados con HS256 y `SECRET_KEY` seguro desde variables de entorno.  
- Se valida:
  - Token no expirado (`exp`).
  - `sub` (username) y `user_id` existen en la DB.
  - Token tiene el tipo correcto (`access` o `refresh`).
- Separación de access y refresh tokens para minimizar riesgo de exposición y permitir revocación.


### 2️⃣ Contraseñas

- Hashing seguro: SHA-256 + sha256_crypt (passlib) → evita límite de 72 bytes de bcrypt y permite migraciones futuras.  
- Política de contraseñas:
  - Mínimo 8 caracteres.
  - Al menos 1 letra mayúscula.
  - Al menos 1 número.
  - Recomendable: incluir caracteres especiales para mayor seguridad.


Esta política se valida en registro y actualización de usuarios.

### 3️⃣ Rate Limiting

Se protege contra ataques de fuerza bruta y abuso de endpoints críticos usando SlowAPI:

| Endpoint                   | Límite          | Justificación                                         |
|-----------------------------|----------------|-------------------------------------------------------|
| `/auth/register`            | 5 requests/hora | Evita creación masiva de cuentas.                    |
| `/auth/login`               | 10 requests/min | Limita intentos de login y ataques de fuerza bruta. |
| Otros endpoints críticos    | Configurable    | Se pueden establecer límites según carga y riesgo.  |

Respuestas ante límite excedido devuelven código 429 Too Many Requests.

### 4️⃣ CORS (Cross-Origin Resource Sharing)
- Orígenes permitidos: `http://localhost:3000`, `http://localhost:5173`, `https://tu-dominio.com`.  
- Métodos: GET, POST, PUT, PATCH, DELETE.  
- Headers permitidos: Authorization, Content-Type.  
- `allow_credentials=True` habilitado solo para cookies y autenticación segura.  
> Esto bloquea solicitudes desde dominios no autorizados, evitando ataques cross-site.


Métodos permitidos --> GET, POST, PUT, PATCH, DELETE

Headers permitidos -->  Authorization, Content-Type

allow_credentials=True --> habilitado solo para cookies y autenticación segura.

Esto evita solicitudes desde dominios no autorizados.

### 5️⃣ Variables de Entorno

- Se usan variables de entorno para evitar exponer información sensible en código fuente.  
- Contienen:
  - SECRET_KEY → firma de JWT.
  - DATABASE_URL → conexión a la DB.
  - Expiraciones de tokens: ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_MINUTES.
- Deben guardarse en `.env` fuera del repositorio, con permisos restringidos.  
- Nunca exponerlas en logs ni en errores HTTP.


### 6️⃣ Mitigación de Vulnerabilidades OWASP Top 10

| Vulnerabilidad OWASP                   | Mitigación implementada                                                      |
|---------------------------------------|----------------------------------------------------------------------------|
| A1: Broken Access Control              | Dependencias verifican propiedad de recursos.                               |
| A2: Cryptography Failures              | Hashing seguro (SHA-256 + sha256_crypt) y JWT firmado.                      |
| A3: Injection                          | Uso de SQLModel con parámetros seguros; no hay concatenación de queries.    |
| A4: Insecure Design                     | Validaciones Pydantic y manejo centralizado de errores.                     |
| A5: Security Misconfiguration          | CORS restringido, rate limiting activo, logging controlado.                 |
| A6: Vulnerable Components              | Dependencias actualizadas y revisadas.                                      |
| A7: Identification & Authentication Failures | Política de contraseñas estricta y expiración de tokens.                  |
| A8: Software and Data Integrity Failures | No aplica (no hay código externo no verificado).                           |
| A9: Security Logging & Monitoring Failures | Logging de requests HTTP y errores críticos.                               |
| A10: Server-Side Request Forgery       | No expone endpoints de fetch externo directo.                                |


>  Otras consideraciones: testing automatizado de endpoints críticos, validación de inputs con Pydantic, y manejo de excepciones centralizado.

### 7️⃣ Mejores Prácticas y Recomendaciones Futuras

- Integrar OAuth2 social login (Google, Discord) para reducción de riesgos de contraseñas.

- Añadir webhooks y alertas en tiempo real para auditoría de eventos.

- Soporte para rotación periódica de SECRET_KEY y expiración más corta de tokens sensibles.

- Implementar escaneo automático de dependencias para vulnerabilidades conocidas.

- Revisar y auditar rate limits periódicamente según tráfico real.

