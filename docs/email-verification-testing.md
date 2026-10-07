# Verificación del flujo de correo de cuenta

## Contrato probado

El backend usa `TransactionalEmailClient` para llamar al proveedor externo:

- `POST {EMAIL_SERVICE_URL}/emails/transactional`
- Header `Content-Type: application/json`
- Body con `recipient`, `subject`, `body` y `html_body`
- Respuesta aceptada: cualquier estado HTTP `2xx`; el proveedor desplegado
  responde `202 Accepted`.

El contrato se comprobó contra el OpenAPI público del proveedor el 7 de
octubre de 2026. El checkout local de `Email_Python_FastAPI` contiene rutas
históricas adicionales y no debe usarse como única fuente para validar el
despliegue activo.

## Qué cubren las pruebas

- Construcción exacta de URL, headers, timeout y payload.
- Envío sin una API key local porque el endpoint transaccional es público.
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

El endpoint genérico `/emails/send` documentado por el proveedor requiere un
`user_id` entero y se reserva para su flujo de bandeja. No se utiliza para la
verificación de SoftStack porque los usuarios de SoftStack usan identificadores
MongoDB y el envío transaccional no debe depender de esa bandeja.

## Ejecución

Desde `softstack-backend`:

```bash
uv run pytest tests/test_email_service.py tests/test_account_email_service.py tests/test_auth_email_routes.py
```

Estas pruebas no envían correos reales ni requieren MongoDB. Una prueba de
entrega real debe ejecutarse aparte con un destinatario autorizado y sin
exponer secretos en logs.
