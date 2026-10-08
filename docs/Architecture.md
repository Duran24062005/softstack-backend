# Arquitectura del backend

## Flujo real de medios de contenido

El CMS carga imágenes, videos y portadas de módulos mediante el Route Handler BFF de Next.js. El handler comprueba la sesión administrativa y genera un token limitado para el Blob Store público de contenido. El editor conserva la URL y metadatos en el JSON Tiptap; FastAPI valida nuevamente el contrato y persiste `media_assets` junto con el documento en MongoDB.

```text
Administrador
    │ cookie HttpOnly
    ▼
Next.js /api/content-media/upload
    │ token de carga server-side
    ▼
Vercel Blob público (content-media/)
    │ url + pathname + MIME + tamaño
    ▼
Editor Tiptap / portada de módulo
    ▼
FastAPI admin content endpoint
    ├── valida referencias y nodos anidados
    ├── persiste URL en MongoDB
    └── elimina blobs retirados o huérfanos
```

Los documentos `lessons` mantienen las URLs en `content.*.attrs.src` y un array interno `media_assets`. Los documentos `modules` mantienen `cover_media` y `media_assets`. El store público permite lectura directa; las fotos de perfil continúan usando el store privado y sus endpoints autenticados.

## Flujo real de fotos de perfil

La foto de perfil sigue este flujo:

```text
Usuario autenticado
        │ multipart/form-data
        ▼
Next.js BFF /api/backend/auth/me/profile-photo
        │ cookies de sesión
        ▼
FastAPI /auth/me/profile-photo
        ├── valida MIME, firma y tamaño
        ├── guarda metadatos en MongoDB.users
        └── carga/lee/elimina el binario en Vercel Blob privado
```

MongoDB conserva el pathname, tipo, tamaño, ETag y fecha de carga. Las respuestas de usuario solo exponen `has_profile_photo`. La lectura no acepta pathnames del cliente: FastAPI resuelve el pathname desde el usuario autenticado y transmite el blob con cabeceras privadas.

El backend usa FastAPI con una arquitectura por capas y MongoDB como persistencia.

```text
HTTP -> API routes -> services -> repositories -> MongoDB
              |          |
           schemas    security
```

El `MongoClient` se crea una vez durante el lifespan de FastAPI, se expone en `app.state` y se cierra al apagar la aplicación. Los repositorios reciben la base de datos mediante dependencias para facilitar pruebas aisladas.

La autenticación se encuentra bajo `/auth`: registro, verificación de email, login, `/me`, recuperación de contraseña y logout. Los access tokens JWT se validan con Bearer; los refresh tokens se almacenan en `refresh_tokens` únicamente como hashes. Los enlaces y códigos temporales se guardan en `email_action_tokens` únicamente como hashes y se consumen una vez.

Las cuentas normales se registran con `account_status=pending` e `is_active=false`. La verificación de email no sustituye la aprobación administrativa. Solo una cuenta `active` y verificada puede iniciar sesión; `rejected` e `inactive` permanecen bloqueadas. Las cuentas cuyo email pertenece a `ADMIN_EMAILS` conservan el alta administrativa de bootstrap.

## Vertical implementada: sesión, aprendizaje y edición

La primera vertical funcional mantiene compatibilidad con Bearer, pero el cliente web usa una sesión de cookies HttpOnly (`softstack_access` y `softstack_refresh`). Registro y login crean la sesión; refresh rota el refresh token; logout lo revoca y limpia ambas cookies. El perfil admite `full_name`, email y cambio de contraseña protegido por la contraseña actual.

### Perfil académico de estudiantes

El registro público solicita un `academic_profile` a las cuentas con rol
`user`. El perfil se conserva dentro del documento `users`, pero tiene contratos
propios para no mezclar identidad con información académica:

- `GET/PUT /auth/me/academic-profile` para el estudiante autenticado.
- `GET/PUT /admin/students/{student_id}/academic-profile` para administradores.

El bloque conserva `start_year`, un grupo, una sede y URLs opcionales de
LinkedIn/GitHub. Los trainers creados por administración no reciben este
requisito. Las cuentas existentes sin el bloque permanecen compatibles y pueden
completarlo desde el dashboard. Los perfiles históricos con `memberships` se
normalizan al leerlos tomando el grupo actual o el primero, y se convierten a
la forma simple en el siguiente guardado.

El contenido publicado vive en `modules` y `lessons`. El campo `lessons.content` contiene el documento JSON de Tiptap completo, mientras que `progress` registra la finalización por usuario y lección. Las rutas editoriales requieren `require_roles("admin", "trainer")`; las rutas de gestión de usuarios, asignaciones, configuración y reinicios requieren `require_roles("admin")`. El frontend obtiene acceso admin mediante `ADMIN_EMAILS` durante el registro.

