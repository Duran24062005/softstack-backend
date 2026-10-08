# PRD 009 — Analítica visual de aprendizaje

## Problema y objetivo

La plataforma ya conserva progreso de lecciones, módulos e intentos de evaluación, pero los usuarios deben leer esos datos como listas y cifras aisladas. Esta vertical convierte los eventos existentes en tendencias claras para que el estudiante entienda su avance, el trainer oriente el refuerzo y el admin observe el comportamiento global.

## Alcance

- Series de avance acumulado, calificaciones y actividad por fecha.
- Períodos configurables de 7, 30, 90 días o todo el historial; el valor predeterminado es 30 días.
- `GET /me/analytics` para el estudiante autenticado.
- Ampliación de `/educator/analytics/overview`, `/educator/analytics/students` y `/educator/analytics/students/{id}`.
- Actividad basada únicamente en lecciones/módulos completados e intentos enviados.
- Agregación server-side sobre las colecciones existentes.

No se incluyen sesiones de navegación, tracking de visitas, exportación, cohortes nuevas ni cambios en autenticación.

## Contrato y reglas

Todos los endpoints analíticos aceptan `period=7d|30d|90d|all`. Las fechas de series se serializan como `YYYY-MM-DD` en UTC.

Cada respuesta incluye un snapshot actual, estudiantes activos dentro del período cuando aplica, promedio de calificación, series `progress_series`, `score_series` y `activity_series`, además de competencias con fallos.

El snapshot de progreso representa el estado actual y no queda limitado por el período. Las series sí respetan el filtro temporal; el avance acumulado considera completados anteriores al inicio del período para no reiniciar artificialmente la curva.

- `user` solo puede consultar sus propios eventos.
- `trainer` solo puede consultar estudiantes con asignación vigente.
- `admin` puede consultar todos los estudiantes.
- Solo intentos con `status=submitted` participan en promedios, actividad y competencias.
- Completados repetidos no incrementan el porcentaje de avance.

## Persistencia e implementación

No se crean colecciones nuevas ni se modifica el esquema de autenticación. `ProgressRepository` expone consultas agrupadas para varios usuarios y `analytics_service.py` centraliza el filtro temporal, deduplicación y agregación. Se reutilizan los índices existentes por usuario y fecha.

## Riesgos y controles

- Períodos sin eventos: devolver series vacías y permitir que la interfaz muestre un estado orientativo.
- Registros antiguos sin fecha válida: no entran en series temporales, pero no rompen el snapshot.
- Alcance trainer: validar la asignación en backend en cada detalle, independientemente de la navegación frontend.
- Crecimiento del volumen: mantener consultas acotadas por usuarios y fechas; revisar índices antes de ampliar el período a nuevas fuentes.

## Validación

La suite cubre agregación por día, filtros de período, estados de intento, deduplicación de progreso, estudiantes activos, competencias fallidas, respuesta vacía y privacidad del endpoint personal. La validación local usa `uv run pytest -q`, compilación de módulos y comprobación de rutas OpenAPI.
