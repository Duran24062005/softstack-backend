# PRDs de SoftStack Backend

| Documento | Funcionalidad | Estado |
| --- | --- | --- |
| [`001-authentication.md`](./001-authentication.md) | Registro, login, sesiones, verificación de email y recuperación de contraseña | Implementado |
| [`002-learning-foundation.md`](./002-learning-foundation.md) | Módulos, lecciones, progreso y administración del contenido | Implementado |
| [`003-email-account-lifecycle.md`](./003-email-account-lifecycle.md) | Contrato de correo transaccional y ciclo de cuenta | Implementado |
| [`004-profile-photo-storage.md`](./004-profile-photo-storage.md) | Fotos de perfil privadas con Vercel Blob | Implementado |
| [`005-content-media-storage.md`](./005-content-media-storage.md) | Imágenes, videos y portadas de contenido con Vercel Blob público | Implementado |
| [`006-assessments-and-trainers.md`](./006-assessments-and-trainers.md) | Quizzes, intentos, banco de preguntas, DeepSeek y rol trainer | Implementado |
| [`007-account-approval-and-status.md`](./007-account-approval-and-status.md) | Aprobación administrativa y estado de cuentas | Implementado |
| [`008-student-academic-profile.md`](./008-student-academic-profile.md) | Perfil académico final de grupo y sede para estudiantes | Implementado |
| [`009-learning-analytics.md`](./009-learning-analytics.md) | Series de avance, mejora y actividad para estudiantes, trainers y admin | Implementado |
| [`010-ai-content-authoring-and-organization.md`](./010-ai-content-authoring-and-organization.md) | Asistencia IA para crear, organizar y revisar módulos y lecciones | Implementado |

Cada PRD documenta el contrato funcional, las reglas de seguridad, la persistencia y los límites conocidos de su vertical. SoftStack consume `POST /emails/send` del proveedor externo desplegado en `https://email-python-fast-api.vercel.app`, sin API key.