La gestión de cuentas vive en `/admin/users`. El backend devuelve roles y estados, valida las transiciones `pending → active/rejected`, `rejected → pending` y `active ↔ inactive`, y registra el último actor y momento del cambio en el documento de usuario.

## Vertical implementada: evaluaciones y trainers

Las evaluaciones viven separadas del contenido en `assessments` y `questions`. Cada lección puede tener un quiz y cada módulo una evaluación final. Los `attempts` guardan una copia inmutable de las preguntas, opciones y respuesta correcta para conservar la trazabilidad aunque el banco se edite después.

El estudiante recibe únicamente las opciones durante un intento activo. FastAPI selecciona preguntas aprobadas, reordena las opciones y evita repetir la posición de la respuesta correcta cuando el intento anterior contiene la misma pregunta. La calificación se ejecuta en backend; al aprobar se registra progreso de lección o módulo.

`assessment_states` mantiene el ciclo y los intentos disponibles. Un reinicio administrativo incrementa el ciclo, cancela un intento activo si existe y conserva los intentos históricos en `assessment_resets` y `attempts`.

El rol `trainer` puede editar contenido y evaluaciones y consultar analítica solo de estudiantes asignados mediante `trainer_assignments`. DeepSeek se integra detrás de `QuestionProvider`; sus sugerencias quedan como preguntas `suggested` hasta la aprobación humana.

El seed inicial se ejecuta explícitamente con `uv run python -m scripts.seed_content` y no se dispara durante el arranque de la API.

La superficie de evaluaciones mantiene pruebas aisladas por capa: los servicios usan repositorios falsos, las rutas se prueban con dependencias explícitas y el proveedor IA se sustituye por dobles que entregan respuestas válidas o inválidas. La CI exige cobertura de ramas focalizada de al menos 95 % y verifica que el contrato OpenAPI de intentos permanezca publicado.

## Core y middlewares

- `app/core/security.py` contiene hashing Argon2id y emisión/validación de JWT.
- `app/core/exception.py` define excepciones de aplicación y registra sus handlers HTTP globales.
- `app/middlewares/cors.py` configura CORS desde `CORS_ORIGINS`.
- `app/middlewares/auth_middleware.py` extrae el Bearer token y deja el payload validado en `request.state` sin bloquear rutas públicas.
- `app/middlewares/role_middleware.py` expone `require_roles(...)` para proteger rutas por rol.

Los controllers traducen las operaciones de entrada y los services lanzan excepciones de dominio; el handler global convierte esas excepciones en respuestas HTTP uniformes.


## Proposed Architecture

Sí. Para este proyecto yo lo estructuraría como un **LMS/CMS educativo modular**, no como un simple CRUD de artículos.

La idea central sería:

> **El administrador construye una ruta de aprendizaje → el estudiante consume contenido → realiza evaluaciones → genera intentos y puntuaciones → el sistema calcula su progreso.**

Además, mantendría **contenido, evaluaciones e historial académico separados**. Esto será importante cuando edites una lección que ya fue estudiada por estudiantes.

MongoDB encaja bien porque su modelo flexible permite documentos polimórficos y permite decidir entre documentos embebidos y referencias según los patrones de acceso. ([MongoDB][1])

---

# 1. Arquitectura funcional completa

La arquitectura conceptual sería:

```text
                         ┌──────────────────────┐
                         │       USUARIO        │
                         └──────────┬───────────┘
                                    │
                       ┌────────────▼────────────┐
                       │    AUTENTICACIÓN        │
                       │    AUTORIZACIÓN         │
                       └────────────┬────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     │                             │
              ┌──────▼──────┐              ┌──────▼──────┐
              │ ADMINISTRADOR│              │ ESTUDIANTE  │
              └──────┬──────┘              └──────┬──────┘
                     │                             │
                     │                             │
              ┌──────▼────────┐             ┌──────▼────────┐
              │    MÓDULOS    │             │    PROGRESO   │
              └──────┬────────┘             └──────▲────────┘
                     │                             │
              ┌──────▼────────┐                    │
              │   LECCIONES   │◄───────────────────┤
              └──────┬────────┘                    │
                     │                             │
              ┌──────▼────────────┐                │
              │ BLOQUES CONTENIDO │                │
              └──────┬────────────┘                │
                     │                             │
                     ▼                             │
              ┌──────────────┐                     │
              │ EVALUACIÓN   │─────────────────────┤
              └──────┬───────┘                     │
                     │                             │
                     ▼                             │
              ┌──────────────┐                     │
              │   INTENTO    │                     │
              └──────┬───────┘                     │
                     │                             │
                     ▼                             │
              ┌──────────────┐                     │
              │  PUNTUACIÓN  │─────────────────────┘
              └──────────────┘
```

