# SoftStack Backend

Backend base de SoftStack construido con FastAPI y MongoDB usando el driver oficial `pymongo`.

## Requisitos

- Python 3.14+
- [`uv`](https://docs.astral.sh/uv/)
- Docker y Docker Compose para el entorno local completo

## Configuración local

```bash
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Puedes usar MongoDB local o configurar MongoDB Atlas en `MONGODB_URI`.

### Variables de autenticación

- `ADMIN_EMAILS` es una lista separada por comas. Cada usuario cuyo email normalizado aparezca allí recibe el rol `admin` al registrarse. Cambiar la variable no cambia el rol de usuarios ya existentes.
- `COOKIE_DOMAIN` debe permanecer vacío cuando el frontend usa el proxy BFF de Next.js, como en este proyecto. No debe apuntar al dominio del backend para intentar compartir cookies con el frontend; el navegador recibe las cookies desde el dominio del frontend.
- En local usa `COOKIE_SECURE=false` y `COOKIE_SAMESITE=lax`. En producción con HTTPS, `COOKIE_SECURE=true` es la opción recomendada.

Ejemplo mínimo local:

```env
ADMIN_EMAILS=tu-correo@example.com
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
COOKIE_DOMAIN=
```

El email de `ADMIN_EMAILS` debe coincidir con el que usarás en el registro. Si el usuario ya existe como `user`, la variable no lo convierte automáticamente en administrador.

## Docker Compose

```bash
docker compose up --build
```

MongoDB queda disponible en `localhost:27017` y la API en `http://localhost:8000`. Los datos se conservan en el volumen `mongodb_data`.

## MongoDB Atlas

```env
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>/<database>?retryWrites=true&w=majority
MONGODB_DATABASE=softstack
```

No guardes credenciales reales en el repositorio.

## Endpoints

- `GET /` — confirma que la API está funcionando.
- `GET /health` — comprueba MongoDB; responde `200` si está disponible y `503` si no lo está.
- `POST /auth/register` y `POST /auth/login` — crean sesión mediante cookies HttpOnly.
- `POST /auth/refresh` y `POST /auth/logout` — rotan o revocan la sesión.
- `GET /auth/me` y `PATCH /auth/me` — consultan y editan el perfil.
- `GET /modules`, `GET /modules/{id}/lessons` y `GET /lessons/{id}` — contenido publicado.
- `GET /admin/modules` — lista módulos en cualquier estado para administradores.
- `GET /admin/modules/{id}` y `GET /admin/modules/{id}/lessons` — consulta un módulo y sus lecciones, incluidos borradores.
- `POST /admin/modules` y `PATCH /admin/modules/{id}` — crea y actualiza módulos.
- `POST /admin/modules/{id}/lessons`, `GET /admin/lessons/{id}` y `PATCH /admin/lessons/{id}` — gestión de lecciones para administradores.
- `GET /me/progress` y `POST /lessons/{id}/complete` — progreso del estudiante.

Las cookies usan `COOKIE_SECURE=true` en producción. Si frontend y backend viven en dominios distintos, configura `COOKIE_SAMESITE=none`, HTTPS y `CORS_ORIGINS` con el origen exacto del frontend.

## Contenido inicial

Con MongoDB disponible, carga los módulos y lecciones iniciales con:

```bash
uv run python scripts/seed_content.py
```

El seed es idempotente: puede repetirse sin duplicar módulos ni lecciones.

## Despliegue

El proyecto incluye `vercel.json` para Vercel. Define `MONGODB_URI` y `MONGODB_DATABASE` como variables de entorno en la plataforma.


## Estructura de autenticación

La autenticación se organiza por responsabilidades: `routes` define endpoints, `controllers` coordina entradas y errores, `services` contiene la lógica de negocio, `repositories` accede a MongoDB y `core` centraliza seguridad y excepciones. Los middlewares de CORS, autenticación Bearer y roles se registran desde `app/main.py`.

Para proteger una ruta por rol, usa `Depends(require_roles("admin"))` desde `app.middlewares.role_middleware`.
