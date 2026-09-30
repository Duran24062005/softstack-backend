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