---

# 2. Roles

Para el MVP **no crearía 10 roles**.

Empezaría con:

```text
ADMIN
STUDENT
```

Pero diseñaría el sistema para poder agregar permisos posteriormente.

## ADMIN

Puede:

* crear módulos
* editar módulos
* crear lecciones
* editar lecciones
* agregar contenido
* subir recursos
* crear evaluaciones
* crear preguntas
* publicar contenido
* despublicar contenido
* visualizar estudiantes
* visualizar progreso
* visualizar resultados
* gestionar usuarios

## STUDENT

Puede:

* consultar módulos publicados
* consultar lecciones
* consumir contenido
* marcar lecciones como completadas
* presentar evaluaciones
* consultar sus intentos
* consultar sus puntuaciones
* consultar su progreso

---

# 3. Autenticación y autorización

Yo separaría:

```text
Authentication
      ↓
¿Quién eres?
      ↓
Authorization
      ↓
¿Qué puedes hacer?
```

FastAPI proporciona herramientas para OAuth2/JWT y mecanismos de seguridad que puedes integrar con tus propios modelos y base de datos. ([FastAPI][2])

Una estructura inicial:

```text
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/auth/me
```

Y luego dependencias:

```text
get_current_user()
require_admin()
require_student()
```

No pondría la lógica de permisos directamente dentro de cada endpoint.

---

# 4. Módulos

El módulo representa una **gran categoría de conocimiento**.

Ejemplo:

```text
Módulo
│
├── Comunicación profesional
├── Hoja de vida
├── LinkedIn
├── Portafolio
├── Entrevistas
└── Imagen profesional
```

### MongoDB

Collection:

```text
modules
```

Documento:

```json
{
  "_id": "ObjectId",
  "title": "Hoja de vida",
  "slug": "hoja-de-vida",
  "description": "Aprende a construir una hoja de vida profesional.",
  "cover_image": {
    "url": "...",
    "alt": "..."
  },
  "order": 2,
  "status": "published",
  "created_by": "ObjectId",
  "created_at": "Date",
  "updated_at": "Date"
}
```

### Estados

```text
draft
published
archived
```

Yo **no borraría físicamente un módulo que ya tenga actividad de estudiantes**.

---

# 5. Lecciones

Un módulo tiene muchas lecciones.

```text
HOJA DE VIDA
│
├── 01. Estructura de una hoja de vida
├── 02. Perfil profesional
├── 03. Experiencia laboral
├── 04. Logros cuantificables
├── 05. Adaptación al cargo
└── 06. Errores frecuentes
```

Collection:

```text
lessons
```

```json
{
  "_id": "ObjectId",
  "module_id": "ObjectId",

  "title": "Experiencia laboral",
  "slug": "experiencia-laboral",

  "description": "Cómo presentar correctamente tu experiencia.",

  "order": 3,

  "status": "published",

  "estimated_minutes": 15,

  "created_by": "ObjectId",
  "updated_by": "ObjectId",

  "created_at": "Date",
  "updated_at": "Date"
}
```

Aquí recomiendo **referenciar el módulo**, no incrustar todas las lecciones dentro del módulo.

¿Por qué?

Porque las lecciones:

* pueden crecer bastante
* se consultan individualmente
* pueden modificarse independientemente
* tendrán evaluaciones
* tendrán estadísticas
* pueden necesitar versionado

MongoDB recomienda referencias cuando el lado hijo tiene alta cardinalidad, puede crecer sin límite o necesita existir/consultarse independientemente. ([MongoDB][3])

---

# 6. Bloques de contenido

Esta es probablemente **la decisión arquitectónica más importante del proyecto**.

No guardaría una lección así:

```json
{
  "text": "<h1>...</h1><p>...</p>"
}
```

En su lugar utilizaría un documento estructurado.

Aquí Tiptap es especialmente interesante: representa el contenido como un árbol JSON compuesto por nodos y marcas, y su esquema permite definir qué estructuras puede contener el documento. ([Tiptap][4])

Por ejemplo:

```json
{
  "type": "doc",
  "content": [
    {
      "type": "heading",
      "attrs": {
        "level": 2
      },
      "content": [
        {
          "type": "text",
          "text": "Experiencia laboral"
        }
      ]
    },
    {
      "type": "paragraph",
      "content": [
        {
          "type": "text",
          "text": "Describe tus responsabilidades..."
        }
      ]
    }
  ]
}
```

Pero además puedes crear tus propios bloques:

```text
paragraph
heading
bulletList
orderedList
image
video
quote
callout
code
table
checklist
divider
embed
```

Por ejemplo:

