# PRD — Fixture demo y catálogo publicado en vivo

## Problema y objetivo

El catálogo inicial solo permitía validar contenido. Las pantallas de estudiante,
trainer y administración quedaban vacías porque no existían cuentas, evaluaciones,
progreso ni eventos históricos reproducibles. Además, la landing mostraba módulos y
porcentajes ilustrativos que no correspondían con MongoDB.

El objetivo es disponer de un fixture local realista, repetible y trazable, y hacer
que la landing lea el catálogo publicado actual.

## Alcance

- Enriquecer los cinco módulos y trece lecciones con `instructional_plan`.
- Crear `scripts.seed_demo` separado de `scripts.seed_content`.
- Sembrar seis cuentas demo: administrador, trainer, tres estudiantes activos y un estudiante pendiente.
- Sembrar perfiles académicos, asignaciones, evaluaciones, preguntas aprobadas, intentos, progreso, estados, un reinicio y configuración.
- Mantener documentos multimedia, tokens de sesión, tokens de email y revisiones fuera del fixture.
- Identificar todos los documentos administrados con `softstack.demo.v1` y actualizar únicamente esos documentos.

## Reglas y seguridad

- El comando exige `--confirm` y una contraseña de al menos ocho caracteres mediante `SEED_DEMO_PASSWORD` o `--password`.
- El seed no elimina colecciones ni usuarios ajenos al namespace demo.
- Las cuentas usan el dominio reservado `softstack.test`, están pensadas para desarrollo local y no deben crearse en producción.
- Las preguntas son contenido curado del fixture, no respuestas generadas por DeepSeek.
- Los intentos conservan snapshots de preguntas y respuestas para que la analítica sea coherente con el contrato actual.

## Datos y relaciones

Se crean 18 evaluaciones —una por lección y una por módulo— con preguntas aprobadas
en español. Tres estudiantes recorren trayectorias distintas; algunos tienen
intentos fallidos antes de aprobar y uno conserva un reinicio histórico. El trainer
solo recibe asignaciones de los tres estudiantes activos.

## Validación

La suite prueba los planes instruccionales, cantidades, roles y repetición del seed
sin duplicados. La aceptación manual requiere levantar MongoDB, ejecutar el comando
con una contraseña local y recorrer landing, dashboard, quizzes, usuarios y
analítica con las cuentas documentadas en el README.
