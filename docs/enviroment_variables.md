# Variables de entorno de SoftStack

Este documento describe las variables de entorno que forman parte de la configuración de SoftStack. El contrato se basa en el código actual del backend FastAPI, el proxy BFF del frontend Next.js, `.env.example` y `docker-compose.yml`.

El archivo se llama `enviroment_variables.md` para conservar el nombre solicitado.

## Reglas generales

- Los archivos `.env` son locales y están ignorados por Git. No deben subirse al repositorio.
- `.env.example` contiene nombres, valores seguros de ejemplo y valores por defecto; no contiene credenciales reales.
- En producción, las variables deben configurarse en el proveedor de despliegue, por ejemplo Vercel.
- Las variables definidas por el entorno de ejecución tienen prioridad sobre los valores de `.env`.
- No compartas valores reales de `MONGODB_URI` ni `JWT_SECRET_KEY` en tickets, commits, capturas o logs.
- Los nombres son sensibles a mayúsculas y minúsculas. Usa exactamente los nombres documentados aquí.

## Backend

El backend carga estas variables desde `softstack-backend/.env` mediante `python-dotenv`.

### Aplicación y servidor

| Variable | Para qué sirve | Valor por defecto | Notas |
| --- | --- | --- | --- |
| `APP_NAME` | Nombre lógico de la aplicación usado en la configuración de FastAPI. | `SoftStack` | Es opcional y actualmente no aparece en `.env.example`. |
| `APP_VERSION` | Versión lógica expuesta por la configuración de la API. | `1.0.0` | Es opcional y actualmente no aparece en `.env.example`. |
| `HOST` | Interfaz de red donde escucha Uvicorn. | `0.0.0.0` | `0.0.0.0` permite conexiones desde Docker y plataformas cloud. En desarrollo local también es el valor usado por defecto. |
| `PORT` | Puerto HTTP del backend. | `8000` | Debe coincidir con el puerto publicado por Docker o con el puerto esperado por la plataforma. |
| `ENVIRONMENT` | Indica el entorno lógico, por ejemplo `development` o `production`. | No se consume actualmente en `config.py`. | Se conserva como variable descriptiva; cambiarla por sí sola no cambia el comportamiento de seguridad. |
| `LOG_LEVEL` | Nivel de logging esperado por la configuración del proyecto. | No se consume actualmente en `config.py`. | Puede documentar la intención del despliegue, pero no modifica los logs mientras no se conecte a una configuración de logging. |

### MongoDB

| Variable | Para qué sirve | Valor por defecto | Notas |
| --- | --- | --- | --- |
| `MONGODB_URI` | Cadena de conexión a MongoDB. | `mongodb://localhost:27017` | En local puede apuntar a MongoDB local o a `mongodb://mongodb:27017` dentro de Docker Compose. En producción debe ser una URI de MongoDB Atlas u otro servidor protegido. Contiene credenciales en muchos despliegues, por lo que es secreta. |
| `MONGODB_DATABASE` | Nombre de la base de datos usada por la aplicación. | `softstack` | El backend usa colecciones como `users`, `refresh_tokens`, `modules`, `lessons` y `progress` dentro de esta base. |
| `MONGODB_SERVER_SELECTION_TIMEOUT_MS` | Tiempo máximo para encontrar un servidor MongoDB disponible. | `2000` | Se interpreta como entero y está expresado en milisegundos. Auméntalo si Atlas tarda en responder, pero no lo uses para ocultar problemas de red. |
| `MONGODB_MAX_POOL_SIZE` | Máximo de conexiones simultáneas del pool de PyMongo. | `100` | Debe ajustarse al límite de conexiones del plan de MongoDB y al tráfico esperado. |
| `MONGODB_MIN_POOL_SIZE` | Mínimo de conexiones que PyMongo mantiene en el pool. | `0` | `0` evita mantener conexiones inactivas innecesarias. |

Valores típicos:

```env
# Desarrollo fuera de Docker
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=softstack

# API dentro de Docker Compose
MONGODB_URI=mongodb://mongodb:27017
MONGODB_DATABASE=softstack
```

