# PRD — Flujo de autenticación y autorización SoftStack

## Objetivo

Implementar registro, login, consulta del usuario autenticado y el contrato inicial de recuperación de contraseña con JWT, refresh tokens persistidos como hashes y MongoDB.

## Roles

- `user`: rol asignado por defecto durante el registro.
- `admin`: solo se asigna si el email está incluido en `ADMIN_EMAILS`; no se acepta el rol desde el cliente.

## Endpoints

- `POST /auth/register` crea un usuario y devuelve su perfil público (`201`).
- `POST /auth/login` valida credenciales y devuelve access token, refresh token y usuario (`200`).
- `GET /auth/me` requiere `Authorization: Bearer <access_token>` (`200`).
- `POST /auth/reset-password` valida el email y devuelve `501` hasta integrar tokens de recuperación y email.

Las credenciales inválidas devuelven `401`, usuarios inactivos `403`, y emails duplicados `409`. Las respuestas no exponen contraseñas, hashes ni permiten enumerar cuentas.

## Persistencia

`users` almacena email normalizado, hash Argon2id, rol, estado y timestamps. `refresh_tokens` almacena únicamente el hash SHA-256 del token, usuario, expiración, creación y revocación. Se crean índices únicos, de estado y TTL sobre `expires_at`.

## Seguridad

Los access tokens son JWT de corta duración y contienen `sub`, `type=access`, `role`, `iat`, `exp` y `jti`. Los refresh tokens también son JWT, se devuelven en JSON como Bearer y se registran por hash para permitir revocación individual. `/auth/me` rechaza tokens de tipo refresh.

## Capas

- `config`: variables de entorno y ciclo de vida MongoDB.
- `models`/`schemas`: representación persistida y contratos HTTP.
- `repositories`: acceso a colecciones.
- `services`: hash de contraseñas, tokens y reglas de autenticación.
- `api`: rutas y dependencias de autorización.


## Convenciones de implementación

La seguridad transversal vive en `app/core/security.py` y las excepciones de aplicación en `app/core/exception.py`. Los middlewares de CORS, autenticación y roles se encuentran en `app/middlewares/`. Las rutas solo declaran contratos HTTP; los controllers coordinan errores y los services mantienen la lógica de negocio.
