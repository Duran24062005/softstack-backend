# Propuesta institucional de formación y habilitación en empleabilidad

## SoftStack · Campuslands

| Campo | Definición |
| --- | --- |
| Estado | Propuesta para aprobación institucional |
| Versión | 1.0 |
| Fecha | 4 de octubre de 2026 |
| Audiencia | Dirección, área educativa, trainers, equipo de empleabilidad y equipo de tecnología |
| Cobertura propuesta | Todos los campers vinculados a Campuslands |
| Escala de referencia | Hasta 500 campers activos |
| Decisión solicitada | Aprobar la implementación institucional completa del modelo |

> **Nota de trazabilidad.** Este documento se versiona en `softstack-backend/docs` como propuesta rectora del modelo institucional. Debido a que sus decisiones también afectan al frontend y a la operación educativa, cada capacidad aprobada deberá documentar sus contratos e impactos en el repositorio o área responsable, enlazando este documento como fuente de contexto y evitando copias divergentes.

---

## 1. Resumen ejecutivo

Campuslands prepara talento técnico para ingresar al mercado laboral, pero el dominio de programación no garantiza que un camper pueda presentar su experiencia, construir un currículum competitivo, explicar el impacto de sus proyectos o desenvolverse correctamente en una entrevista. Estas competencias requieren práctica deliberada, evidencia observable, retroalimentación y un estándar institucional común.

SoftStack ya dispone de una base LMS funcional: autenticación, módulos, lecciones, contenido multimedia, edición administrativa y registro básico de lecciones completadas. Sin embargo, hoy completar una lección equivale esencialmente a marcarla como terminada. El sistema todavía no permite demostrar dominio, entregar evidencias, realizar evaluaciones, gestionar cohortes, asignar trainers, identificar brechas por competencia ni determinar formalmente si una persona está preparada para ser presentada a una empresa.

Esta propuesta convierte SoftStack en un **sistema de preparación demostrada para el empleo**. El modelo no buscará obligar al estudiante a mantener una pestaña abierta durante una cantidad arbitraria de minutos. Exigirá resultados verificables:

- comprender los conceptos mediante microevaluaciones;
- aplicar cada competencia en una evidencia concreta;
- corregir errores mediante refuerzos y nuevos intentos;
- demostrar desempeño en una entrevista simulada presencial;
- satisfacer un conjunto explícito y auditable de requisitos antes de acceder a procesos de empleabilidad.

La ruta será obligatoria para todos los campers, tendrá una dedicación estimada de 10 a 12 horas, podrá recorrerse en orden libre y no impondrá fechas límite por actividad. La consecuencia institucional será clara: **una persona que no complete y apruebe todos los requisitos permanecerá en estado `NO APTO` y no deberá ser postulada o recomendada a empresas por los canales oficiales de Campuslands**.

La inteligencia artificial tendrá un papel de apoyo, no de autoridad académica. DeepSeek se propone como proveedor inicial por costo y capacidad de producir salidas estructuradas, pero se integrará mediante una interfaz intercambiable. La IA podrá proponer bancos de preguntas y ofrecer retroalimentación sobre texto previamente anonimizado. Las evaluaciones objetivas se calificarán con reglas deterministas y las decisiones sobre evidencias, apelaciones y habilitación laboral permanecerán bajo control humano.

La aprobación solicitada comprende cinco decisiones institucionales:

1. Adoptar la preparación demostrada como requisito formal de empleabilidad.
2. Autorizar la evolución funcional de SoftStack en backend y frontend.
3. Designar al área educativa como propietaria del currículo, las rúbricas y los bancos de preguntas.
4. Asignar entre 3 y 5 trainers para revisión, refuerzo y entrevistas simuladas.
5. Autorizar la revisión jurídica y de privacidad previa al tratamiento de información mediante proveedores externos de IA.

---

## 2. Problema y oportunidad institucional

### 2.1 Problema observado

Los campers pueden tener conocimientos técnicos valiosos y, aun así, perder oportunidades por dificultades como:

- describir responsabilidades en lugar de logros;
- no cuantificar resultados ni explicar el impacto de una solución;
- desconocer estructuras como XYZ para CV o STAR para entrevistas;
- presentar portafolios, perfiles o currículums sin una propuesta de valor clara;
- responder de forma desordenada o demasiado extensa;
- no preparar adecuadamente el entorno, la cámara, el fondo, la postura o la vestimenta en entrevistas virtuales;
- no saber hacer seguimiento después de una entrevista o conversar sobre aspiración salarial;
- consumir información, pero no convertirla en comportamientos observables.

El problema no es solamente de acceso a contenidos. Es un problema de **transferencia entre conocimiento y desempeño**. Publicar más lecturas o videos no garantiza que el camper pueda ejecutar la competencia cuando una empresa lo evalúe.

### 2.2 Oportunidad para Campuslands

Un estándar común de preparación permite que Campuslands:

- reduzca la variabilidad con la que los campers se presentan ante empresas;
- detecte brechas antes de una postulación real;
- concentre el acompañamiento de trainers donde exista mayor dificultad;
- construya evidencia auditable de la preparación entregada;
- proteja la reputación institucional asociada a cada candidato recomendado;
- transforme datos educativos en decisiones de refuerzo y mejora curricular;
- conecte progresivamente el aprendizaje con resultados como entrevistas y contrataciones.