### CORS

| Variable | Para qué sirve | Valor por defecto | Notas |
| --- | --- | --- | --- |
| `CORS_ORIGINS` | Lista separada por comas de orígenes autorizados para solicitudes cross-origin. | `http://localhost:3000,http://127.0.0.1:3000` | Debe contener orígenes completos, con esquema y host, pero sin rutas. El código elimina espacios y una `/` final. No uses `*` cuando se necesitan credenciales. |

Ejemplo local:

```env
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Ejemplo de producción con el frontend actual:

```env
CORS_ORIGINS=https://softstack-portal.vercel.app
```

El frontend usa un proxy BFF de Next.js, por lo que muchas solicitudes del navegador salen al mismo dominio del frontend. Aun así, `CORS_ORIGINS` debe mantenerse correcto para cualquier consumo directo de la API.

### Frontend y proveedor de correo

| Variable | Para qué sirve | Valor por defecto | Notas |
| --- | --- | --- | --- |
| `FRONTEND_URL` | URL pública usada para construir enlaces de confirmación de cuenta. | `http://localhost:3000` | No se debe construir el enlace a partir del host recibido en la petición. En producción debe ser la URL pública del portal. |
| `EMAIL_SERVICE_URL` | URL base del proveedor externo de correo transaccional. | `https://email-python-fast-api.vercel.app` | SoftStack llama a `POST /emails/transactional`, un endpoint público. No debe terminar en una ruta específica del endpoint. |
| `EMAIL_REQUEST_TIMEOUT_SECONDS` | Tiempo máximo de espera del cliente hacia el proveedor. | `10` segundos | Se interpreta como entero. El registro no se revierte si el proveedor no responde; el reenvío permite reintentar. |
| `EMAIL_VERIFICATION_EXPIRE_MINUTES` | Vigencia del enlace de confirmación. | `1440` minutos | Equivale a 24 horas. |
| `PASSWORD_RESET_CODE_EXPIRE_MINUTES` | Vigencia del código de recuperación. | `10` minutos | Debe ser corto porque el código tiene seis dígitos. |
| `PASSWORD_RESET_MAX_ATTEMPTS` | Intentos fallidos permitidos por código. | `5` | Al superar el límite, el código queda inutilizable. |

El endpoint transaccional público no requiere una clave compartida. `FRONTEND_URL` sigue siendo necesario para que SoftStack construya enlaces de verificación que apunten al portal correcto.

### JWT y sesiones

| Variable | Para qué sirve | Valor por defecto | Notas |
| --- | --- | --- | --- |
| `JWT_SECRET_KEY` | Clave secreta para firmar y validar access tokens y refresh tokens. | `change-me-in-production-use-a-32-byte-secret` en código | Es obligatoria en producción aunque el código tenga un fallback. Genera una clave aleatoria larga; nunca uses el fallback ni una clave corta compartida. Cambiarla invalida los tokens existentes. |
| `JWT_ALGORITHM` | Algoritmo usado para firmar los JWT. | `HS256` | Debe ser igual al generar y validar tokens. Si se cambia, todos los servicios que validen tokens deben usar el mismo algoritmo y clave. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración del access token. | `15` minutos | Se interpreta como entero. Un valor menor reduce la ventana de exposición, pero exige refresh más frecuente. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Duración máxima del refresh token. | `30` días | Se interpreta como entero. Los refresh tokens se almacenan en forma de hash y se rotan durante el refresh. |
| `PASSWORD_HASH_SCHEME` | Esquema de hash de contraseñas. | `argon2id` | Debe permanecer en `argon2id` salvo que también se actualice explícitamente la lógica de hashing y verificación. |
| `ADMIN_EMAILS` | Lista separada por comas de emails que reciben el rol `admin` durante el registro. | Lista vacía | Los emails se normalizan a minúsculas y se eliminan espacios. La variable no cambia el rol de usuarios ya existentes. No se acepta el rol desde el cliente. |

