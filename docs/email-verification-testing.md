# Verificación del flujo de correo de cuenta

## Contrato probado

El backend usa `TransactionalEmailClient` para llamar al proveedor externo:

- `POST {EMAIL_SERVICE_URL}/emails/send`
- Header `Content-Type: application/json`
- Body con `user_id`, `recipient`, `subject`, `body` y `html_body`
- `user_id` fijo en `1`, porque el proveedor exige un entero y los usuarios de
  SoftStack se identifican con `ObjectId` de MongoDB
- Respuesta aceptada: cualquier estado HTTP `2xx`; el proveedor desplegado
  responde `201 Created`.

El contrato corresponde al PRD 022 del proveedor. La llamada no envía API key
ni otro header de autenticación.

## Qué cubren las pruebas

- Construcción exacta de URL, headers, timeout y payload.
- Envío sin una API key porque `/emails/send` es público.
- Traducción de errores HTTP y de red a `EmailServiceError`.
- Registro con `verification_required=true` y envío del mensaje.
- Verificación válida, token inválido y reenvío con respuesta genérica.
- Persistencia del token de verificación aunque el proveedor no acepte el
  mensaje.

## Límite de lo que se puede afirmar

Una respuesta `202` demuestra que el proveedor aceptó la solicitud; no prueba
que el correo haya llegado a Inbox. La entrega posterior depende del proveedor,
SMTP, reputación del remitente, SPF/DKIM/DMARC y filtros antispam.

El registro actualmente no se revierte si el proveedor falla: el servicio
persiste el token, registra el error y permite usar `POST
/auth/resend-verification`. Esta decisión evita perder la cuenta, pero exige
revisar los logs del backend y la trazabilidad del proveedor cuando un usuario
no recibe el correo.

El `user_id=1` enviado al proveedor es únicamente un identificador de remitente
del sistema de correo. No representa ni sustituye al `_id` MongoDB del usuario
de SoftStack.

## Ejecución

Desde `softstack-backend`:

```bash
uv run pytest tests/test_email_service.py tests/test_account_email_service.py tests/test_auth_email_routes.py
```

Estas pruebas no envían correos reales ni requieren MongoDB. Una prueba de
entrega real debe ejecutarse aparte con un destinatario autorizado y sin
exponer secretos en logs.