El valor no consiste en afirmar que la plataforma garantiza un empleo. Consiste en asegurar que las personas postuladas por Campuslands hayan demostrado un conjunto mínimo, consistente y verificable de competencias de empleabilidad.

---

## 3. Estado actual comprobado de SoftStack

La revisión de los repositorios `softstack-backend` y `softstack-frontend` muestra una base adecuada para evolucionar hacia este modelo, sin necesidad de reemplazar la plataforma existente.

| Capacidad | Estado actual | Brecha para el modelo propuesto |
| --- | --- | --- |
| Autenticación y perfil | Implementada con sesión por cookies, verificación de correo y perfil | Falta asociación institucional con cohorte y trainer |
| Roles | Existen `user` y `admin` | Falta el rol `trainer` y permisos educativos diferenciados |
| Módulos y lecciones | Implementados con estados, orden, contenido Tiptap y multimedia | Falta asociar resultados de aprendizaje, competencias y requisitos |
| Progreso | Se registra una finalización idempotente por lección | No demuestra dominio ni conserva intentos, notas o refuerzos |
| Evaluaciones | No implementadas | Se necesitan bancos versionados, microquizzes, intentos y calificación determinista |
| Evidencias | No implementadas | Se necesitan entregas privadas, versiones, rúbricas y revisiones |
| Cohortes | No implementadas | Se requieren agrupación, asignaciones y filtros operativos |
| Trainers | No implementados | Se requieren bandejas de revisión, seguimiento y registro de intervención |
| Mock interviews | No implementadas | Se necesita una rúbrica presencial registrada y auditable |
| Analítica educativa | Solo se muestra porcentaje de lecciones completadas | Se requieren brechas por competencia, intentos, refuerzos y carga de revisión |
| Habilitación laboral | No implementada | Se necesita un estado oficial `APTO` / `NO APTO`, exportable e integrable |
| Inteligencia artificial | No implementada | Se requiere generación gobernada, anonimización, costos y auditoría |

Esta propuesta no asume que el catálogo actual sea el currículo definitivo. Los cinco módulos y trece lecciones existentes constituyen una referencia valiosa, pero el área educativa conservará la autoridad para aprobar, reorganizar, reemplazar o ampliar los contenidos, evidencias y resultados de aprendizaje.

---

## 4. Modelo institucional propuesto

### 4.1 Principios de diseño

1. **Demostrar antes que declarar.** El avance debe depender de conocimiento recuperado y evidencia aplicada, no de tiempo de pantalla.
2. **Dominio por competencia.** Una fortaleza no debe ocultar una brecha crítica en otra área; cada evaluación obligatoria debe aprobarse.
3. **Refuerzo antes que castigo.** Fallar activa retroalimentación y práctica adicional, no una exclusión definitiva.
4. **IA con supervisión humana.** La tecnología acelera tareas, pero no toma decisiones sensibles de forma autónoma.
5. **Reglas visibles y auditables.** El camper debe saber qué falta, cómo se evalúa y por qué tiene determinado estado.
6. **Datos para intervenir.** Los paneles deben facilitar acciones educativas, no limitarse a mostrar porcentajes decorativos.
7. **Privacidad desde el diseño.** Los datos personales y académicos solo se usarán para finalidades explícitas y con acceso mínimo necesario.

### 4.2 Recorrido del camper

```text
Autorregistro y verificación
            │
            ▼
Asignación a cohorte y trainer
            │
            ▼
Ruta modular en orden libre
            │
            ├── Lección
            │     ├── Contenido
            │     ├── Microquiz aleatorio
            │     ├── Aprobación ≥ 80 %
            │     └── Refuerzo + nuevo intento si no aprueba
            │
            ├── Evidencia práctica por módulo
            │     ├── Feedback automatizado anonimizado
            │     ├── Corrección del camper
            │     └── Revisión humana con rúbrica
            │
            ▼
Mock interview presencial
            │
            ▼
Motor de reglas de habilitación
            │
            ├── NO APTO: requisitos pendientes o no aprobados
            └── APTO: elegible para procesos de empleabilidad
```

### 4.3 Dedicación y libertad de recorrido

- La dedicación total estimada será de **10 a 12 horas**.
- El camper podrá elegir el orden de los módulos y lecciones disponibles.
- No existirán fechas límite obligatorias por lección o módulo.
- SoftStack podrá enviar recordatorios no bloqueantes y mostrar el impacto de los pendientes sobre el estado de preparación.
- La ausencia de fechas no elimina el requisito final: toda la ruta deberá estar aprobada antes de acceder a procesos oficiales de empleabilidad.

Esta decisión favorece la autonomía, pero crea un riesgo de acumulación al final. Por ello, el panel deberá mostrar anticipadamente la carga pendiente y el equipo educativo deberá monitorear la demanda de revisiones para evitar cuellos de botella.

### 4.4 Definición de avance

| Nivel | Condición de cumplimiento |
| --- | --- |
| Lección estudiada | El camper accedió al contenido; este evento es informativo y no acredita dominio |
| Lección aprobada | Obtuvo al menos 80 % en su microquiz obligatorio |
| Módulo aprobado | Aprobó todas sus lecciones y la evidencia del módulo fue aceptada mediante rúbrica |
| Ruta académica aprobada | Todos los módulos obligatorios están aprobados |
| Preparación integral aprobada | Ruta académica aprobada y mock interview presencial aceptada |
| Habilitación laboral | El motor de reglas genera estado oficial `APTO` y no existen bloqueos administrativos |

