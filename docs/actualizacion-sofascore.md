# Actualización del worker de Sofascore

Guía para el **administrador del servidor**. Actualizada el 17 de noviembre de 2026.

El worker actualiza Chile/Primera/2026 en el esquema `scouting` de Supabase.
El portal y el worker son procesos independientes: **levantar la web no instala ni ejecuta el cron**.
La fecha de descarga y el alcance del último intento semanal quedan en `data/recovery/manual-2026/weekly-summary.json`.
Solo `status=published` y `applied=true` confirman una publicación del comando semanal; `validated`, `blocked` o `stopped` no la confirman.

## 1. Actualizar el checkout y construir el worker

Desde la raíz del checkout de `ohigginsfc/ohiggins-scouting`:

```bash
git remote get-url origin
git fetch origin
git checkout main
git pull --ff-only origin main
docker compose --env-file .env.portal -f docker-compose.sync.yml build collector publisher
```

El remoto debe apuntar a `https://github.com/ohigginsfc/ohiggins-scouting.git` o a su equivalente SSH.
Conservar los archivos de entorno privados y `data/recovery`. Si Git se detiene por cambios o conflictos, resolverlos antes de seguir.

## 2. Comprobar acceso desde EC2

```bash
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T collector probe
```

Seguir únicamente si devuelve `status=access_ok` y salida `0`. Hace una sola petición al calendario y no escribe en Supabase.
Un **403/429 obliga a parar**; en 429, respetar `retry_at`.
El éxito local y los checks de CI no garantizan que la IP del servidor tenga acceso. No repetir pruebas en bucle.

## 3. Preparar la caché si el servidor no la tiene

El paquete privado `SCOUTING_CACHE_2026_2026-11-17.zip` contiene el `candidate.json` validado y un manifiesto SHA-256.
No contiene `.env`, credenciales, informes del club ni respaldos de la BD.

Copiar el ZIP al servidor y, desde la raíz del repo, extraer sin sobrescribir:

```bash
unzip -n /ruta/SCOUTING_CACHE_2026_2026-11-17.zip -d .
```

Sustituir `/ruta` por la ubicación real del ZIP. Debe quedar:

```text
data/recovery/manual-2026/candidate.json
```

Si ya hay un checkpoint, conservarlo. Si está incompleto, seguir el [apartado de reanudación](#5-reanudar-una-ejecución-incompleta).
Sin caché, `collect` intentaría descargar la temporada entera; esta copia evita repetir los históricos para iniciar el incremental.

## 4. Actualizar 2026 manualmente

Ejecutar **cada comando solo si el anterior terminó con salida `0`**:

```bash
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T collector collect --max-requests 120 --seconds 1800
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T collector validate
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T publisher publish
```

`collect` y `validate` deben devolver `validated=true`.
Se revisan partidos nuevos, cambios de checksum y los últimos 14 días, con al menos cinco segundos entre peticiones, un máximo de 120 peticiones y 30 minutos.

`publish` sin `--apply` comprueba el candidato y su compatibilidad con la BD; no publica.
Solo si esas comprobaciones pasan, ejecutar:

```bash
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T publisher publish --apply
```

El publisher usa `SCOUTING_DATABASE_URL` del `.env.portal` privado y el esquema `scouting`.
Antes de publicar guarda un respaldo en `data/recovery/manual-2026/backups`.
El resultado queda en `data/recovery/manual-2026/publication.json`.

## 5. Reanudar una ejecución incompleta

Después de resolver el fallo o agotar una espera indicada por el proveedor:

```bash
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T collector collect --resume --max-requests 120 --seconds 1800
```

Luego repetir `validate`, `publish` sin `--apply` y, si pasan, `publish --apply`.
No borrar un checkpoint incompleto ni lanzar dos recolectores sobre la misma carpeta.
`--resume` conserva el corte inicial; tras completar la ejecución, la próxima actualización empieza con `collect`, sin `--resume`.

## 6. Pendientes y validación realizada

La instalación del cron en EC2 corresponde al administrador del servidor. No se activa al hacer `git pull`, reconstruir la imagen ni iniciar Streamlit.
GitHub Actions sigue sin una descarga directa validada de Sofascore. El acceso correcto desde un PC no garantiza acceso desde la IP de EC2.

Como referencia histórica, la publicación del 03/10/2026 validó 183 partidos y 523 jugadores. Las siguientes ejecuciones deben comprobarse con su propio resumen y lote, no con esas cifras.

## 7. Activar la sincronización semanal en el servidor

Requisitos: Linux con `bash` y `flock` (paquete `util-linux`), Docker Compose y un usuario con acceso a Docker.
El `.env.portal` privado debe contener `SCOUTING_DATABASE_URL` con permisos para importar en `scouting`, usando session pooler y SSL. No se necesitan las claves de Supabase Auth.
Si el archivo privado tiene otro nombre, usar `SCOUTING_SYNC_ENV_FILE=/ruta/archivo` al invocar el lanzador.

Desde el checkout actualizado y con una caché conservada en `data/recovery/manual-2026`:

```bash
mkdir -p data/logs data/runtime
chmod 600 .env.portal
docker compose --env-file .env.portal -f docker-compose.sync.yml build collector publisher
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T collector probe
```

Solo si la prueba devuelve `access_ok`, ejecutar una actualización real:

```bash
bash scripts/sync_scouting_weekly.sh
cat data/recovery/manual-2026/weekly-summary.json
```

El lanzador obtiene un bloqueo exclusivo, reanuda un checkpoint incompleto y después refresca el calendario hasta el nuevo corte.
Descarga lo nuevo, lo modificado y los últimos 14 días, con pausas mínimas de cinco segundos. El presupuesto compartido es de 240 peticiones y 30 minutos de descarga por ejecución.
Solo publica una temporada completa y validada. Guarda respaldo antes de la publicación y conserva los informes, COMET y los históricos 2024/2025.
Ante un 403/429 para; `Retry-After` queda registrado y se respeta en el siguiente intento semanal. Un límite agotado conserva el checkpoint y no publica datos parciales.

Si termina correctamente, instalar con `crontab -e` esta línea, sustituyendo `/RUTA/ohiggins-scouting` por la ruta absoluta real:

```cron
15 6 * * 2 /bin/bash /RUTA/ohiggins-scouting/scripts/sync_scouting_weekly.sh >> /RUTA/ohiggins-scouting/data/logs/sofascore-weekly.log 2>&1
```

Ejecuta los martes a las 06:15 **en la zona horaria del servidor**. Comprobarla con `timedatectl`; si el servidor usa UTC, serán las 06:15 UTC. No instalar la misma tarea en dos usuarios ni en dos servidores.
La primera ejecución desde EC2 debe validarse antes de dejar el cron activo.

Para comprobarlo después:

```bash
crontab -l
tail -n 30 data/logs/sofascore-weekly.log
cat data/recovery/manual-2026/weekly-summary.json
```

El resumen incluye inicio, final, corte, último partido, cantidades y resultado de publicación. Un proceso solapado sale con código 75; un bloqueo del proveedor, con 2; un fallo o presupuesto agotado, con 1.
Conservar y rotar los logs y respaldos privados. No ejecutar el procedimiento manual sobre la misma carpeta mientras corre el semanal.
Si EC2 devuelve 403, dejar el cron sin activar y actualizar desde un equipo con acceso comprobado; no repetir peticiones ni asumir que Docker cambia la IP.