```text
LECCIÓN
│
├── Heading
├── Paragraph
├── Image
├── Paragraph
├── Callout
├── Video
├── Heading
├── Checklist
└── Quote
```

### ¿Embebido o colección separada?

Para **el contenido de una lección**, yo lo embebiría:

```text
lessons
   │
   └── content
         └── Tiptap JSON
```

No haría:

```text
lesson_blocks
lesson_blocks
lesson_blocks
lesson_blocks
```

porque aumentaría muchísimo la complejidad.

MongoDB recomienda embedding cuando los datos forman una relación "contiene", se consultan juntos y se actualizan juntos. ([MongoDB][5])

---

# 7. Pero cuidado con las imágenes y videos

MongoDB **no debería almacenar el archivo multimedia directamente**.

Separaría:

```text
MongoDB
   │
   └── metadata + URL
```

de:

```text
Object Storage
   │
   ├── images
   ├── videos
   └── documents
```

Por ejemplo:

```json
{
  "type": "image",
  "attrs": {
    "src": "https://storage/.../cv-example.webp",
    "alt": "Ejemplo de hoja de vida",
    "width": 1200
  }
}
```

Esto evita convertir MongoDB en almacenamiento de archivos.

MongoDB tiene un límite de 16 MiB por documento y recomienda mecanismos específicos como GridFS para archivos binarios grandes. ([MongoDB][5])

Para tu caso, preferiría inicialmente un object storage externo.

---

# 8. Evaluaciones

Una lección puede tener:

```text
LECCIÓN
   │
   └── EVALUACIÓN
         │
         ├── Pregunta 1
         ├── Pregunta 2
         ├── Pregunta 3
         └── Pregunta 4
```

Collection:

```text
assessments
```

```json
{
  "_id": "ObjectId",
  "lesson_id": "ObjectId",

  "title": "Evaluación: Experiencia laboral",

  "instructions": "Selecciona la respuesta correcta.",

  "passing_score": 70,

  "max_attempts": 3,

  "status": "published",

  "created_at": "Date",
  "updated_at": "Date"
}
```

---

# 9. Preguntas

Aquí yo **sí usaría otra colección**:

```text
questions
```

Porque las preguntas pueden crecer bastante y luego puedes querer reutilizarlas.

```json
{
  "_id": "ObjectId",

  "assessment_id": "ObjectId",

  "type": "single_choice",

  "question": "¿Cuál descripción representa mejor un logro profesional?",

  "options": [
    {
      "id": "a",
      "text": "Desarrollé aplicaciones web."
    },
    {
      "id": "b",
      "text": "Reduje el tiempo de procesamiento en un 30%."
    }
  ],

  "correct_answer": ["b"],

  "explanation": "La segunda respuesta cuantifica el resultado.",

  "points": 10,

  "order": 1
}
```

Tipos que dejaría preparados:

```text
single_choice
multiple_choice
true_false
```

Y posteriormente:

```text
ordering
matching
short_answer
case_study
```

Pero para el MVP:

**single_choice + multiple_choice + true_false**.

---

# 10. Una decisión crítica: no devolver las respuestas correctas

Este endpoint:

```text
GET /assessments/{id}
```

NO debería devolver:

```json
"correct_answer": ["b"]
```

al estudiante.

Porque entonces alguien podría simplemente inspeccionar:

```text
Network → API → Response
```

y encontrar las respuestas.

El backend debe enviar:

```json
{
  "id": "...",
  "question": "...",
  "options": [...]
}
```

Y guardar las respuestas correctas **solo en backend**.

---

# 11. Intentos

Aquí comienza el verdadero sistema académico.

Cuando el estudiante empieza una evaluación:

```text
POST /assessments/{id}/attempts
```

Se crea:

```json
{
  "_id": "ObjectId",
  "assessment_id": "ObjectId",
  "student_id": "ObjectId",

  "attempt_number": 1,

  "status": "in_progress",

  "started_at": "Date",

  "answers": []
}
```

Luego:

```text
POST /attempts/{id}/answers
```

o, más sencillo para el MVP:

```text
POST /attempts/{id}/submit
```

enviando todo el examen.

---

# 12. ¿Por qué guardar los intentos?

Porque no quieres simplemente:

```text
student.score = 80
```

Quieres saber:

```text
Juan
│
├── Intento 1 → 60%
├── Intento 2 → 70%
└── Intento 3 → 90%
```

Entonces:

```text
attempts
```

sería algo parecido a:

```json
{
  "_id": "ObjectId",

  "student_id": "ObjectId",
  "assessment_id": "ObjectId",

  "attempt_number": 3,

  "answers": [
    {
      "question_id": "ObjectId",
      "selected_options": ["b"],
      "is_correct": true,
      "points_earned": 10
    }
  ],

  "score": {
    "earned": 90,
    "maximum": 100,
    "percentage": 90
  },

  "passed": true,

  "started_at": "Date",
  "submitted_at": "Date"
}
```