### 4.5 Microquizzes por lección

Cada lección tendrá entre 3 y 5 preguntas seleccionadas aleatoriamente desde un banco previamente aprobado. El número de respuestas correctas requerido será el entero inmediatamente superior o igual al 80 % del total:

| Preguntas | Respuestas correctas requeridas |
| ---: | ---: |
| 3 | 3 |
| 4 | 4 |
| 5 | 4 |

Para que el umbral tenga mayor granularidad, se recomienda usar cinco preguntas calificables por defecto. Las evaluaciones podrán incluir selección única, selección múltiple, ordenamiento y casos situacionales con opciones cerradas. Las preguntas abiertas podrán utilizarse para práctica y feedback, pero no deberán definir automáticamente un bloqueo laboral.

Reglas de reintento:

- no habrá un límite definitivo de intentos;
- después de un intento fallido, el sistema mostrará conceptos por reforzar, no únicamente la respuesta correcta;
- el camper deberá completar una actividad breve de refuerzo antes de reintentar;
- el nuevo intento usará otra combinación de preguntas cuando el banco lo permita;
- todos los intentos se conservarán para medir dificultad, recuperación y calidad de las preguntas;
- la nota aprobatoria no borrará el historial anterior.

### 4.6 Evidencias por módulo

Cada módulo obligatorio culminará en una evidencia aplicable al proceso laboral. El área educativa definirá su versión final. Tomando como referencia el catálogo actual, podrían considerarse:

| Área de referencia | Evidencia ilustrativa |
| --- | --- |
| Presencia y etiqueta profesional | Plan de preparación de entrevista virtual y resolución de casos situacionales |
| CV y filtros ATS | Currículum adaptado a una vacante y logros redactados con evidencia cuantificable |
| Marca personal y portafolio | Diagnóstico y plan de mejora de LinkedIn, GitHub o portafolio |
| Comunicación en entrevistas | Pitch profesional y respuestas escritas con estructura STAR |
| Negociación y seguimiento | Rango salarial argumentado y mensajes de agradecimiento o seguimiento |

Las evidencias serán privadas. Podrán incluir texto, documentos y enlaces controlados. Cada entrega conservará versiones, fecha, autor, rúbrica aplicada, observaciones y decisión. La IA podrá producir feedback preliminar sobre una copia anonimizada, pero un trainer deberá aceptar o solicitar cambios sobre la versión final.

### 4.7 Mock interview presencial

Las competencias de presentación personal, postura, entorno, manejo de cámara, escucha y comunicación oral no pueden validarse de forma suficiente mediante texto. Por ello, la entrevista simulada será presencial o sincrónica con un trainer y su resultado quedará registrado en SoftStack.

La rúbrica deberá incluir, como mínimo:

- preparación del entorno y presentación personal;
- claridad y duración del pitch;
- estructura de respuestas;
- uso de ejemplos y resultados verificables;
- escucha, contacto visual y lenguaje corporal;
- capacidad de formular preguntas al entrevistador;
- cierre y seguimiento;
- fortalezas, brechas y plan de refuerzo.

El área educativa definirá los descriptores de cada nivel y el estándar mínimo. El resultado podrá ser `APROBADA`, `REQUIERE_REFUERZO` o `PENDIENTE_DE_REVISIÓN`. Una nueva simulación deberá quedar disponible después del refuerzo cuando el resultado no sea aprobatorio.

### 4.8 Regla oficial de habilitación

El estado oficial será binario para el proceso de empleabilidad:

```text
APTO =
  todas las microevaluaciones obligatorias aprobadas
  AND todas las evidencias obligatorias aceptadas
  AND mock interview aprobada
  AND cuenta activa
  AND sin revisión o apelación pendiente

NO APTO = cualquier otra condición
```

La interfaz podrá mostrar estados operativos más explicativos —`EN PROGRESO`, `REQUIERE REFUERZO`, `PENDIENTE DE REVISIÓN`—, pero las integraciones externas recibirán únicamente el estado oficial, la fecha de cálculo, la versión de reglas y los motivos estructurados de los requisitos pendientes. Ningún administrador deberá editar manualmente el valor final sin registrar una excepción justificada y auditable.

---

## 5. Gobierno y responsabilidades

### 5.1 Actores

| Actor | Responsabilidades principales |
| --- | --- |
| Camper | Completar la ruta, responder evaluaciones, entregar evidencias, aplicar feedback y asistir a la mock interview |
| Trainer | Acompañar cohortes asignadas, revisar evidencias, registrar rúbricas, realizar refuerzos y mock interviews |
| Administrador SoftStack | Gestionar usuarios, cohortes, asignaciones, permisos, publicación y configuración operativa |
| Área educativa | Aprobar currículo, competencias, rúbricas, bancos de preguntas, reglas de refuerzo y cambios de versión |
| Equipo de empleabilidad | Consultar la habilitación, usarla antes de postular y registrar resultados posteriores cuando exista integración |
| Tecnología | Implementar, operar, monitorear, controlar costos y mantener seguridad y trazabilidad |
| Jurídica o responsable de datos | Validar bases legales, consentimientos, proveedores, transferencias y tratamiento de datos de menores |

