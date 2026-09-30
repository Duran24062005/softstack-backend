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

## Despliegue

El proyecto incluye `vercel.json` para Vercel. Define `MONGODB_URI` y `MONGODB_DATABASE` como variables de entorno en la plataforma.


## Estructura de autenticación

La autenticación se organiza por responsabilidades: `routes` define endpoints, `controllers` coordina entradas y errores, `services` contiene la lógica de negocio, `repositories` accede a MongoDB y `core` centraliza seguridad y excepciones. Los middlewares de CORS, autenticación Bearer y roles se registran desde `app/main.py`.

Para proteger una ruta por rol, usa `Depends(require_roles("admin"))` desde `app.middlewares.role_middleware`.
