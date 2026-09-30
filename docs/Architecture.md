# Arquitectura del backend

El backend usa FastAPI con una arquitectura por capas y MongoDB como persistencia.

```text
HTTP -> API routes -> services -> repositories -> MongoDB
              |          |
           schemas    security
```

El `MongoClient` se crea una vez durante el lifespan de FastAPI, se expone en `app.state` y se cierra al apagar la aplicación. Los repositorios reciben la base de datos mediante dependencias para facilitar pruebas aisladas.

La autenticación se encuentra bajo `/auth`: registro, login, `/me` y el contrato inicial de reset de contraseña. Los access tokens JWT se validan con Bearer; los refresh tokens se almacenan en `refresh_tokens` únicamente como hashes.

## Core y middlewares

- `app/core/security.py` contiene hashing Argon2id y emisión/validación de JWT.
- `app/core/exception.py` define excepciones de aplicación y registra sus handlers HTTP globales.
- `app/middlewares/cors.py` configura CORS desde `CORS_ORIGINS`.
- `app/middlewares/auth_middleware.py` extrae el Bearer token y deja el payload validado en `request.state` sin bloquear rutas públicas.
- `app/middlewares/role_middleware.py` expone `require_roles(...)` para proteger rutas por rol.

Los controllers traducen las operaciones de entrada y los services lanzan excepciones de dominio; el handler global convierte esas excepciones en respuestas HTTP uniformes.
