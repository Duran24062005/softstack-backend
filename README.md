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

Ejecuta las pruebas unitarias con:

```bash
uv run pytest
```

La funcionalidad de evaluaciones y trainers tiene una suite estricta sin MongoDB ni servicios externos reales. Para validar su cobertura de líneas y ramas:

```bash
uv run pytest -q --cov=app.services.assessment_service --cov=app.services.question_provider --cov=app.routes.assessment_routes --cov=app.repositories.assessment_repository --cov=app.schemas.assessment --cov=app.models.auth --cov=app.middlewares.role_middleware --cov-branch --cov-report=term-missing --cov-fail-under=95 tests/test_assessment_service.py tests/test_assessment_schemas.py tests/test_assessment_repository.py tests/test_assessment_routes.py tests/test_question_provider.py tests/test_progress_repository.py tests/test_auth_service.py
```

La validación de contratos también puede comprobarse sin levantar MongoDB:

```bash
uv run python -m compileall -q app tests
uv run python -c "from app.main import app; paths = app.openapi()['paths']; assert '/assessments/{assessment_id}/attempts' in paths"
```

Las pruebas de servicios de contenido cubren medios anidados, límites, SSRF, portadas, compensación y limpieza de blobs.

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
- `GET /auth/verify-email`, `POST /auth/resend-verification` — verifican o reenvían la confirmación de cuenta.
- `POST /auth/forgot-password` y `POST /auth/reset-password` — solicitan y aplican códigos de recuperación.
- `POST /auth/refresh` y `POST /auth/logout` — rotan o revocan la sesión.
- `GET /auth/me` y `PATCH /auth/me` — consultan y editan el perfil.
- `POST /auth/me/profile-photo`, `GET /auth/me/profile-photo` y `DELETE /auth/me/profile-photo` — gestionan la foto privada del usuario autenticado.
- `GET /modules`, `GET /modules/{id}/lessons` y `GET /lessons/{id}` — contenido publicado.
- `GET /admin/modules` — lista módulos en cualquier estado para administradores.
- `GET /admin/modules/{id}` y `GET /admin/modules/{id}/lessons` — consulta un módulo y sus lecciones, incluidos borradores.
- `POST /admin/modules` y `PATCH /admin/modules/{id}` — crea y actualiza módulos.
- `POST /admin/modules/{id}/lessons`, `GET /admin/lessons/{id}` y `PATCH /admin/lessons/{id}` — gestión de lecciones para administradores.
- `POST /admin/content-media/import` y `DELETE /admin/content-media` — importación segura y limpieza de medios para administradores.
- `GET /internal/content-media/cleanup` — limpieza protegida de blobs de contenido huérfanos; Vercel Cron lo ejecuta diariamente.
- `GET /me/progress` — progreso derivado de evaluaciones; la finalización manual dejó de ser válida.
- `GET /assessments/lessons/{id}`, `GET /assessments/modules/{id}`, `POST /assessments/{id}/attempts` y `POST /attempts/{id}/submit` — quizzes e intentos del estudiante.
- `/educator/*` — edición de evaluaciones, preguntas, sugerencias y analítica para admin/trainer.
- `/admin/assessment-settings`, `/admin/students/{id}/trainer` y `/admin/assessments/{id}/students/{student_id}/reset` — configuración, asignaciones y reinicios protegidos para admin.

Las cookies usan `COOKIE_SECURE=true` en producción. Si frontend y backend viven en dominios distintos, configura `COOKIE_SAMESITE=none`, HTTPS y `CORS_ORIGINS` con el origen exacto del frontend. El backend envía correos de cuenta mediante el endpoint público `/emails/transactional` del servicio configurado en `EMAIL_SERVICE_URL`. `FRONTEND_URL` se usa para generar los enlaces de verificación.

Las fotos de perfil usan un Blob Store privado de Vercel. Configura `BLOB_STORE_ID` y `BLOB_READ_WRITE_TOKEN` en el backend; nunca expongas el token al frontend. Se aceptan imágenes JPG, PNG y WebP de máximo 3 MB.

Las imágenes, videos y portadas de módulos usan un Blob Store público separado. Configura `CONTENT_BLOB_STORE_ID`, `CONTENT_BLOB_READ_WRITE_TOKEN` y `CONTENT_BLOB_PUBLIC_HOST`. El contenido público puede ser leído por cualquiera que conozca su URL. Los límites predeterminados son 10 MB para imágenes y 100 MB para videos.

Para habilitarlo en Vercel, crea un Blob Store dedicado con acceso público, copia su store ID y token read-write en las variables anteriores y configura el mismo token en el entorno server-side del frontend. El endpoint de eliminación rechaza pathnames todavía referenciados; los archivos abandonados se recuperan mediante el cron diario. Para convertir contenido externo existente antes de aplicar la validación estricta, ejecuta primero `uv run python -m scripts.migrate_content_media` en modo dry-run y luego añade `--apply`.

## Contenido inicial

Con MongoDB disponible, carga los módulos y lecciones iniciales con:

```bash
uv run python -m scripts.seed_content
```

El seed es idempotente: puede repetirse sin duplicar módulos ni lecciones.

El catálogo inicial contiene cinco módulos y trece lecciones sobre presencia virtual, CV y filtros ATS, marca personal y mercado oculto, comunicación en entrevistas, y negociación y seguimiento. La estructura detallada está documentada en [`prds/002-learning-foundation.md`](./prds/002-learning-foundation.md).

## Despliegue

El proyecto incluye `vercel.json` para Vercel. Define `MONGODB_URI` y `MONGODB_DATABASE` como variables de entorno en la plataforma.


## Estructura de autenticación

La autenticación se organiza por responsabilidades: `routes` define endpoints, `controllers` coordina entradas y errores, `services` contiene la lógica de negocio, `repositories` accede a MongoDB y `core` centraliza seguridad y excepciones. Los middlewares de CORS, autenticación Bearer y roles se registran desde `app/main.py`.

Para proteger una ruta por rol, usa `Depends(require_roles("admin"))` desde `app.middlewares.role_middleware`.
