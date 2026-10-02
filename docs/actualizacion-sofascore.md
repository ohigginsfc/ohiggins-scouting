# Actualización del worker de Sofascore

Guía para el **administrador del servidor**. Actualizada el 3 de octubre de 2026.

El cambio del worker está integrado en `main` mediante la [PR #14](https://github.com/ohigginsfc/ohiggins-scouting/pull/14), con ambos checks correctos.
Commit: `8f9b26487112fe75cd0f00d074faba3abb6c8397`.

Supabase tiene publicado el corte validado de Chile 2026: **183 partidos, 523 jugadores y 21.419 métricas**.
Los informes y los históricos se conservaron, comprobados por hashes, con un respaldo lógico previo.
El siguiente paso es actualizar el worker del servidor y comprobar acceso desde EC2.

## 1. Actualizar el checkout y construir el worker

Desde la raíz del checkout de `ohigginsfc/ohiggins-scouting`:

```bash
git remote get-url origin
git fetch origin
git checkout main
git pull --ff-only origin main
docker compose -f docker-compose.sync.yml build collector publisher
```

El remoto debe apuntar a `https://github.com/ohigginsfc/ohiggins-scouting.git` o a su equivalente SSH.
Conservar el `.env` privado y `data/recovery`. Si Git se detiene por cambios o conflictos, resolverlos antes de seguir.

## 2. Comprobar acceso desde EC2

```bash
docker compose -f docker-compose.sync.yml run --rm collector probe
```

Seguir únicamente si devuelve `status=access_ok` y salida `0`. Hace una sola petición al calendario y no escribe en Supabase.
Un **403/429 obliga a parar**; en 429, respetar `retry_at`.
El éxito local y los checks de CI no garantizan que la IP del servidor tenga acceso. No repetir pruebas en bucle.

## 3. Preparar la caché si el servidor no la tiene

El paquete privado `SCOUTING_CACHE_2026_2026-10-03.zip` contiene el `candidate.json` validado y un manifiesto SHA-256.
No contiene `.env`, credenciales, informes del club ni respaldos de la BD.

Copiar el ZIP al servidor y, desde la raíz del repo, extraer sin sobrescribir:

```bash
unzip -n /ruta/SCOUTING_CACHE_2026_2026-10-03.zip -d .
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
docker compose -f docker-compose.sync.yml run --rm collector collect --max-requests 120 --seconds 1800
docker compose -f docker-compose.sync.yml run --rm collector validate
docker compose -f docker-compose.sync.yml run --rm publisher publish
```

`collect` y `validate` deben devolver `validated=true`.
Se revisan partidos nuevos, cambios de checksum y los últimos 14 días, con al menos cinco segundos entre peticiones, un máximo de 120 peticiones y 30 minutos.

`publish` sin `--apply` comprueba el candidato y su compatibilidad con la BD; no publica.
Solo si esas comprobaciones pasan, ejecutar:

```bash
docker compose -f docker-compose.sync.yml run --rm publisher publish --apply
```

El publisher usa `SCOUTING_DATABASE_URL` del `.env` privado y el esquema `scouting`.
Antes de publicar guarda un respaldo en `data/recovery/manual-2026/backups`.
El resultado queda en `data/recovery/manual-2026/publication.json`.

## 5. Reanudar una ejecución incompleta

Después de resolver el fallo o agotar una espera indicada por el proveedor:

```bash
docker compose -f docker-compose.sync.yml run --rm collector collect --resume --max-requests 120 --seconds 1800
```

Luego repetir `validate`, `publish` sin `--apply` y, si pasan, `publish --apply`.
No borrar un checkpoint incompleto ni lanzar dos recolectores sobre la misma carpeta.
`--resume` conserva el corte inicial; tras completar la ejecución, la próxima actualización empieza con `collect`, sin `--resume`.

## 6. Pendientes y validación realizada

Comprobar `probe` y una actualización completa desde EC2. Después se podrá programar el cron semanal con bloqueo de concurrencia y registro de errores.
No hay cron activado ni descarga directa de Sofascore validada en GitHub Actions.
La web no necesita volver a cargar estos datos: ya están en Supabase.

La prueba local real usó 7 peticiones de calendario y 2 para descargar alineaciones e incidencias de un partido; validó **183/183 partidos y 523 jugadores**.
Publicación en Supabase completada y verificada el 03/10/2026:
`b8018745-d070-4f60-8895-5285a20ce35d`.
