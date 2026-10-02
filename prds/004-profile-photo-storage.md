# PRD 004: Fotos de perfil privadas

## Problema y objetivo

Las cuentas de SoftStack actualmente muestran únicamente la inicial del nombre. La plataforma necesita permitir que cada usuario gestione una foto de perfil sin exponer credenciales de almacenamiento ni publicar accidentalmente datos personales.

El objetivo es almacenar fotos en un Blob Store privado de Vercel y mantener en MongoDB solo los metadatos necesarios para localizar y entregar la foto al propietario autenticado.

## Alcance

- Subir una foto de perfil.
- Reemplazar la foto existente.
- Eliminar la foto.
- Servir la foto únicamente al usuario autenticado que la posee.
- Mostrar la foto o la inicial en el dashboard.

Fuera de alcance: perfiles públicos, consulta de fotos por administradores, recorte automático, transformación de imágenes y cargas mayores a 3 MB.

## Actores

- Usuario autenticado: gestiona únicamente su propia foto.
- Backend FastAPI: valida, almacena, elimina y entrega la foto.
- Frontend Next.js/BFF: presenta el flujo de usuario y reenvía cookies de sesión.
- Vercel Blob privado: almacena el binario.

## Contrato HTTP

### `POST /auth/me/profile-photo`

Recibe `multipart/form-data` con el campo `file`. Acepta JPEG, PNG y WebP de hasta 3 MB. Devuelve `UserResponse` con `has_profile_photo=true`.

### `GET /auth/me/profile-photo`

Requiere la sesión del usuario. Devuelve el binario mediante streaming, con el tipo MIME persistido y cabeceras `Cache-Control: private, no-store` y `X-Content-Type-Options: nosniff`. Devuelve `404` si el usuario no tiene foto.

### `DELETE /auth/me/profile-photo`

Elimina la referencia de MongoDB y solicita la eliminación del blob anterior. Devuelve `UserResponse` con `has_profile_photo=false`.

## Persistencia

El documento `users` guarda un campo opcional `profile_photo`:

```json
{
  "pathname": "profile-photos/<user-id>/<uuid>.png",
  "content_type": "image/png",
  "size": 123456,
  "etag": "<etag>",
  "uploaded_at": "<datetime>"
}
```

Las respuestas públicas del usuario exponen únicamente `has_profile_photo`; nunca exponen el pathname, el token ni una URL directa reutilizable.

## Seguridad y validaciones

- El Blob Store debe ser privado.
- `BLOB_READ_WRITE_TOKEN` permanece únicamente en variables de entorno del backend.
- Se comprueba MIME y firma binaria del contenido.
- Se rechazan SVG, GIF, HEIC, archivos vacíos y cargas mayores a 3 MB.
- La ruta de lectura no acepta pathnames enviados por el cliente.
- Los pathnames se generan con el identificador del usuario y un UUID.
- Los errores del proveedor no revelan credenciales ni detalles internos.

## Consistencia y errores

Al reemplazar se sube primero el nuevo blob, después se actualiza MongoDB y finalmente se elimina el anterior. Si falla la actualización, se intenta eliminar el nuevo blob como compensación. Si una eliminación posterior falla, se conserva la referencia nueva o se limpia la referencia de MongoDB y se registra el huérfano para limpieza operativa posterior.

Los usuarios existentes sin `profile_photo` continúan siendo válidos y muestran la inicial.

## Riesgos y límites conocidos

- Las cargas server-side están limitadas a 3 MB para mantenerse por debajo del límite de request body de Vercel Functions.
- La eliminación del blob es una operación externa; puede quedar un objeto huérfano si Vercel está temporalmente indisponible.
- El token read-write debe rotarse si se expone fuera del gestor de secretos.
