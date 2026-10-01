# PRD — Base LMS SoftStack

## Problema y objetivo

SoftStack necesita pasar de una API de autenticación a una experiencia educativa utilizable: el estudiante debe registrarse, recorrer contenido publicado, guardar progreso y editar su perfil; el administrador debe poder crear lecciones estructuradas sin almacenar HTML arbitrario.

## Alcance

- Sesión web con cookies HttpOnly, refresh rotativo y logout.
- Perfil con nombre, email y cambio de contraseña.
- Módulos y lecciones con estados `draft`, `published` y `archived`.
- Contenido de lección como JSON de Tiptap embebido.
- Progreso idempotente por usuario y lección.
- Seed inicial de contenido de empleabilidad.
- Rutas administrativas protegidas por rol.

Quedan fuera de esta vertical las evaluaciones, badges, subida de archivos, almacenamiento multimedia y verificación de email.

## Contratos y reglas

- `POST /auth/register` y `POST /auth/login` crean cookies de access/refresh y nunca exponen tokens en JSON.
- `POST /auth/refresh` solo acepta el refresh token almacenado en cookie y lo rota.
- `PATCH /auth/me` admite `full_name`, `email` y `new_password`; email o contraseña requieren `current_password`.
- El email se normaliza a minúsculas y conserva índice único.
- Solo módulos y lecciones publicados son visibles para estudiantes.
- Las rutas `/admin/*` requieren rol `admin`; el rol se determina mediante `ADMIN_EMAILS`, nunca desde el cliente.
- `GET /admin/modules` permite al administrador revisar módulos en cualquier estado; `POST /admin/modules` crea módulos con estado inicial configurable.
- `GET /admin/modules/{id}` y `GET /admin/modules/{id}/lessons` permiten revisar el módulo y sus lecciones administrativas, incluidos borradores, antes de continuar editando.
- `POST /lessons/{id}/complete` usa una clave única `(user_id, lesson_id)` para ser idempotente.

La interfaz administrativa expone `/admin/modules` para listar el catálogo, `/admin/modules/new` para crear módulos y `/admin/modules/{id}` para revisar sus lecciones. Crear un módulo redirige al catálogo; crear o editar una lección redirige al módulo correspondiente.

## Persistencia

- `users`: identidad, rol, estado, hash Argon2id y `full_name`.
- `refresh_tokens`: hash SHA-256, usuario, expiración y revocación.
- `modules`: metadata y orden de publicación.
- `lessons`: referencia a módulo, metadata y JSON Tiptap embebido.
- `progress`: relación única usuario/lección y fecha de finalización.

## Riesgos y límites conocidos

- La edición de email no incluye verificación de propiedad en esta fase.
- Las imágenes del editor se guardan como URLs; no existe upload seguro todavía.
- Para despliegues cross-site se debe usar HTTPS, `COOKIE_SECURE=true`, `COOKIE_SAMESITE=none` y CORS restringido al frontend.