Ejemplo:

```env
ADMIN_EMAILS=admin@example.com,otra-persona@example.com
```

Si un usuario ya existe como `user`, agregar su email a `ADMIN_EMAILS` no lo promueve automáticamente. En ese caso hay que realizar una operación administrativa controlada sobre la base de datos o definir un flujo de promoción explícito.

### Evaluaciones e IA

| Variable | Para qué sirve | Valor por defecto | Notas |
| --- | --- | --- | --- |
| `AI_QUESTION_PROVIDER` | Proveedor activo para sugerir preguntas. | `deepseek` | Es un selector detrás de `QuestionProvider`; no se usa desde el navegador. |
| `DEEPSEEK_API_KEY` | Credencial server-side para generar sugerencias. | Vacía | Nunca la expongas con `NEXT_PUBLIC_` ni la guardes en Git. |
| `DEEPSEEK_BASE_URL` | URL base compatible con la API de DeepSeek. | `https://api.deepseek.com` | Permite sustituir el endpoint en pruebas o por otro proveedor compatible. |
| `DEEPSEEK_MODEL` | Modelo utilizado por el adaptador inicial. | `deepseek-flash` | Cambiable sin modificar el contrato de preguntas. |
| `DEEPSEEK_TIMEOUT_SECONDS` | Tiempo máximo de una sugerencia. | `30` | Un fallo no guarda preguntas parciales. |
| `ASSESSMENT_DEFAULT_PASSING_SCORE` | Umbral inicial de aprobación global. | `80` | El valor vigente se administra desde la API y MongoDB. |
| `ASSESSMENT_DEFAULT_QUESTION_COUNT` | Número inicial de preguntas por evaluación. | `5` | Debe estar entre 3 y 5. |

El proveedor recibe únicamente título, descripción y texto educativo anonimizado. Las preguntas se guardan como sugerencias y necesitan aprobación humana.

### Cookies de autenticación

| Variable | Para qué sirve | Valor por defecto | Notas |
| --- | --- | --- | --- |
| `COOKIE_SECURE` | Hace que el navegador solo envíe las cookies por HTTPS cuando es `true`. | `false` | Usa `false` en HTTP local. En producción con HTTPS debe ser `true`. Se aceptan `1`, `true`, `yes` y `on` sin importar mayúsculas. |
| `COOKIE_SAMESITE` | Política SameSite de las cookies. | `lax` | `lax` es adecuado para el flujo actual con proxy BFF. `none` requiere HTTPS y `COOKIE_SECURE=true`; úsalo solo si realmente se necesita un flujo cross-site. |
| `COOKIE_DOMAIN` | Dominio al que se limita la cookie. | Vacío (`None` en Python) | Debe quedar vacío con el BFF actual: el navegador recibe la cookie desde el dominio del frontend. No lo pongas como `softstack-backend.vercel.app` para compartirla con `softstack-portal.vercel.app`; son dominios distintos y el backend no puede asignar cookies al dominio del frontend. |
| `ACCESS_COOKIE_NAME` | Nombre de la cookie del access token. | `softstack_access` | Debe ser estable entre login, autenticación, refresh y logout. |
| `REFRESH_COOKIE_NAME` | Nombre de la cookie del refresh token. | `softstack_refresh` | Debe ser estable entre login, refresh y logout. |

Configuración local recomendada:

```env
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
COOKIE_DOMAIN=
ACCESS_COOKIE_NAME=softstack_access
REFRESH_COOKIE_NAME=softstack_refresh
```

Configuración recomendada en producción HTTPS con el BFF:

```env
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
COOKIE_DOMAIN=
```

El backend devuelve `Set-Cookie` y el Route Handler de Next.js reenvía esas cabeceras al navegador. Por eso, con esta arquitectura, las cookies deben pertenecer al dominio del frontend y normalmente no se configura `COOKIE_DOMAIN`.

### Vercel Blob