Esto es un **registro histórico**.

No deberías modificarlo después de enviarlo.

---

# 13. Puntuación

Aquí hay que distinguir:

### Score de una evaluación

```text
90 / 100
```

### Resultado

```text
PASSED
```

### Progreso de una lección

```text
COMPLETED
```

### Progreso del módulo

```text
4 / 6 lecciones
66%
```

No mezclaría todo en un único campo.

---

# 14. Progreso

Collection:

```text
progress
```

Documento:

```json
{
  "_id": "ObjectId",

  "student_id": "ObjectId",
  "module_id": "ObjectId",
  "lesson_id": "ObjectId",

  "status": "completed",

  "started_at": "Date",
  "completed_at": "Date",

  "last_accessed_at": "Date",

  "best_score": 90
}
```

Estados:

```text
not_started
in_progress
completed
```

---

# 15. ¿Cuándo una lección está completada?

Aquí tienes que definir una regla de negocio.

Por ejemplo:

```text
LECCIÓN COMPLETADA =
    estudiante abrió la lección
    +
    llegó al final
    +
    aprobó evaluación
```

O:

```text
LECCIÓN COMPLETADA =
    estudiante llegó al final
```

Yo para tu proyecto utilizaría:

```text
Contenido visto
        +
Evaluación aprobada
        =
Lección completada
```

porque tu objetivo no es simplemente que el estudiante "lea".

Quieres comprobar:

> **¿Entendió?**

---

# 16. Progreso del módulo

Supongamos:

```text
Hoja de vida

6 lecciones
│
├── ✓ Estructura
├── ✓ Perfil
├── ✓ Experiencia
├── ✓ Logros
├── ○ Adaptación
└── ○ Errores
```

Entonces:

```text
completed = 4
total = 6

progress = 66.67%
```

Esto puede calcularse dinámicamente.

No necesitas almacenar necesariamente:

```text
progress_percentage: 66.67
```

porque es un **dato derivado**.

MongoDB contempla patrones de valores calculados cuando almacenar resultados precomputados tiene sentido para las consultas. ([MongoDB][6])

Para el MVP:

**calcularlo**.

Cuando tengas mucho tráfico:

**considerar materializarlo**.

---

# 17. Administración

Ahora viene el CMS.

Yo tendría:

```text
/admin
```

y dentro:

```text
/admin/dashboard

/admin/users

/admin/modules

/admin/modules/:id

/admin/lessons/:id

/admin/assessments/:id

/admin/questions

/admin/resources

/admin/statistics
```

---

# 18. Dashboard administrativo

El administrador debería poder ver:

```text
┌──────────────────────────────────────────────┐
│ Dashboard                                    │
│                                              │
│ Estudiantes              248                 │
│ Módulos                  8                   │
│ Lecciones                47                  │
│ Evaluaciones             39                  │
│                                              │
│ ──────────────────────────────────────────── │
│                                              │
│ Progreso promedio          68%               │
│                                              │
│ Evaluaciones realizadas   1,284              │
│                                              │
│ Módulos más completados                      │
│                                              │
└──────────────────────────────────────────────┘
```

---

# 19. Arquitectura de MongoDB

Yo empezaría con estas collections:

```text
users
modules
lessons
assessments
questions
attempts
progress
media
```

Opcionalmente:

```text
audit_logs
lesson_versions
refresh_tokens
```

---

# 20. Relaciones

Visualmente:

```text
USERS
 │
 │
 ├──────────────────────┐
 │                      │
 ▼                      ▼
PROGRESS              ATTEMPTS
 │                      │
 │                      ▼
 │                 ASSESSMENTS
 │                      │
 │                      ▼
 │                  QUESTIONS
 │
 ▼
MODULES
 │
 ▼
LESSONS
 │
 ├──────────────► CONTENT
 │
 └──────────────► ASSESSMENT
```

Más específicamente:

```text
User
 │
 ├──< Progress
 │
 └──< Attempt


Module
 │
 └──< Lesson
         │
         └──< Assessment
                 │
                 └──< Question


Student
 │
 └──< Progress
          │
          ├── Module
          └── Lesson
```

---

# 21. Índices MongoDB

Esto es algo que quiero que tengas desde el principio.

### users

```text
email → unique
```

### modules

```text
slug → unique
status
order
```

### lessons

```text
module_id + order
status
slug
```

### assessments

```text
lesson_id
```

### questions

```text
assessment_id + order
```

### attempts

