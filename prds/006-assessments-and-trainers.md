# PRD 006 — Evaluaciones, intentos y trainers

## Problema y objetivo

La primera versión de SoftStack permite marcar una lección como completada sin demostrar dominio. Esta vertical reemplaza esa acción por quizzes objetivos y crea el rol `trainer` para acompañar a estudiantes, revisar contenido y detectar competencias con mayor dificultad.

## Alcance

- Evaluación de selección única por lección y evaluación final por módulo.
- Entre 3 y 5 preguntas aprobadas por evaluación.
- Tres intentos por ciclo, con reinicio administrativo auditable.
- Calificación determinista en FastAPI.
- Preguntas y opciones aleatorias por intento.
- Preguntas sugeridas por un proveedor de IA intercambiable.
- DeepSeek como proveedor inicial, sin enviar datos personales.
- Trainer principal asignado directamente a cada estudiante.
- Analítica de resultados y falencias por competencia.

No se incluyen respuestas abiertas, evidencias prácticas, cohortes ni decisiones de empleabilidad.

## Reglas de negocio

1. Una lección se aprueba al alcanzar el porcentaje global configurado, inicialmente 80 %.
2. El estudiante dispone de tres envíos por ciclo. Un intento activo puede reanudarse y solo consume cupo al enviarse.
3. El quiz final de módulo se desbloquea cuando todas sus lecciones publicadas están aprobadas.
4. Un módulo se completa cuando se aprueba su evaluación final.
5. El backend nunca entrega la respuesta correcta durante un intento activo.
6. Cada intento conserva un snapshot de preguntas y opciones para que una edición posterior no altere el historial.
7. Reiniciar conserva los intentos anteriores, incrementa el ciclo y devuelve tres intentos disponibles.
8. El trainer ve resultados únicamente de estudiantes asignados; el admin ve todos.

## Preguntas y IA

Las preguntas tienen cuatro opciones, una respuesta correcta, explicación, dificultad y competencia. Solo las preguntas `approved` participan en intentos publicados.

`QuestionProvider` es el contrato de generación. `DeepSeekQuestionProvider` usa la API server-side configurada por variables de entorno y devuelve JSON validado con Pydantic. El contenido enviado se limita a título, descripción y texto educativo anonimizado. Las sugerencias quedan en estado `suggested`; admin o trainer deben revisarlas, editarlas y aprobarlas.

## Roles y permisos

- `user`: consume contenido, presenta evaluaciones y consulta sus resultados.
- `trainer`: crea y publica contenido y evaluaciones, genera/aprueba preguntas y consulta analítica de estudiantes asignados.
- `admin`: tiene todos los permisos, gestiona trainers, asignaciones, configuración global y reinicios.

El registro público no acepta el rol. Los trainers se crean o promueven mediante rutas protegidas de admin.

## Persistencia

Se agregan las colecciones `assessments`, `questions`, `attempts`, `assessment_states`, `assessment_resets`, `trainer_assignments`, `assessment_settings` y `module_progress`. Los intentos y reinicios son históricos; el estado actual se mantiene separado para controlar cupos y bloqueos.

## Riesgos y controles

- IA indisponible o inválida: devolver error controlado y no guardar preguntas parciales.
- Preguntas insuficientes: impedir publicar una evaluación.
- Exposición de respuestas: separar payload público de payload editorial y calificar exclusivamente en backend.
- Cambios de contenido: snapshot inmutable por intento.
- Privacidad: no transmitir identificadores personales al proveedor externo.
- Acceso trainer: validar la asignación en cada consulta, no solo en la interfaz.

## Validación

La cobertura incluye calificación, umbral, tres intentos, reinicios, bloqueo del quiz de módulo, aleatoriedad, snapshots, autorización por rol, alcance trainer, ocultamiento de respuestas y validación de respuestas DeepSeek mediante proveedor falso.

### Matriz estricta de pruebas

La suite usa dobles de repositorios, proveedor IA y servicios de correo. No abre conexiones reales a MongoDB, DeepSeek ni servicios externos.

| Superficie | Contratos cubiertos |
| --- | --- |
| Schemas y configuración | límites 1–100, 3–5 preguntas, tres intentos fijos, opciones únicas, estados, dificultad y rol trainer |
| Dominio | snapshots, reanudación, tres intentos, umbral inclusivo, respuestas incompletas o ajenas, aleatoriedad, progreso derivado y bloqueo por quizzes |
| Persistencia | evaluaciones, preguntas, intentos, estados, reinicios, asignaciones, configuración y fuente/modelo IA |
| API y permisos | payload público/editorial, IDs inválidos, admin/trainer/estudiante, analítica asignada, invitaciones, promoción y reinicios |
| IA | JSON válido o cercado, cantidad y opciones inválidas, timeout, HTTP, API key, proveedor desconocido y prompt anonimizado |

Comandos de validación local:

```bash
uv run pytest -q
uv run pytest -q --cov=app.services.assessment_service --cov=app.services.question_provider --cov=app.routes.assessment_routes --cov=app.repositories.assessment_repository --cov=app.schemas.assessment --cov=app.models.auth --cov=app.middlewares.role_middleware --cov-branch --cov-report=term-missing --cov-fail-under=95 tests/test_assessment_service.py tests/test_assessment_schemas.py tests/test_assessment_repository.py tests/test_assessment_routes.py tests/test_question_provider.py tests/test_progress_repository.py tests/test_auth_service.py
uv run python -m compileall -q app tests
uv run python -c "from app.main import app; paths = app.openapi()['paths']; assert '/assessments/{assessment_id}/attempts' in paths"
```

La cobertura focalizada debe permanecer por encima de 95 % en líneas y ramas. Los tests de rutas llaman directamente a las funciones FastAPI para mantenerlos deterministas y evitar dependencias con el transporte HTTP del entorno de desarrollo.
