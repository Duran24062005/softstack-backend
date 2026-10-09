# PRD 010: autoría y organización de contenido asistida por IA

## Problema y objetivo

La creación de módulos y lecciones exige ordenar objetivos, conceptos,
formatos, actividades y tiempos antes de escribir el contenido. El objetivo es
ofrecer a `admin` y `trainer` un asistente server-side que proponga esa
estructura y borradores editables sin quitar el control editorial ni cambiar
automáticamente lo que ve un estudiante.

## Alcance

La feature genera propuestas para módulos y lecciones con:

- objetivos de aprendizaje;
- mapa conceptual;
- progresión de simple a complejo y justificación;
- formatos recomendados (`text`, `video`, `activity`, `interactive`,
  `gamification`);
- guía de sesión con minutos y actividades;
- blueprint de secuencia de lecciones;
- bloques Tiptap seguros para un borrador de lección.

El blueprint no crea documentos de lección. La propuesta se muestra por
secciones y puede aplicarse parcialmente. No se conserva una generación que el
usuario descarte.

## Actores y permisos

`admin` y `trainer` pueden generar, revisar y aplicar propuestas dentro de sus
permisos editoriales actuales. La administración de usuarios, trainers,
asignaciones, configuración y reinicios permanece restringida a `admin`.
Los estudiantes no pueden invocar estas rutas; solo reciben objetivos y
resúmenes estructurales ya aprobados en el contenido publicado.

## Diseño técnico

`ContentSuggestionProvider` es un puerto independiente de
`QuestionProvider`. La implementación DeepSeek reutiliza
`DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL` y el timeout existente, y permite
`AI_CONTENT_PROVIDER` y `DEEPSEEK_CONTENT_MODEL`. La fábrica rechaza
proveedores desconocidos o no configurados.

Las respuestas del proveedor se validan con Pydantic. El prompt se construye
con contexto educativo mínimo y elimina emails y teléfonos conocidos; nunca se
envían tokens, cookies ni identificadores personales. Se aceptan solo los
tipos de nodos Tiptap definidos por `GeneratedContentBlock`; no se aceptan
HTML, URLs, imágenes, videos ni embeds externos.

## Contrato HTTP

- `POST /educator/content-suggestions/modules`
- `POST /educator/content-suggestions/lessons`
- `POST /educator/content-suggestions/modules/{module_id}/apply`
- `POST /educator/content-suggestions/lessons/{lesson_id}/apply`
- `GET /educator/content-revisions/{target_type}/{target_id}`
- `POST /educator/content-revisions/{revision_id}/publish`
- `DELETE /educator/content-revisions/{revision_id}`

La generación devuelve `base_updated_at`, proveedor/modelo y una propuesta
estructurada. La aplicación exige ese timestamp y una lista de secciones. El
backend verifica que las lecciones pertenezcan al módulo y que las órdenes sean
válidas.

## Persistencia y publicación

Los módulos y lecciones conservan `instructional_plan` junto a sus datos
actuales. Una aplicación sobre borrador actualiza únicamente los campos
seleccionados. Una aplicación sobre contenido `published` crea o actualiza una
revisión pendiente en `content_revisions` con el snapshot de cambios, usuario y
versión base. La publicación vuelve a comprobar `updated_at`, aplica los
cambios y marca la revisión como `published`; el descarte elimina la revisión
pendiente y solo devuelve una confirmación efímera. Si hay una edición concurrente, la API devuelve `409` y el usuario
debe regenerar.

La edición manual normal no entra en este flujo de versiones. La publicación de
un módulo aplica también las órdenes de lecciones incluidas en su revisión.

## Seguridad, límites y riesgos

- La clave de IA vive únicamente en el backend.
- El proveedor puede fallar por timeout, HTTP, JSON inválido, esquema
  incompleto o configuración ausente; en todos los casos se devuelve un error
  controlado y no se persiste contenido parcial.
- El contenido generado es una sugerencia y requiere revisión humana.
- La respuesta del modelo puede ser pedagógicamente incorrecta; el UI debe
  mostrarla como borrador editable y permitir aplicar por sección.
- La revisión publicada debe volver a comprobar la versión base para evitar
  sobrescribir cambios recientes.
- Las pruebas locales cubren contratos, permisos y dobles del proveedor, pero
  no demuestran conectividad real con MongoDB, disponibilidad de DeepSeek ni
  comportamiento visual autenticado.

## Validación de aceptación

Se cubren schemas y límites, JSON válido/inválido/incompleto/cercado,
timeouts/errores HTTP/configuración, redacción de PII, conversión segura a
Tiptap, permisos `admin`/`trainer`, aplicación selectiva, conflictos y ciclo
de revisión. El contrato OpenAPI debe incluir todas las rutas anteriores.
