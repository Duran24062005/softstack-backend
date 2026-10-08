# PRD — Flujo de autenticación y autorización SoftStack

## Objetivo

Implementar registro, login, consulta del usuario autenticado, verificación de email y recuperación de contraseña con JWT, refresh tokens persistidos como hashes y MongoDB.

## Roles

- `user`: rol asignado por defecto durante el registro.
- `admin`: solo se asigna si el email está incluido en `ADMIN_EMAILS`; no se acepta el rol desde el cliente.
- El registro público de estudiantes también recibe `academic_profile` con el año de inicio, un grupo y una sede finales. Los trainers se crean mediante rutas administrativas y no necesitan ese bloque.

## Endpoints

- `POST /auth/register` crea un usuario no verificado y devuelve su perfil público (`201`). También genera un enlace de verificación mediante el servicio de correo.
- `POST /auth/login` valida credenciales y devuelve el usuario (`200`); las cookies HttpOnly contienen la sesión. Si la contraseña es correcta pero el email no está verificado, genera un nuevo enlace y código, responde `403` con `code=EMAIL_NOT_VERIFIED` y no crea cookies.
- `GET /auth/verify-email?token=...` confirma la propiedad del email (`200`).
- `POST /auth/verify-email-code` confirma la propiedad del email con `{email, code}` (`200`).
- `POST /auth/resend-verification` reenvía el enlace y el código con respuesta genérica (`202`).
- `POST /auth/forgot-password` genera y envía un código de recuperación con respuesta genérica (`202`).
- `POST /auth/reset-password` valida el código de seis dígitos, cambia la contraseña y revoca las sesiones activas (`200`).
- `GET /auth/me` requiere `Authorization: Bearer <access_token>` (`200`).
- `GET /auth/me/academic-profile` devuelve el perfil académico del estudiante o `null` si una cuenta existente aún no lo tiene (`200`).
- `PUT /auth/me/academic-profile` reemplaza el perfil académico del estudiante autenticado (`200`).

Las credenciales inválidas devuelven `401`, usuarios inactivos `403`, emails duplicados `409` y cuentas no verificadas `403` con `EMAIL_NOT_VERIFIED`. Las respuestas de verificación y recuperación no permiten enumerar cuentas.

## Persistencia

`users` almacena email normalizado, hash Argon2id, estado `email_verified`, rol y timestamps. `refresh_tokens` almacena únicamente el hash SHA-256 del token, usuario, expiración, creación y revocación. `email_action_tokens` almacena hashes de enlaces/códigos, propósito (`email_verification`, `email_verification_code` o `password_reset`), expiración, intentos y consumo. Se crean índices únicos y TTL sobre los tokens temporales.

## Seguridad

Los access tokens son JWT de corta duración y contienen `sub`, `type=access`, `role`, `iat`, `exp` y `jti`. Los refresh tokens también son JWT, se entregan mediante cookies HttpOnly y se registran por hash para permitir revocación individual. `/auth/me` rechaza tokens de tipo refresh. Los enlaces y códigos de email solo se almacenan como hashes, tienen expiración, límite de intentos para códigos y se consumen una vez.

## Capas

- `config`: variables de entorno y ciclo de vida MongoDB.
- `models`/`schemas`: representación persistida y contratos HTTP.
- `repositories`: acceso a colecciones.
- `services`: hash de contraseñas, tokens y reglas de autenticación.
- `api`: rutas y dependencias de autorización.

El ciclo de email y sus contratos con el servicio externo están detallados en [`003-email-account-lifecycle.md`](./003-email-account-lifecycle.md).

La estructura del perfil académico y sus permisos están detallados en
[`008-student-academic-profile.md`](./008-student-academic-profile.md).


## Convenciones de implementación

La seguridad transversal vive en `app/core/security.py` y las excepciones de aplicación en `app/core/exception.py`. Los middlewares de CORS, autenticación y roles se encuentran en `app/middlewares/`. Las rutas solo declaran contratos HTTP; los controllers coordinan errores y los services mantienen la lógica de negocio.