### 5.2 Separación de permisos

- El rol `admin` administrará configuración global, contenido y asignaciones.
- El nuevo rol `trainer` solo podrá consultar y gestionar campers o cohortes asignadas.
- El área educativa aprobará preguntas y rúbricas mediante un permiso específico; esta función no debe depender de acceso técnico a la base de datos.
- El equipo de empleabilidad tendrá acceso de solo lectura al estado necesario para postulación.
- El camper solo podrá consultar su información y sus propias entregas.
- Toda consulta de documentos privados deberá requerir autorización y quedar protegida por sesión.

### 5.3 Flujo editorial de preguntas

```text
Resultado de aprendizaje aprobado
        │
        ▼
Generación de borradores por IA
        │
        ▼
Validación técnica de estructura
        │
        ▼
Revisión y edición del área educativa
        │
        ▼
Publicación de versión aprobada
        │
        ▼
Uso aleatorio en intentos
        │
        ▼
Análisis de dificultad y discriminación
        │
        └── Retiro o nueva versión cuando corresponda
```

La IA no publicará preguntas directamente. Cada pregunta deberá incluir competencia, lección, dificultad esperada, respuesta correcta, explicación, distractores y versión. Los cambios posteriores no alterarán retroactivamente los intentos ya realizados.

---

## 6. Indicadores y paneles de decisión

### 6.1 Indicador principal

El KPI principal será **preparación demostrada**:

```text
Preparación demostrada (%) =
  campers con estado APTO
  ────────────────────────── × 100
  campers activos asignados a la ruta
```

El denominador no deberá limitarse a quienes iniciaron voluntariamente, porque eso ocultaría a los campers que no han comenzado. El indicador se segmentará por cohorte, trainer, sede o programa cuando esos datos estén disponibles.

No se fijará una meta porcentual sin línea base. El primer ciclo institucional establecerá la distribución real y permitirá acordar objetivos alcanzables con el área educativa.

### 6.2 Indicadores de aprendizaje y operación

| Indicador | Uso |
| --- | --- |
| Activación de la ruta | Identificar campers asignados que aún no han iniciado |
| Progreso por módulo y competencia | Detectar acumulación y contenidos con mayor dificultad |
| Aprobación en primer intento | Señalar comprensión inicial y calidad de la instrucción |
| Recuperación después del refuerzo | Medir si la intervención corrige la brecha |
| Intentos promedio por pregunta | Detectar preguntas ambiguas o competencias críticas |
| Evidencias aceptadas en primera revisión | Medir claridad de las instrucciones y preparación aplicada |
| Tiempo de espera de revisión | Controlar la capacidad operativa de trainers |
| Casos pendientes por trainer | Equilibrar carga y anticipar cuellos de botella |
| Resultados de mock interview por criterio | Diseñar refuerzos focalizados |
| Uso y costo de IA | Controlar presupuesto y detectar comportamientos anómalos |
| Excepciones o cambios manuales de estado | Auditar decisiones sensibles |

### 6.3 Indicadores posteriores de empleabilidad

Cuando exista integración con el proceso laboral, podrán medirse:

- campers aptos postulados;
- conversión de postulación a entrevista;
- avance entre etapas del proceso;
- ofertas recibidas;
- contrataciones;
- tiempo entre habilitación y primera entrevista o contratación;
- causas de rechazo reportadas por empresas.

Estos indicadores son resultados compartidos por la preparación técnica, el perfil del camper, la disponibilidad de vacantes, las condiciones de mercado y el proceso de selección. No deben presentarse como efectos exclusivos de SoftStack sin un diseño de evaluación que permita sostener esa atribución.

### 6.4 Vistas requeridas

**Dirección y área educativa**

- preparación demostrada total y por cohorte;
- mapa de calor por competencia;
- embudo desde asignación hasta habilitación;
- evolución de intentos y refuerzos;
- carga de trainers;
- costos y disponibilidad del componente de IA.

**Trainer**

- campers asignados y estado actual;
- revisiones pendientes;
- brechas repetidas;
- historial de feedback y refuerzos;
- agenda o registro de mock interviews;
- alertas de inactividad no bloqueantes.

**Camper**

- requisitos completados y pendientes;
- explicación del estado `APTO` / `NO APTO`;
- resultados por competencia;
- feedback accionable;
- acceso a refuerzos y nuevos intentos;
- historial de evidencias y revisiones.

---

## 7. Impacto técnico previsto

Esta sección identifica el alcance para toma de decisiones. Antes de implementar cada vertical deberán crearse PRDs técnicos y contratos detallados en el repositorio que sea propietario del cambio.

### 7.1 Backend

El backend deberá evolucionar desde progreso binario por lección hacia dominios explícitos:

- **Cohortes y asignaciones:** cohortes, membresías, trainer responsable y estado del vínculo.
- **Competencias y resultados:** objetivos vinculados a lecciones, módulos, evidencias y rúbricas.
- **Evaluaciones:** definiciones, bancos de preguntas, versiones, estados editoriales y selección aleatoria.
- **Intentos:** respuestas, puntaje determinista, preguntas usadas, refuerzo requerido y marca temporal.
- **Evidencias:** entregas, versiones, documentos privados, feedback automatizado y revisión humana.
- **Entrevistas simuladas:** sesiones, rúbricas, criterios, observaciones y resultado.
- **Habilitación:** snapshot de requisitos, estado oficial, versión de reglas y eventos de cambio.
- **Auditoría:** actor, acción, recurso, cambio, motivo y fecha para decisiones sensibles.
- **Uso de IA:** proveedor, modelo, propósito, tokens, costo estimado, estado y versión de prompt, sin conservar identificadores innecesarios.

