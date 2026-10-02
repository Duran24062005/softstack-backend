# PRDs de SoftStack Backend

| Documento | Funcionalidad | Estado |
| --- | --- | --- |
| [`001-authentication.md`](./001-authentication.md) | Registro, login, sesiones, verificación de email y recuperación de contraseña | Implementado |
| [`002-learning-foundation.md`](./002-learning-foundation.md) | Módulos, lecciones, progreso y administración del contenido | Implementado |
| [`003-email-account-lifecycle.md`](./003-email-account-lifecycle.md) | Contrato de correo transaccional y ciclo de cuenta | Implementado |

Cada PRD documenta el contrato funcional, las reglas de seguridad, la persistencia y los límites conocidos de su vertical. SoftStack consume el endpoint transaccional del proveedor externo desplegado en `https://email-python-fast-api.vercel.app`.
