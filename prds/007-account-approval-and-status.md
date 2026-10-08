# PRD 007 — Aprobación y estado de cuentas

## Objetivo

Evitar que un registro nuevo acceda al LMS antes de que un administrador lo
revise y permitir la gestión segura del ciclo de vida de las cuentas desde el
panel administrativo.

## Estados y reglas

Las cuentas tienen un `account_status` persistido:

- `pending`: registro creado y pendiente de decisión administrativa.
- `active`: cuenta aprobada y habilitada para acceder.
- `rejected`: solicitud rechazada, conservada para trazabilidad y reabrible.
- `inactive`: cuenta pausada o bloqueada; no puede autenticarse.

`is_active` se conserva por compatibilidad y se mantiene en `true` únicamente
para `active`. Los registros normales empiezan como `pending` e inactivos.
Los correos incluidos en `ADMIN_EMAILS` mantienen la excepción de bootstrap y
crean administradores activos, aunque siguen necesitando verificar su email.

Verificar el email solo cambia `email_verified`; nunca aprueba la cuenta.
Después de verificarlo, el usuario debe esperar que un administrador lo pase a
`active`.

## Transiciones administrativas

```text
pending  -> active | rejected
rejected -> pending
active   -> inactive
inactive -> active
```

El actor debe tener rol `admin`. No puede cambiar su propio estado ni el de
otra cuenta con rol `admin`. Cada cambio actualiza `status_changed_at` y
`status_changed_by`.

## Contrato HTTP

### Listar cuentas

`GET /admin/users?role=user&account_status=pending`

Devuelve todas las cuentas administrativas con nombre, email, rol, estado,
verificación de email, fecha de registro y los datos del último cambio de
estado. Los filtros son opcionales.

### Cambiar estado

`PATCH /admin/users/{user_id}/status`

```json
{ "account_status": "active" }
```

El backend rechaza transiciones no permitidas con `409` y protege el endpoint
con autorización administrativa. Los estados `pending`, `rejected` e
`inactive` bloquean login, refresh y rutas protegidas.

## Migración y compatibilidad

Los usuarios existentes sin `account_status` se interpretan temporalmente a
partir de `is_active` y pueden normalizarse con:

```bash
uv run python -m scripts.migrate_account_status
uv run python -m scripts.migrate_account_status --apply
```

La migración solo rellena documentos que todavía no tienen estado y puede
repetirse sin duplicar ni sobrescribir decisiones posteriores.

## Fuera de alcance

- Correos nuevos para aprobación, rechazo, bloqueo o reactivación.
- Edición libre del rol `admin`.
- Eliminación de cuentas rechazadas.
- Historial separado de eventos administrativos; la primera versión conserva
  el último actor y momento del cambio en `users`.