Los índices deberán responder a consultas por camper, cohorte, trainer, estado, competencia, fecha de revisión y versión. Los intentos y decisiones académicas no deberán sobrescribirse; las correcciones se registrarán como nuevas versiones o eventos.

### 7.2 Frontend

El frontend deberá incorporar:

- experiencia de ruta con requisitos y estado de preparación;
- microquizzes accesibles con feedback y refuerzo;
- entrega y versionado de evidencias;
- bandeja de trabajo para trainers;
- formularios de rúbrica y mock interview;
- panel administrativo de cohortes, currículo y preguntas;
- analítica con filtros y explicaciones, no solo gráficos;
- exportación de resultados;
- estados de carga, error, indisponibilidad de IA y reintento seguro;
- navegación y permisos diferenciados para camper, trainer y admin.

Se conservará el patrón actual de BFF en Next.js y cookies HttpOnly. Las validaciones de autorización seguirán siendo responsabilidad del backend; ocultar una opción en la interfaz no sustituye el control de permisos.

### 7.3 Almacenamiento privado

Los documentos de campers no deberán reutilizar el Blob Store público de medios de contenido. Se requiere un espacio privado con:

- rutas no predecibles;
- acceso únicamente a través de endpoints autenticados o URLs firmadas de corta duración;
- validación de extensión, MIME, firma y tamaño;
- análisis de malware antes de habilitar descarga cuando la infraestructura lo permita;
- cifrado en tránsito y controles del proveedor en reposo;
- retención y eliminación alineadas con la finalidad educativa;
- separación entre documentos estudiantiles, fotos de perfil y medios públicos del CMS.

### 7.4 Interfaces funcionales futuras

Los nombres definitivos se fijarán en los PRDs técnicos, pero la plataforma deberá ofrecer contratos equivalentes a:

| Consumidor | Capacidad mínima |
| --- | --- |
| Camper | Consultar ruta y estado; iniciar y entregar intentos; consultar feedback; cargar y versionar evidencias |
| Trainer | Consultar cohortes asignadas; revisar evidencias; registrar refuerzos y mock interviews |
| Admin / Educación | Gestionar cohortes, asignaciones, competencias, evaluaciones, preguntas, rúbricas y publicación |
| Dirección | Consultar métricas agregadas y exportar reportes |
| Empleabilidad | Consultar `APTO` / `NO APTO`, fecha, versión de reglas y requisitos pendientes permitidos |

La integración con empleabilidad deberá admitir:

- consulta por identificador institucional;
- exportación CSV controlada como respaldo operativo;
- filtros por cohorte y estado;
- fecha y versión del cálculo;
- respuesta mínima, evitando exponer notas o documentos cuando no sean necesarios;
- autenticación de servicio, límites de consumo y registro de accesos.

---

## 8. Uso de inteligencia artificial

### 8.1 Alcance aprobado

DeepSeek será el proveedor inicial, encapsulado detrás de un adaptador para permitir cambio de modelo o proveedor sin modificar las reglas académicas. La integración deberá soportar, como mínimo:

- generación estructurada de borradores de preguntas;
- generación de explicaciones y feedback formativo;
- límites de tokens, concurrencia y presupuesto;
- validación de respuestas contra esquemas JSON;
- reintentos controlados y circuit breaker;
- métricas por propósito y versión de prompt;
- fallback a contenido previamente aprobado.

El sistema de evaluación no dependerá de una llamada en tiempo real para funcionar. Las preguntas se generarán de manera editorial, se revisarán y se almacenarán antes de ser usadas. Si el proveedor no está disponible, los campers deberán poder continuar con el banco aprobado.

### 8.2 Límites de autoridad

La IA podrá:

- proponer preguntas, distractores, explicaciones y variantes;
- sugerir mejoras de redacción;
- ofrecer feedback formativo sobre texto anonimizado;
- clasificar posibles áreas de refuerzo para revisión del trainer.

La IA no podrá:

- publicar preguntas sin aprobación educativa;
- decidir por sí sola si una evidencia está aprobada;
- modificar el estado oficial de empleabilidad;
- resolver apelaciones;
- asignar sanciones;
- usar datos de un camper para entrenar funcionalidades internas sin base legal y autorización;
- recibir nombres, correos, teléfonos, direcciones, documentos de identidad, CV completos o identificadores directos.

### 8.3 Anonimización y minimización

Antes de enviar texto estudiantil a un proveedor externo, SoftStack deberá:

1. extraer únicamente el fragmento necesario;
2. remover nombre, correo, teléfono, enlaces personales y otros identificadores directos;
3. reemplazar entidades por etiquetas neutras cuando el contexto lo requiera;
4. bloquear el envío si la anonimización no alcanza un nivel confiable;
5. informar al usuario que recibirá feedback asistido por IA;
6. registrar propósito, modelo, versión y resultado técnico sin almacenar datos adicionales innecesarios.

