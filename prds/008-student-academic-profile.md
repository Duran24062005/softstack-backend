# PRD 008 — Perfil académico de estudiantes

## Problema y objetivo

El registro público crea estudiantes, pero actualmente solo solicita nombre,
correo y contraseña. La plataforma necesita conservar el año de inicio, el
grupo y la sede donde termina su formación, y enlaces opcionales a LinkedIn y
GitHub.

El objetivo es que el registro público capture esa información sin permitir que
el cliente elija un rol y que los administradores puedan corregirla después.

## Alcance

- Mantener `user` como rol interno de estudiante.
- Exigir al registro público un año de inicio, un grupo y una sede finales.
- No modelar una trayectoria ni permitir agregar grupos anteriores: el perfil
  representa la formación que la persona finaliza en un grupo y una sede.
- Validar LinkedIn y GitHub como URLs HTTP(S) de sus dominios respectivos.
- Guardar el perfil académico dentro del documento `users`, separado del
  `UserResponse` público.
- Exponer lectura y actualización para el estudiante autenticado.
- Exponer lectura y actualización para administradores sobre estudiantes.
- Mantener la invitación y promoción administrativa de trainers sin exigirles
  datos académicos de estudiante.

## Contratos

El registro acepta `academic_profile` además de las credenciales:

```json
{
  "start_year": 2024,
  "group_name": "Grupo A",
  "campus_name": "Bucaramanga",
  "linkedin_url": null,
  "github_url": "https://github.com/usuario"
}
```

Los endpoints de perfil son:

- `GET /auth/me/academic-profile`
- `PUT /auth/me/academic-profile`
- `GET /admin/students/{student_id}/academic-profile`
- `PUT /admin/students/{student_id}/academic-profile`

El perfil académico no se incluye en `UserResponse` para mantener separado el
contrato de identidad del contrato de información académica.

## Reglas y permisos

- El registro público no recibe un rol y crea cuentas `user`, salvo la
  excepción de bootstrap ya existente para emails incluidos en `ADMIN_EMAILS`.
- El año no puede estar en el futuro.
- Grupo y sede son texto declarado por el estudiante; todavía no existen
  catálogos administrados.
- El estudiante puede editar su propio perfil.
- Solo `admin` puede editar el perfil de otro estudiante.
- Los perfiles de trainers y administradores no usan este contrato.
- La aprobación, verificación de email y estados de cuenta permanecen sin
  cambios.

## Compatibilidad y riesgos

Los usuarios existentes sin `academic_profile` siguen siendo válidos y reciben
`null` al consultar su perfil. Podrán completarlo desde el dashboard. Los
documentos de la primera versión que todavía contienen `memberships` se
normalizan al leerlos: se toma la membresía marcada como actual o, si no
existe, la primera. El siguiente guardado persiste la forma simple. No se
eliminan datos antiguos automáticamente.

En una fase posterior, los textos libres podrán migrarse a catálogos de
cohortes y sedes sin cambiar el rol interno.

## Validación

La cobertura debe incluir schemas, registro público, invitación de trainers,
lectura y actualización propia, permisos administrativos, roles no permitidos,
URLs inválidas, años futuros, rechazo de la forma histórica en nuevas
peticiones y usuarios existentes con el perfil antiguo.