| Variable | Para qué sirve | Valor por defecto | Notas |
| --- | --- | --- | --- |
| `BLOB_STORE_ID` | Identificador del Blob Store conectado al backend. | Vacío | Debe corresponder al store privado de Vercel utilizado por SoftStack. |
| `BLOB_READ_WRITE_TOKEN` | Credencial server-side para cargar, leer y eliminar fotos privadas. | Vacía | Es secreta. No debe enviarse al navegador, registrarse en logs ni incluirse en commits. |

El backend exige ambas variables para habilitar el flujo de fotos de perfil. En Vercel deben configurarse como variables protegidas en los entornos que utilicen la feature. El store debe ser privado; el backend usa el SDK oficial de Python con `access="private"`.

La implementación limita las fotos a JPEG, PNG y WebP de máximo 3 MB.

### Vercel Blob público para contenido

El contenido educativo usa un store público separado del store privado de fotos de perfil. El modo público permite que el navegador del estudiante lea directamente las imágenes y videos mediante la URL persistida en MongoDB.

| Variable | Para qué sirve | Valor por defecto | Notas |
| --- | --- | --- | --- |
| `CONTENT_BLOB_STORE_ID` | Identificador del store público de contenido. | Vacío | Crea el store con acceso `public`; no reutilices el store privado de perfiles. |
| `CONTENT_BLOB_READ_WRITE_TOKEN` | Token server-side para importación, eliminación y limpieza. | Vacío | También se configura como secreto en el frontend para el Route Handler BFF; nunca se expone al navegador. |
| `CONTENT_BLOB_PUBLIC_HOST` | Host exacto del store público. | Obligatorio para referencias persistidas | Debe coincidir con el host de la URL pública del store; el backend rechaza referencias si falta o no coincide. |
| `CONTENT_BLOB_MAX_IMAGE_SIZE_BYTES` | Tamaño máximo de imágenes. | `10000000` | Equivale a 10 MB. |
| `CONTENT_BLOB_MAX_VIDEO_SIZE_BYTES` | Tamaño máximo de videos. | `100000000` | Equivale a 100 MB. |
| `CONTENT_BLOB_IMPORT_TIMEOUT_SECONDS` | Timeout al importar una URL externa. | `10` | Se rechazan destinos locales y redes privadas. |
| `CONTENT_BLOB_ORPHAN_RETENTION_HOURS` | Retención de blobs sin referencia. | `24` | La limpieza se ejecuta mediante Vercel Cron. |
| `CRON_SECRET` | Protege el endpoint interno de limpieza. | Vacío | Debe ser un secreto largo y distinto por entorno. |

Formatos de contenido: JPEG, PNG, WebP y AVIF para imágenes; MP4, WebM y MOV para videos.

## Frontend

El frontend usa estas variables en el servidor de Next.js. No llevan el prefijo `NEXT_PUBLIC_` porque no deben exponerse al navegador.

| Variable | Para qué sirve | Valor por defecto | Notas |
| --- | --- | --- | --- |
| `BACKEND_URL` | URL base del backend a la que apuntan el BFF y las funciones server-side del frontend. | `http://localhost:8000` | No incluyas una ruta como `/auth`; debe ser la URL base. Una `/` final funciona con la implementación actual, aunque es más limpio omitirla. |

Ejemplos:

```env
# Desarrollo
BACKEND_URL=http://localhost:8000

# Producción
BACKEND_URL=https://softstack-backend.vercel.app
```

## Docker Compose

`softstack-backend/docker-compose.yml` usa directamente estas variables:

| Variable | Uso en Docker Compose | Fallback de Compose |
| --- | --- | --- |
| `MONGODB_URI` | URI que usa el contenedor `api` para conectarse al servicio MongoDB. | `mongodb://mongodb:27017` |
| `MONGODB_DATABASE` | Base de datos usada por el contenedor `api`. | `softstack` |

El servicio MongoDB se llama `mongodb`; por eso la URI interna de Docker no debe usar `localhost`, ya que `localhost` dentro del contenedor `api` apunta al propio contenedor de la API.

