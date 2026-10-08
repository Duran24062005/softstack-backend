# PRD — Confirmación de cuenta y recuperación de contraseña por email

## Problema y objetivo

SoftStack actualmente registra usuarios y permite iniciar sesión sin comprobar la propiedad del email. Además, `POST /auth/reset-password` todavía responde `501`. Esta vertical agrega confirmación de cuenta y recuperación de contraseña mediante un código de un solo uso, usando un proveedor transaccional de correo desplegado externamente.

El objetivo es que:

- cada registro genere un enlace y un código de confirmación;
- las cuentas no confirmadas no puedan iniciar sesión;
- un usuario pueda solicitar un código temporal para recuperar su contraseña;
- el código sea de un solo uso, tenga expiración y nunca se almacene en texto plano;
- los fallos del proveedor de correo no expongan secretos ni permitan enumerar usuarios.

## Alcance

### Incluido

- Estado `email_verified` en `users`, con valor inicial `false` para usuarios nuevos.
- Token aleatorio de confirmación con expiración configurable.
- Código numérico de seis dígitos para recuperar la confirmación cuando el
  enlace original no llegó.
- `GET /auth/verify-email?token=...` para confirmar la cuenta.
- `POST /auth/verify-email-code` para confirmar la cuenta con email y código.
- `POST /auth/resend-verification` para reenviar confirmación con respuesta genérica.
- `POST /auth/forgot-password` para solicitar un código de recuperación.
- `POST /auth/reset-password` para validar el código y cambiar la contraseña.
- Colección `email_action_tokens` para hashes de tokens/códigos, expiración, consumo e intentos.
- Revocación de refresh tokens después de cambiar la contraseña.
- Cliente HTTP hacia `POST /emails/send` del proveedor externo.
- Pantallas frontend para confirmar email, solicitar recuperación y establecer nueva contraseña.
- Plantillas HTML/texto para confirmación y recuperación.
- Variables de entorno, pruebas y documentación de contratos.

### Fuera de alcance

- Cambiar el proveedor SMTP o administrar buzones desde SoftStack.
- Usar la base de datos del proveedor de correo para autenticar usuarios de SoftStack.
- Recuperación mediante preguntas de seguridad.
- Verificación automática de dominios, MX o listas de correo desechable.
- Rate limiting distribuido por IP; se limita el número de intentos por token y se deja documentada la necesidad de rate limiting de borde.

## Actores

- Usuario no confirmado: puede registrarse y solicitar reenvío, pero no iniciar sesión. Si proporciona la contraseña correcta, el login emite otro código y responde `EMAIL_NOT_VERIFIED`; el frontend muestra el campo para introducirlo.
- Usuario confirmado: puede iniciar recuperación y cambiar su contraseña con un código válido.
- Servicio SoftStack: crea, consume y revoca tokens; mantiene la identidad y las reglas de autenticación.
- Proveedor externo: recibe un mensaje transaccional autenticado y lo entrega mediante su infraestructura de correo.

## Flujo de confirmación

1. `POST /auth/register` valida email, nombre y contraseña.
2. SoftStack crea el usuario con `email_verified=false`.
3. Genera un token aleatorio y un código de seis dígitos, almacena únicamente sus hashes y calcula sus expiraciones.
4. Envía el enlace y el código mediante el proveedor de correo.
5. La respuesta indica `verification_required=true` y no crea cookies de sesión.
6. El usuario abre `/verify-email?token=...` en el frontend.
7. El frontend llama a `GET /auth/verify-email?token=...` por el BFF.
8. SoftStack valida hash, propósito, expiración y consumo; después marca `email_verified=true`.

También puede enviar `{email, code}` a `POST /auth/verify-email-code`. El código
se invalida después de cinco intentos incorrectos (configurable) y al confirmar
se invalidan los enlaces/códigos alternativos activos.

El servicio normaliza espacios exteriores y mayúsculas del email, y espacios
exteriores del código antes de consultar o comparar. Esto evita que una copia
del código desde el correo falle por formato sin relajar la validación de seis
dígitos del contrato HTTP.

Si falla el proveedor durante el registro, el usuario permanece creado pero no confirmado. El endpoint de reenvío permite recuperar el flujo sin revelar si el email existe.

## Flujo de recuperación

