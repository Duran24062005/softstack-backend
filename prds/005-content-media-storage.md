# PRD 005: Medios multimedia en contenido

## Problema y objetivo

Las lecciones se almacenan como documentos JSON de Tiptap, pero el editor actual solo acepta imágenes por URL y no ofrece una forma controlada de cargar imágenes o videos. Los módulos tampoco pueden conservar una portada multimedia.

El objetivo es que todo medio administrado desde el contenido se almacene en un Blob Store público de Vercel y que MongoDB conserve la URL, el pathname y los metadatos necesarios para renderizar y limpiar el archivo. Las fotos de perfil permanecen en el Blob Store privado existente.

## Alcance

- Cargar imágenes y videos desde el editor de lecciones.
- Insertar medios en cualquier nivel del documento Tiptap.
- Importar URLs externas a Blob antes de persistirlas.
- Añadir una portada multimedia opcional a cada módulo.
- Limpiar blobs reemplazados, eliminados o huérfanos.
- Mantener compatibilidad con lecciones y módulos que no tienen medios.

Fuera de alcance: transformación de imágenes, generación de thumbnails, edición de video, almacenamiento privado de contenido educativo y conversión de formatos.

## Actores

- Administrador: carga, importa, reemplaza y elimina medios desde el CMS.
- Estudiante: consume las URLs públicas al visualizar contenido publicado.
- Frontend Next.js: autentica el upload client-side y presenta el editor.
- Backend FastAPI: valida medios, persiste contratos en MongoDB y coordina limpieza.
- Vercel Blob público: entrega imágenes y videos de contenido.

## Flujo

```text
Administrador
    │ cookie de sesión
    ▼
Next.js Route Handler /api/content-media/upload
    │ token limitado para carga cliente
    ▼
Vercel Blob público
    │ URL + pathname + metadatos
    ▼
Editor Tiptap / ModuleForm
    │ JSON con attrs.src o cover_media
    ▼
FastAPI admin content endpoints
    │ valida URL, MIME, pathname y referencias
    ▼
MongoDB modules / lessons
    │
    ▼
Estudiante → URL pública de Blob
```

## Contrato de medios

La carga devuelve:

```json
{
  "url": "https://...public.blob.vercel-storage.com/...",
  "pathname": "content-media/...",
  "content_type": "image/png",
  "size": 123456
}
```

Los nodos `image` y `video` guardan la URL en `attrs.src`. Cada lección mantiene además `media_assets`, derivado por el backend, para localizar referencias retiradas. Los módulos guardan `cover_media` y `media_assets`.

## Validaciones

- Solo administradores pueden generar tokens, importar URLs o eliminar cargas.
- Imágenes permitidas: JPEG, PNG, WebP y AVIF; máximo predeterminado de 10 MB.
- Videos permitidos: MP4, WebM y MOV; máximo predeterminado de 100 MB.
- El servidor valida MIME, tamaño, firma cuando es posible y pertenencia al Blob Store público configurado.
- `CONTENT_BLOB_PUBLIC_HOST` es obligatorio para validar referencias persistidas; no se acepta como sustituto cualquier otro host público de Vercel Blob.
- Se rechazan URLs `data:`, `blob:`, hosts externos no importados, localhost, redes privadas, link-local y destinos con credenciales.
- Las importaciones externas aplican timeout, límite de bytes y validación de cada redirección.
- El token read-write nunca se expone al navegador.

## Persistencia y consistencia

MongoDB se actualiza después de que el medio exista en Blob. Tras una actualización exitosa se eliminan referencias retiradas si ya no aparecen en otro documento. Si MongoDB falla, se intenta eliminar cualquier blob nuevo. Los errores de limpieza se registran y una tarea diaria elimina objetos de `content-media/` sin referencia y con más de 24 horas.

La operación entre MongoDB y Blob no es transaccional. El diseño prioriza no dejar URLs persistidas sin objeto y permite que un fallo temporal de eliminación sea recuperado por la tarea de limpieza.

## Seguridad y privacidad

El store de contenido es público por diseño: cualquier persona que posea la URL puede leer el archivo. El store privado de fotos de perfil y su token permanecen separados. El endpoint de importación protege contra SSRF y nunca sigue una redirección hacia una dirección no permitida.

## Migración y compatibilidad

Los documentos sin medios continúan válidos. Se incluye una migración opcional para importar medios externos existentes y convertirlos al contrato Blob antes de activar la validación estricta para esos documentos.

## Riesgos y límites conocidos

- Un administrador puede abandonar una pantalla después de cargar un blob; la tarea diaria lo elimina tras el periodo de retención.
- Los videos públicos generan coste de transferencia según el uso.
- El navegador no puede garantizar la firma binaria antes de la carga directa; el backend limita MIME, tamaño, pathname y el flujo de importación server-side valida el contenido recibido.