Un CV completo no deberá enviarse a DeepSeek. El sistema podrá extraer y anonimizar una sección concreta —por ejemplo, la descripción de un logro— para producir feedback, conservando el documento original exclusivamente en el almacenamiento privado de SoftStack.

### 8.4 Riesgo de privacidad y menores

La política pública de DeepSeek indica que los datos personales pueden procesarse y almacenarse en la República Popular China, contempla usos para mejora de sus servicios y señala que sus servicios no están dirigidos a menores. Campuslands admite participantes desde los 17 años y su propia política reconoce el tratamiento de datos de menores en contextos educativos.

Por esta razón, la habilitación del feedback externo deberá quedar condicionada a:

- revisión jurídica de la relación responsable–encargado;
- análisis de transferencias o transmisiones internacionales aplicables;
- actualización de avisos y política de tratamiento;
- consentimiento previo, expreso e informado cuando corresponda;
- autorización del representante legal y garantías reforzadas para menores cuando sean exigibles;
- procedimiento de acceso, corrección, supresión y revocación;
- evaluación de retención, seguridad, entrenamiento y subencargados del proveedor;
- alternativa sin IA para los casos en que no pueda utilizarse legalmente.

La Superintendencia de Industria y Comercio ha reiterado que el tratamiento de datos de niños, niñas y adolescentes exige interés superior, respeto de derechos fundamentales, derecho a ser escuchados y las autorizaciones aplicables. La aprobación del proyecto tecnológico no reemplaza esta validación.

---

## 9. Modelo operativo y capacidad

### 9.1 Dimensionamiento inicial

Para una población máxima de 500 campers y cinco evidencias por persona:

| Actividad | Supuesto | Carga por ciclo completo |
| --- | --- | ---: |
| Revisión final de evidencias | 2.500 entregas × 6–10 minutos | 250–417 horas |
| Mock interview | 500 entrevistas × 20–30 minutos | 167–250 horas |
| Carga base total | Sin contar refuerzos o segundas revisiones | 417–667 horas |

Distribuida entre 3 y 5 trainers, la carga base equivale aproximadamente a 83–222 horas por trainer durante un ciclo completo, según número de trainers y profundidad de cada revisión. Esto no representa horas mensuales: dependerá del ritmo real de avance. La ausencia de fechas puede concentrar la demanda, por lo que la bandeja de revisión deberá permitir balancear asignaciones y visualizar capacidad.

El feedback automatizado busca reducir retrabajo antes de la revisión humana, pero no debe utilizarse para justificar una dotación insuficiente. Después del primer ciclo se deberán recalcular tiempos reales por tipo de evidencia y ajustar el número de reviewers o el diseño de las rúbricas.

### 9.2 Operación recomendada

- Cada cohorte tendrá uno o más trainers responsables.
- Las evidencias ingresarán a una cola con antigüedad, prioridad y estado visibles.
- Un trainer no deberá revisar campers fuera de sus asignaciones salvo reasignación explícita.
- Las revisiones deberán usar rúbricas comunes y comentarios accionables.
- Los desacuerdos o apelaciones deberán ser evaluados por una persona distinta del revisor original o por un responsable educativo.
- Los cambios de currículo y reglas deberán publicarse por versión y fecha efectiva.
- Los campers que ya iniciaron una versión no deberán cambiar de reglas silenciosamente.
- Los recordatorios por inactividad serán informativos, no fechas límite encubiertas.

---

## 10. Presupuesto operativo mensual de referencia

### 10.1 Alcance del cálculo

El presupuesto cubre costos operativos incrementales para hasta 500 campers. **No incluye desarrollo, salarios, tiempo de trainers, diseño curricular, revisión jurídica, impuestos, retenciones ni costos base que Campuslands ya pague por Vercel, correo o MongoDB.**

Los valores son referencias para aprobación de un techo inicial, no cotizaciones. Los proveedores pueden cambiar precios y las regiones o planes contratados alteran el total.

### 10.2 Supuestos de consumo

- hasta 2.500 interacciones de feedback anonimizado al mes en un escenario de actividad alta;
- promedio de 4.000 tokens de entrada y 800 tokens de salida por interacción;
- generación editorial de bancos de preguntas en lotes, no en cada intento;
- almacenamiento privado de documentos con control de versiones;
- MongoDB administrado y monitoreo básico de errores, costos y disponibilidad;
- límites de gasto y alertas configurados desde el primer despliegue.

### 10.3 Rango mensual

| Componente | Escenario contenido | Escenario institucional | Supuesto principal |
| --- | ---: | ---: | --- |
| DeepSeek | USD 10–30 | USD 25–75 | Modelo económico, límites por propósito y margen para reintentos |
| MongoDB Atlas | USD 8–30 | USD 60–150 | Flex para validación; dedicado o capacidad equivalente para producción |
| Vercel Blob privado | USD 1–10 | USD 5–25 | Almacenamiento, operaciones y transferencia de documentos privados |
| Monitoreo y correo | USD 10–40 | USD 30–100 | Depende de proveedores y planes existentes |
| Contingencia operativa | USD 10–25 | USD 30–100 | Cambios de consumo, región, transferencia, impuestos o incidentes |
| **Total estimado** | **USD 39–135/mes** | **USD 150–450/mes** | No incluye trabajo humano ni planes base ya contratados |