1. El usuario envía su email a `POST /auth/forgot-password`.
2. SoftStack responde siempre con el mismo mensaje y estado `202`, exista o no la cuenta.
3. Si la cuenta existe y está activa, se invalida el código anterior, se genera un código numérico de seis dígitos y se almacena solo su hash.
4. El proveedor envía el código con una expiración corta.
5. El usuario envía email, código y nueva contraseña a `POST /auth/reset-password`.
6. SoftStack valida propósito, hash, expiración, consumo e intentos máximos.
7. Si es válido, actualiza el hash Argon2id, marca el token como consumido y revoca refresh tokens activos del usuario.

## Contratos HTTP

### Registro

`POST /auth/register` mantiene el usuario público, pero no crea sesión hasta que el email esté confirmado.

Respuesta `201`:

```json
{
  "expires_in": 0,
  "user": {
    "id": "...",
    "full_name": "Alex Rivera",
    "email": "alex@example.com",
    "role": "user",
    "is_active": true,
    "email_verified": false,
    "created_at": "..."
  },
  "verification_required": true,
  "message": "Revisa tu correo para confirmar tu cuenta."
}
```

### Confirmación

`GET /auth/verify-email?token=<token>`

- `200`: `{ "message": "Email verificado correctamente." }`
- `400`: token inválido, expirado, usado o de propósito incorrecto.
- `404`: no se expone para evitar distinguir tokens asociados a usuarios inexistentes; un token válido para un usuario eliminado se trata como inválido.

### Reenvío

`POST /auth/resend-verification`

```json
{ "email": "alex@example.com" }
```

Respuesta `202` siempre:

```json
{ "message": "Si la cuenta puede recibir un correo, enviaremos un nuevo enlace y código." }
```

### Solicitud de recuperación

`POST /auth/forgot-password`

```json
{ "email": "alex@example.com" }
```

Respuesta `202` siempre, sin confirmar si la cuenta existe.

### Confirmación de recuperación

`POST /auth/reset-password`

```json
{
  "email": "alex@example.com",
  "code": "483921",
  "new_password": "nueva-clave-segura"
}
```

- `200`: contraseña actualizada.
- `400`: código inválido, expirado, consumido o sin intentos disponibles.
- `422`: email o contraseña inválidos.

## Persistencia

`users` agrega:

- `email_verified: bool`, default `false`.

`email_action_tokens` almacena:

- `user_id`;
- `purpose`: `email_verification`, `email_verification_code` o `password_reset`;
- `token_hash` SHA-256;
- `expires_at` con índice TTL;
- `created_at`;
- `consumed_at` nullable;
- `attempts`.

No se persisten tokens de confirmación ni códigos en texto plano.

## Integración de correo

SoftStack llama a `POST /emails/send` del proveedor externo (`https://email-python-fast-api.vercel.app`) con:

- `user_id: 1` fijo, requerido por el contrato del proveedor;
- `recipient`;
- `subject`;
- `body`;
- `html_body` opcional;
- sin API key ni otro header de autenticación.

El `user_id` del proveedor identifica un remitente dentro de su propia base y no es el `_id` MongoDB de SoftStack. En desarrollo puede usar `MockEmailSender`; en producción usa el SMTP configurado en el repositorio de correo.

## Reglas de seguridad

- El login rechaza usuarios con `email_verified=false`.
- Las respuestas de forgot/resend son indistinguibles para emails existentes y no existentes.
- Los códigos de recuperación y verificación son de seis dígitos, expiran rápido y permiten un número limitado de intentos.
- Se invalida el token anterior del mismo propósito al emitir uno nuevo.
- Se revocan sesiones refresh después de un cambio de contraseña.
- La clave del proveedor de correo vive solo en variables de entorno; nunca se envía al frontend.
- Los links se construyen con `FRONTEND_URL` configurado, no con el host recibido en la petición.

## Riesgos y decisiones

- Si el proveedor está caído, el registro no se revierte; el reenvío permite reintentar y se registra el fallo sin incluir tokens en logs.
- La protección contra abuso requiere rate limiting de plataforma para complementar los intentos por token.
- Los usuarios existentes se consideran confirmados durante la migración para no bloquear cuentas ya creadas; los nuevos registros empiezan como no confirmados.
- Cambiar `JWT_SECRET_KEY` invalida tokens de sesión, pero no afecta hashes de acciones almacenados.