```text
student_id + assessment_id
student_id + submitted_at
assessment_id
```

### progress

```text
student_id + lesson_id → unique
student_id + module_id
```

Especialmente:

```text
student_id + lesson_id
```

debería ser único para evitar:

```text
Alex → Lesson 1 → progress
Alex → Lesson 1 → progress
Alex → Lesson 1 → progress
```

---

# 22. API de FastAPI

Ahora sí podemos convertir el dominio en API.

Yo utilizaría:

```text
/api/v1
```

FastAPI permite dividir la aplicación mediante `APIRouter`, incluyendo prefijos, tags y dependencias, lo que encaja muy bien con esta separación por dominios. ([FastAPI][7])

---

# AUTH

```http
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
GET    /api/v1/auth/me
```

---

# USERS

Administración:

```http
GET    /api/v1/users
GET    /api/v1/users/{id}
POST   /api/v1/users
PATCH  /api/v1/users/{id}
DELETE /api/v1/users/{id}
```

Perfil:

```http
GET    /api/v1/me
PATCH  /api/v1/me
```

---

# MODULES

Público autenticado:

```http
GET /api/v1/modules
GET /api/v1/modules/{id}
```

Admin:

```http
POST   /api/v1/admin/modules
PATCH  /api/v1/admin/modules/{id}
DELETE /api/v1/admin/modules/{id}

POST /api/v1/admin/modules/{id}/publish
POST /api/v1/admin/modules/{id}/archive
```

---

# LESSONS

Estudiante:

```http
GET /api/v1/modules/{module_id}/lessons
GET /api/v1/lessons/{id}
```

Admin:

```http
POST   /api/v1/admin/modules/{module_id}/lessons
PATCH  /api/v1/admin/lessons/{id}
DELETE /api/v1/admin/lessons/{id}

POST /api/v1/admin/lessons/{id}/publish
POST /api/v1/admin/lessons/{id}/archive
```

---

# CONTENT

Aquí no necesitas necesariamente endpoints separados para cada bloque.

Puedes manejar:

```http
GET   /api/v1/lessons/{id}/content
PATCH /api/v1/admin/lessons/{id}/content
```

El body:

```json
{
  "content": {
    "type": "doc",
    "content": []
  }
}
```

---

# MEDIA

```http
POST   /api/v1/admin/media
GET    /api/v1/admin/media
GET    /api/v1/admin/media/{id}
DELETE /api/v1/admin/media/{id}
```

Pero aquí probablemente FastAPI generará una URL firmada para subir directamente al storage.

Flujo:

```text
Next.js
   │
   │ solicitar upload
   ▼
FastAPI
   │
   │ signed URL
   ▼
Storage
   │
   │ upload
   ▼
Next.js
   │
   │ guardar metadata
   ▼
FastAPI
```

Así evitas hacer pasar videos grandes por FastAPI.

---

# ASSESSMENTS

Estudiante:

```http
GET /api/v1/lessons/{lesson_id}/assessment
GET /api/v1/assessments/{id}
```

Admin:

```http
POST   /api/v1/admin/lessons/{lesson_id}/assessment
PATCH  /api/v1/admin/assessments/{id}
DELETE /api/v1/admin/assessments/{id}
```

---

# QUESTIONS

```http
POST   /api/v1/admin/assessments/{id}/questions
PATCH  /api/v1/admin/questions/{id}
DELETE /api/v1/admin/questions/{id}
```

Y:

```http
PATCH /api/v1/admin/questions/{id}/order
```

---

# ATTEMPTS

Estudiante:

```http
POST /api/v1/assessments/{id}/attempts
GET  /api/v1/attempts/{id}
POST /api/v1/attempts/{id}/submit
```

Historial:

```http
GET /api/v1/me/attempts
GET /api/v1/assessments/{id}/my-attempts
```

Admin:

```http
GET /api/v1/admin/attempts
GET /api/v1/admin/attempts/{id}
```

---

# PROGRESS

```http
GET /api/v1/me/progress
GET /api/v1/me/progress/modules
GET /api/v1/me/progress/modules/{id}
GET /api/v1/me/progress/lessons/{id}
```

Cuando termina una lección:

```http
POST /api/v1/lessons/{id}/complete
```

Aunque internamente recomiendo que el backend determine si realmente puede marcarla como completada.

No confíes simplemente en:

```json
{
  "completed": true
}
```

enviado por el frontend.

---

# ADMIN STATISTICS

```http
GET /api/v1/admin/statistics/overview

GET /api/v1/admin/statistics/students

GET /api/v1/admin/statistics/modules/{id}

GET /api/v1/admin/statistics/assessments/{id}
```

Por ejemplo:

```json
{
  "students": 248,
  "active_students": 201,
  "completed_modules": 732,
  "assessment_attempts": 1284,
  "average_score": 78.4
}
```

---

# 23. Estructura del backend

No haría:

```text
routers/
services/
models/
```

con todo mezclado.

Para este proyecto prefiero organizarlo por **dominio**:

```text
backend/
│
├── app/
│   │
│   ├── main.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── database.py
│   │
│   ├── modules/
│   │
│   │   ├── auth/
│   │   │   ├── router.py
│   │   │   ├── service.py
│   │   │   ├── repository.py
│   │   │   ├── schemas.py
│   │   │   └── models.py
│   │   │
│   │   ├── users/
│   │   │
│   │   ├── learning/
│   │   │   ├── modules/
│   │   │   ├── lessons/
│   │   │   ├── content/
│   │   │   └── progress/
│   │   │
│   │   ├── assessments/
│   │   │   ├── router.py
│   │   │   ├── service.py
│   │   │   ├── repository.py
│   │   │   ├── schemas.py
│   │   │   └── models.py
│   │   │
│   │   ├── attempts/
│   │   │
│   │   ├── media/
│   │   │
│   │   └── administration/
│   │
│   └── shared/
│       ├── exceptions.py
│       ├── pagination.py
│       └── enums.py
│
└── tests/
```

Esto está alineado con la forma en que FastAPI permite separar aplicaciones grandes mediante `APIRouter`. ([FastAPI][8])

---

# 24. Flujo completo de un estudiante

Este sería el flujo que deberías poder demostrar en el MVP:

```text
LOGIN
 │
 ▼
DASHBOARD
 │
 ▼
MÓDULOS
 │
 ▼
HOJA DE VIDA
 │
 ▼
LECCIÓN
 │
 ├── Leer texto
 ├── Ver imagen
 ├── Ver video
 ├── Revisar ejemplo
 └── Checklist
 │
 ▼
EVALUACIÓN
 │
 ▼
INICIAR INTENTO
 │
 ▼
RESPONDER
 │
 ▼
ENVIAR
 │
 ▼
BACKEND CALCULA
 │
 ├── respuestas correctas
 ├── puntos
 ├── porcentaje
 └── aprobado
 │
 ▼
GUARDAR INTENTO
 │
 ▼
ACTUALIZAR PROGRESO
 │
 ▼
LECCIÓN COMPLETADA
 │
 ▼
ACTUALIZAR PROGRESO DEL MÓDULO
```

---

# 25. Flujo completo del administrador

```text
LOGIN
 │
 ▼
ADMIN DASHBOARD
 │
 ▼
CREAR MÓDULO
 │
 ▼
CREAR LECCIÓN
 │
 ▼
ABRIR EDITOR
 │
 ├── Texto
 ├── Heading
 ├── Imagen
 ├── Video
 ├── Callout
 ├── Lista
 └── etc.
 │
 ▼
GUARDAR BORRADOR
 │
 ▼
CREAR EVALUACIÓN
 │
 ▼
CREAR PREGUNTAS
 │
 ▼
PREVISUALIZAR
 │
 ▼
PUBLICAR
 │
 ▼
ESTUDIANTES PUEDEN ACCEDER
```

---

# 26. Hay una cosa que agregaría: Draft vs Published

Esto es **muy importante** para el CMS.

Nunca deberías editar directamente lo que el estudiante está consumiendo sin ningún control.

Tendrías:

```text
DRAFT
   │
   │ Publish
   ▼
PUBLISHED
   │
   │ Archive
   ▼
ARCHIVED
```

Y más adelante:

```text
VERSION 1
   │
   ▼
VERSION 2
   │
   ▼
VERSION 3
```

MongoDB contempla explícitamente patrones de versionado de documentos para esquemas y requisitos que evolucionan. ([MongoDB][6])

Para tu **MVP**, sin embargo:

> implementaría `draft / published / archived` primero.

No construiría versionado todavía.

---

# 27. El modelo final

Entonces tu dominio queda:

```text
                         ┌──────────────┐
                         │     USER     │
                         └──────┬───────┘
                                │
                 ┌──────────────┴─────────────┐
                 │                            │
                 ▼                            ▼
             PROGRESS                      ATTEMPT
                 │                            │
                 │                            ▼
                 │                       ASSESSMENT
                 │                            │
                 │                            ▼
                 │                        QUESTION
                 │
                 ▼
              MODULE
                 │
                 ▼
              LESSON
                 │
           ┌─────┴─────┐
           │           │
           ▼           ▼
        CONTENT    ASSESSMENT
```

Y en MongoDB:

```text
users
modules
lessons
assessments
questions
attempts
progress
media
```

Con:

```text
draft
published
archived
```

como ciclo de vida del contenido.

---