Importante: Docker Compose no inyecta automáticamente todas las variables del archivo `.env` dentro del contenedor. La configuración actual de `docker-compose.yml` solo pasa explícitamente `MONGODB_URI` y `MONGODB_DATABASE` al servicio `api`. Si el backend dentro de Docker necesita JWT, CORS o cookies personalizadas, esas variables deben agregarse explícitamente al bloque `environment` o proporcionarse mediante el mecanismo de secretos de la plataforma.

## Variables de plataforma o variables antiguas

En configuraciones históricas de Vercel se observaron nombres que no forman parte del contrato actual del código:

| Variable | Estado actual |
| --- | --- |
| `JWT_SECRET` | No la lee el código actual; la variable válida es `JWT_SECRET_KEY`. |
| `CORS_ORIGIN` | No la lee el código actual; la variable válida es `CORS_ORIGINS`. |
| `FRONTEND_URL` | Ahora sí forma parte del contrato del backend: se usa para construir enlaces de verificación. No sustituye a `BACKEND_URL`, que es la variable del frontend para localizar la API. |
| `JWT_EXPIRE` | No la lee el código actual; usa `ACCESS_TOKEN_EXPIRE_MINUTES` y `REFRESH_TOKEN_EXPIRE_DAYS`. |
| `CLOUSTER2` | No tiene referencias en el repositorio; parece una variable antigua o un nombre escrito incorrectamente. |
| `EMAIL_API_BASE_URL` | No tiene referencias en el repositorio actual. |
| `SEED_RESET_CONFIRM` | No tiene referencias en el código actual; no debe asumirse que habilita o protege el seed. |
| `NODE_ENV` | Variable estándar de Node/Vercel. No es leída explícitamente por el backend FastAPI. |

Las variables automáticas de Vercel como `VERCEL`, `VERCEL_ENV`, `VERCEL_URL` y `VERCEL_OIDC_TOKEN` pertenecen a la plataforma. No deben copiarse al `.env.example` ni gestionarse manualmente salvo que una integración concreta las necesite.

## Checklist por entorno

### Desarrollo local

Backend:

```env
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=softstack
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
JWT_SECRET_KEY=<clave-local-larga>
ADMIN_EMAILS=<tu-email>
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
COOKIE_DOMAIN=
```

Frontend:

```env
BACKEND_URL=http://localhost:8000
```

### Producción

- Configura `MONGODB_URI` y `JWT_SECRET_KEY` como secretos del proveedor.
- Usa `MONGODB_DATABASE=softstack` salvo que exista una decisión explícita distinta.
- Configura `BACKEND_URL` en el proyecto frontend con la URL pública de la API.
- Configura `CORS_ORIGINS` con los orígenes reales y exactos, sin variables antiguas como `CORS_ORIGIN`.
- Usa `COOKIE_SECURE=true` si el tráfico es HTTPS.
- Mantén `COOKIE_DOMAIN` vacío mientras la autenticación pase por el BFF de Next.js.
- Define `ADMIN_EMAILS` solo con los correos que deben recibir privilegios administrativos al registrarse.

## Diagnóstico rápido

- Si el backend falla al iniciar después de agregar una variable numérica, revisa que `PORT`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `MONGODB_SERVER_SELECTION_TIMEOUT_MS`, `MONGODB_MAX_POOL_SIZE` y `MONGODB_MIN_POOL_SIZE` contengan enteros válidos.
- Si el frontend no encuentra la API, revisa `BACKEND_URL` y que no incluya una ruta adicional.
- Si login funciona pero la sesión no persiste, revisa `COOKIE_SECURE`, `COOKIE_SAMESITE`, `COOKIE_DOMAIN` y que el BFF reenvíe `Set-Cookie`.
- Si un usuario no ve el panel administrativo, verifica que su email estaba en `ADMIN_EMAILS` antes del registro y que el usuario tiene `role=admin` en la base de datos.
- Si las solicitudes directas al backend son bloqueadas por el navegador, revisa `CORS_ORIGINS`; recuerda que `CORS_ORIGIN` no es leído por el código actual.