Para una operación institucional con hasta 500 campers se recomienda solicitar autorización para un **techo incremental inicial de USD 450 mensuales**, sujeto a alertas de consumo y revisión después del primer ciclo.

La conversión presupuestal deberá realizarse al momento de aprobación:

```text
Presupuesto mensual en COP =
  total mensual en USD × TRM vigente en la fecha de pago
  + impuestos, retenciones y costos bancarios aplicables
```

### 10.4 Control financiero

- Establecer límites mensuales por proveedor.
- Registrar tokens, llamadas y costo estimado por funcionalidad, nunca solo por usuario.
- Evitar llamadas de IA cuando exista una respuesta aprobada reutilizable.
- Suspender feedback automatizado antes de afectar evaluaciones o acceso a contenido si se alcanza el límite.
- Revisar costo por camper activo y por evidencia procesada.
- Comparar periódicamente calidad, privacidad y precio de proveedores alternativos.
- Separar el presupuesto de infraestructura del costo de acompañamiento humano.

---

## 11. Hoja de ruta por capacidades

La dirección solicitó no comprometer un calendario antes de validar recursos. La implementación se organizará por capacidades y criterios de salida. Ninguna fase deberá considerarse terminada solo porque exista una interfaz; debe operar de extremo a extremo y quedar documentada en el repositorio responsable.

### Capacidad 1 — Gobierno académico y privacidad

**Entregables**

- propietario institucional del currículo;
- catálogo de competencias y resultados de aprendizaje;
- definición de evidencias y rúbricas;
- política de versiones;
- reglas de habilitación y apelación;
- evaluación jurídica de datos, menores e IA;
- política de retención y eliminación.

**Criterio de salida:** Educación, Empleabilidad, Tecnología y responsable de datos aprueban reglas y responsabilidades.

### Capacidad 2 — Cohortes, trainers y asignaciones

**Entregables**

- rol `trainer`;
- cohortes y membresías;
- asignación posterior al autorregistro;
- permisos y filtros por ámbito;
- panel básico de seguimiento;
- auditoría de cambios de asignación.

**Criterio de salida:** un admin puede organizar la población y cada trainer solo accede a campers autorizados.

### Capacidad 3 — Evaluaciones y refuerzos

**Entregables**

- banco versionado de preguntas;
- flujo editorial con aprobación educativa;
- microquiz aleatorio;
- calificación determinista;
- historial de intentos;
- refuerzos y reintentos;
- analítica básica de dificultad.

**Criterio de salida:** una lección solo queda aprobada con el umbral requerido y el historial completo permanece auditable.

### Capacidad 4 — Evidencias y mock interviews

**Entregables**

- almacenamiento privado;
- entregas versionadas;
- rúbricas y revisión humana;
- feedback anonimizado asistido por IA, si recibe aval jurídico;
- bandeja de trainers;
- registro de mock interview y refuerzo.

**Criterio de salida:** ningún documento es público y toda aprobación puede explicarse mediante una rúbrica y un actor responsable.

### Capacidad 5 — Analítica y habilitación

**Entregables**

- motor de reglas `APTO` / `NO APTO`;
- explicación de requisitos pendientes;
- dashboards por audiencia;
- preparación demostrada y métricas de operación;
- historial de cambios y excepciones;
- control de costos de IA.

**Criterio de salida:** frontend, reportes y cálculo backend producen el mismo estado a partir de reglas versionadas.

### Capacidad 6 — Integración, endurecimiento y despliegue institucional

**Entregables**

- consulta y exportación para empleabilidad;
- contrato de integración y autenticación de servicio;
- pruebas de seguridad, permisos, carga y recuperación;
- observabilidad y alertas;
- documentación operativa;
- capacitación de administradores y trainers;
- procedimiento de soporte e incidentes.

**Criterio de salida:** ningún camper `NO APTO` puede ser presentado por el flujo oficial sin una excepción autorizada y registrada.

---

## 12. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación propuesta |
| --- | --- | --- |
| Ruta libre sin fechas | Acumulación de actividad y revisiones al final | Recordatorios, visualización de preparación, cola por antigüedad y monitoreo de capacidad |
| Cuello de botella de trainers | Retraso en habilitación | Feedback previo, rúbricas breves, balanceo de cargas y medición de tiempo real |
| Preguntas ambiguas o incorrectas | Evaluaciones injustas | Aprobación educativa, versionado, análisis de intentos y retiro controlado |
| Memorización del banco | Nota sin dominio real | Bancos amplios, casos situacionales, variantes aprobadas y evidencias aplicadas |
| Alucinaciones o sesgos de IA | Feedback dañino o inconsistente | Esquemas, prompts versionados, revisión humana y prohibición de decisión automática |
| Exposición de datos personales | Daño legal y reputacional | Almacenamiento privado, anonimización, mínimo privilegio y revisión jurídica |
| Tratamiento inadecuado de menores | Incumplimiento reforzado | Consentimientos, representante legal cuando aplique y alternativa sin IA externa |
| Dependencia de DeepSeek | Interrupción o cambio de precio | Adaptador multi-proveedor, banco local aprobado y límites de gasto |
| Manipulación manual del estado | Pérdida de confianza | Motor de reglas, excepciones justificadas y auditoría inmutable |
| Currículo desactualizado | Preparación desconectada del mercado | Revisión periódica por Educación y Empleabilidad con nuevas versiones |
| Confundir formación con garantía laboral | Expectativas y medición incorrectas | Comunicación clara y separación entre KPI educativo y resultados laborales |
| Duplicación documental entre repositorios | Versiones contradictorias | Propietario documental explícito y enlaces desde cada repositorio afectado |