# 28. Lo que NO construiría todavía

Para que el proyecto sea alcanzable, **dejaría fuera del MVP**:

```text
❌ Colaboración simultánea tipo Notion
❌ Comentarios
❌ Chat
❌ IA
❌ Gamificación compleja
❌ Ranking global
❌ Certificados
❌ Versionado avanzado
❌ Editor multimedia complejo
❌ Analítica avanzada
❌ Recomendaciones personalizadas
❌ Microservicios
```

El proyecto ya tiene suficiente complejidad.

---

# 29. MVP que realmente te recomiendo

Tu primera versión debería demostrar solamente esto:

```text
                  ┌───────────────┐
                  │     ADMIN     │
                  └───────┬───────┘
                          │
                          ▼
                    Crear módulo
                          │
                          ▼
                   Crear lección
                          │
                          ▼
                  Editar contenido
                          │
                          ▼
                 Crear evaluación
                          │
                          ▼
                       Publicar
                          │
                          ▼
                  ┌───────────────┐
                  │   ESTUDIANTE  │
                  └───────┬───────┘
                          │
                          ▼
                     Ver módulo
                          │
                          ▼
                     Leer lección
                          │
                          ▼
                     Presentar
                     evaluación
                          │
                          ▼
                       Resultado
                          │
                          ▼
                       Progreso
```

**Si consigues que ese flujo funcione de punta a punta, ya tienes el núcleo del producto.**

Después puedes agregar todo lo demás.

---

## Mi recomendación arquitectónica final

Para tu caso concreto quedaría así:

```text
                 NEXT.JS
                    │
          ┌─────────┴─────────┐
          │                   │
     STUDENT UI           ADMIN CMS
          │                   │
          └─────────┬─────────┘
                    │
                  REST
                    │
                FASTAPI
                    │
       ┌────────────┼────────────┐
       │            │            │
      AUTH       LEARNING    ASSESSMENTS
       │            │            │
       │            │            │
       └────────────┼────────────┘
                    │
                 SERVICES
                    │
               REPOSITORIES
                    │
             ┌──────┴──────┐
             │             │
          MongoDB       Storage
                         │
                  Images / Videos
```

Y hay una decisión que considero especialmente buena para tu proyecto: **Tiptap + MongoDB para el contenido estructurado**, en lugar de intentar inventar tu propio editor. Tiptap ya trabaja con un árbol JSON de nodos/marcas y permite extender el esquema mediante extensiones. ([Tiptap][4])

### Orden en el que yo lo desarrollaría

```text
01. Auth + Roles
        ↓
02. Modules
        ↓
03. Lessons
        ↓
04. Tiptap Editor
        ↓
05. Media Storage
        ↓
06. Assessments
        ↓
07. Questions
        ↓
08. Attempts
        ↓
09. Scoring
        ↓
10. Progress
        ↓
11. Admin Dashboard
        ↓
12. Student Dashboard
        ↓
13. Analytics
```

Eso te da una ruta de implementación bastante clara y, sobre todo, evita que empieces construyendo el frontend sin tener definido **qué representa cada entidad y quién tiene autoridad sobre cada dato**.

[1]: https://www.mongodb.com/es/docs/v8.0/data-modeling/?utm_source=chatgpt.com "Modelado de datos en MongoDB - Manual de base de datos v8.0 - MongoDB Docs"
[2]: https://fastapi.tiangolo.com/es/tutorial/security/oauth2-jwt/?utm_source=chatgpt.com "OAuth2 con Password (y hashing), Bearer con tokens JWT - FastAPI"
[3]: https://www.mongodb.com/es/docs/v8.0/data-modeling/best-practices/?utm_source=chatgpt.com "Mejores prácticas para modelado de datos en MongoDB - Manual de base de datos v8.0 - MongoDB Docs"
[4]: https://tiptap.dev/docs/editor/core-concepts/introduction?utm_source=chatgpt.com "Tiptap Concepts | Tiptap Editor Docs"
[5]: https://www.mongodb.com/docs/manual/data-modeling/embedding/?utm_source=chatgpt.com "Embedded Data in Your MongoDB Schema - Database Manual - MongoDB Docs"
[6]: https://www.mongodb.com/docs/v8.0/data-modeling/design-patterns/?utm_source=chatgpt.com "Schema Design Patterns - Database Manual v8.0 - MongoDB Docs"
[7]: https://fastapi.tiangolo.com/es/tutorial/bigger-applications/?utm_source=chatgpt.com "Aplicaciones más grandes - Múltiples archivos - FastAPI"
[8]: https://fastapi.tiangolo.com/tutorial/bigger-applications/?utm_source=chatgpt.com "Bigger Applications - Multiple Files - FastAPI"
