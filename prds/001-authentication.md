# PRD — Flujo de autenticación y autorización SoftStack

## Objetivo

Implementar registro, login, consulta del usuario autenticado, verificación de email y recuperación de contraseña con JWT, refresh tokens persistidos como hashes y MongoDB.

## Roles

- `user`: rol asignado por defecto durante el registro.
- `admin`: solo se asigna si el email está incluido en `ADMIN_EMAILS`; no se acepta el rol desde el cliente.

## Endpoints

- `POST /auth/register` crea un usuario no verificado y devuelve su perfil público (`201`). También genera un enlace de verificación mediante el servicio de correo.
- `POST /auth/login` valida credenciales y devuelve el usuario (`200`); las cookies HttpOnly contienen la sesión.
- `GET /auth/verify-email?token=...` confirma la propiedad del email (`200`).
- `POST /auth/resend-verification` reenvía el enlace con respuesta genérica (`202`).
- `POST /auth/forgot-password` genera y envía un código de recuperación con respuesta genérica (`202`).
- `POST /auth/reset-password` valida el código de seis dígitos, cambia la contraseña y revoca las sesiones activas (`200`).
- `GET /auth/me` requiere `Authorization: Bearer <access_token>` (`200`).

Las credenciales inválidas devuelven `401`, usuarios inactivos `403`, emails duplicados `409` y cuentas no verificadas `403`. Las respuestas de verificación y recuperación no permiten enumerar cuentas.

## Persistencia

`users` almacena email normalizado, hash Argon2id, estado `email_verified`, rol y timestamps. `refresh_tokens` almacena únicamente el hash SHA-256 del token, usuario, expiración, creación y revocación. `email_action_tokens` almacena hashes de enlaces/códigos, propósito, expiración, intentos y consumo. Se crean índices únicos y TTL sobre los tokens temporales.

## Seguridad

Los access tokens son JWT de corta duración y contienen `sub`, `type=access`, `role`, `iat`, `exp` y `jti`. Los refresh tokens también son JWT, se entregan mediante cookies HttpOnly y se registran por hash para permitir revocación individual. `/auth/me` rechaza tokens de tipo refresh. Los enlaces y códigos de email solo se almacenan como hashes, tienen expiración y se consumen una vez.

## Capas

- `config`: variables de entorno y ciclo de vida MongoDB.
- `models`/`schemas`: representación persistida y contratos HTTP.
- `repositories`: acceso a colecciones.
- `services`: hash de contraseñas, tokens y reglas de autenticación.
- `api`: rutas y dependencias de autorización.

El ciclo de email y sus contratos con el servicio externo están detallados en [`003-email-account-lifecycle.md`](./003-email-account-lifecycle.md).


## Convenciones de implementación

La seguridad transversal vive en `app/core/security.py` y las excepciones de aplicación en `app/core/exception.py`. Los middlewares de CORS, autenticación y roles se encuentran en `app/middlewares/`. Las rutas solo declaran contratos HTTP; los controllers coordinan errores y los services mantienen la lógica de negocio.