---

## 13. Criterios de aceptación institucional

La implementación completa deberá considerarse aceptada cuando:

- el 100 % de los campers objetivo pueda ser asignado a una ruta y una cohorte;
- cada requisito de aprobación tenga una regla o rúbrica publicada;
- ningún camper obtenga estado `APTO` sin cumplir todos los requisitos vigentes;
- el camper pueda comprender qué le falta y cómo corregirlo;
- los intentos, revisiones, excepciones y cambios de estado sean auditables;
- los trainers solo accedan a su ámbito autorizado;
- los documentos estudiantiles permanezcan privados;
- no se envíen identificadores directos ni CV completos al proveedor de IA;
- una indisponibilidad de IA no impida presentar evaluaciones ya publicadas;
- los datos del panel, la exportación y la API de empleabilidad sean consistentes;
- existan pruebas de permisos, reglas, concurrencia, fallos de proveedor y recuperación;
- las políticas y manuales permitan operar la plataforma sin depender de esta conversación.

---

## 14. Decisiones solicitadas a dirección y al área educativa

Se solicita aprobar formalmente:

- [ ] La implementación institucional completa del modelo en SoftStack.
- [ ] La preparación demostrada como requisito previo a procesos oficiales de empleabilidad.
- [ ] El estado `APTO` / `NO APTO` como fuente oficial, exportable e integrable.
- [ ] La participación del área educativa como propietaria de currículo, rúbricas y bancos de preguntas.
- [ ] La asignación inicial de 3 a 5 trainers para hasta 500 campers.
- [ ] La revisión jurídica y de privacidad antes de activar feedback con IA externa.
- [ ] Un techo operativo incremental inicial de hasta USD 450 mensuales, sujeto a control de consumo.
- [ ] La creación de PRDs y documentación separada en backend y frontend para cada capacidad aprobada.
- [ ] La definición de una ubicación Git oficial para este documento transversal.
- [ ] La formalización del contrato de exportación o API con el proceso de empleabilidad.

La aprobación no implica que la IA pueda tomar decisiones laborales, que los cinco módulos actuales queden congelados ni que SoftStack garantice una contratación. Implica que Campuslands adopta un proceso común, medible y auditable para preparar y habilitar a sus campers antes de representarlos frente a una empresa.

---

## 15. Referencias

Fuentes consultadas el 4 de octubre de 2026:

1. [Campuslands — Campers y rutas de entrenamiento](https://www.campuslands.com/camper). Contexto institucional de formación técnica, inglés y habilidades adaptativas.
2. [Campuslands — Política de privacidad y tratamiento de datos](https://www.campuslands.com/privacidad). Tratamiento institucional de información y referencia expresa a menores de edad.
3. [Campuslands — Términos y condiciones](https://campuslands.com/terminos). Compromisos académicos, evaluaciones, proyectos y límites frente a resultados laborales.
4. [TripleTen — FAQ](https://tripleten.com/faq/). Referencia comparativa sobre aprendizaje práctico, proyectos, acompañamiento y estructura de avance. SoftStack adopta la práctica y el acompañamiento, pero no sus fechas límite.
5. [Institute of Education Sciences — Organizing Instruction and Study to Improve Student Learning](https://ies.ed.gov/ncee/wwc/PracticeGuide/1). Recomendación sobre recuperación activa mediante quizzes y feedback correctivo.
6. [DeepSeek — Responses API](https://api-docs.deepseek.com/api/create-response/). Capacidades de salida estructurada y uso de esquemas JSON.
7. [DeepSeek — Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/). Modelos y precios vigentes de referencia; los valores pueden cambiar.
8. [DeepSeek — Privacy Policy](https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html). Tratamiento, retención, ubicación y uso de datos personales.
9. [DeepSeek — Open Platform Terms of Service](https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html). Responsabilidades del operador de aplicaciones frente a usuarios finales.
10. [Superintendencia de Industria y Comercio — Tratamiento de datos de menores](https://sedeelectronica.sic.gov.co/publicaciones/boletin-juridico/concepto/tratamiento-excepcional-y-autorizacion-del-representante-legal-con-interes-superior). Estándar reforzado para niños, niñas y adolescentes.
11. [Vercel Blob — Usage and Pricing](https://vercel.com/docs/vercel-blob/usage-and-pricing). Costos de almacenamiento, operaciones y transferencia; la entrega privada puede sumar costos de funciones y transferencia.
12. [MongoDB Atlas — Pricing](https://www.mongodb.com/pricing). Rangos de referencia para clusters Flex y dedicados.

---

## 16. Próximo paso después de la aprobación

Nombrar un responsable del área educativa, un responsable técnico y un responsable de empleabilidad para convertir la **Capacidad 1 — Gobierno académico y privacidad** en un PRD operativo aprobado. Solo después deberán iniciarse cambios de código. Esto evita construir evaluaciones, reglas o integraciones antes de que Campuslands haya definido formalmente qué significa estar preparado para representar a la institución frente a una empresa.
