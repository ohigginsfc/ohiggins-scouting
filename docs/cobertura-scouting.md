# Cobertura de datos de scouting

El catálogo del worker está en `src/scouting/sofascore_leagues.py`. Las competiciones se guardan separadas por país, división, competición y temporada.

| Clave del worker | Competición | Torneo Sofascore | Temporada Sofascore | Carpeta de caché |
|---|---|---:|---:|---|
| `cl_primera` | Primera División Chile 2026 | 11653 | 88493 | `data/recovery/manual-2026` |
| `cl_primera_b` | Primera B / Liga de Ascenso Chile 2026 | 1240 | 89007 | `data/recovery/cl-primera-b-2026` |
| `ar_primera` | Primera División / Liga Profesional Argentina 2026 | 155 | 87913 | `data/recovery/ar-primera-2026` |
| `ar_primera_nacional` | Primera Nacional Argentina 2026 (segundo nivel) | 703 | 87940 | `data/recovery/ar-primera-nacional-2026` |
| `uy_primera` | Primera División / Liga AUF Uruguay 2026 | 278 | 89288 | `data/recovery/uy-primera-2026` |

Primera B es el segundo nivel de Chile; no es la competición llamada Segunda División Profesional.
Los históricos 2024/2025 de Primera se conservan en la BD y no se vuelven a descargar al añadir otra liga.

## Calidad y separación de datos

La disponibilidad de estadísticas puede cambiar entre ligas y partidos. El worker conserva los valores observados y sus contadores de presencia; no convierte métricas ausentes en ceros.
En Primera B la cobertura puede ser más básica: no se deben asumir ratings, pases o xG por el hecho de disponer de alineaciones, minutos o goles.
Comparar únicamente métricas y muestras disponibles para cada jugador. El filtro **Competición** conserva los nombres exactos de la BD y añade las ligas configuradas pendientes de publicación.
En **Scouting → Datos objetivos → Liga / competición**, el selector reúne las ligas configuradas de la temporada activa y las que ya tienen métricas. Las configuradas sin datos publicados se identifican como **pendiente**: al seleccionarlas se informa del estado, sin consultar ni mostrar otra liga como sustituto. Una liga publicada filtra por su nombre exacto y conserva sus métricas separadas. Los cambios aparecen tras actualizar el contenedor del portal; no basta con reiniciar un contenedor construido con código anterior.

Cada candidato identifica liga, torneo y temporada. No se puede reutilizar un checkpoint de Primera como si fuera de Primera B.
Una publicación sustituye únicamente su ámbito de competición/temporada, con validación completa y una transacción para métricas y estados de partidos.
No modifica COMET, los informes ni las métricas de otras ligas.

Los jugadores ya identificados por su ID de Sofascore se reutilizan entre competiciones.
Un ID nuevo nunca se fusiona por nombre con una ficha que ya tiene otro ID de Sofascore, tampoco al volver a importar Primera.
Para Primera B y las ligas de Argentina y Uruguay, un ID nuevo no se vincula automáticamente a una ficha existente solo por compartir nombre: se conserva una identidad separada y se cuenta como pendiente de revisión.
El nombre visible no cambia y los informes permanecen en su ficha original. La vinculación manual debe confirmarse en el módulo de matching; no deducir identidad únicamente por el nombre.
No se reasignan ni se corrigen automáticamente identificadores antiguos.

## Primera carga de Primera B

Desde la raíz del repo, conservar `.env.portal` y construir el worker actualizado:

```bash
docker compose --env-file .env.portal -f docker-compose.sync.yml build collector publisher scheduler-primera-b
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T collector probe --league cl_primera_b
```

Continuar únicamente si la prueba devuelve `access_ok`. Ante 403/429, parar y respetar la espera registrada.
Si hay un paquete privado de caché validada de Primera B, extraerlo en la raíz sin sobrescribir checkpoints existentes. La caché no incluye credenciales ni informes.

Sin una caché previa, la primera descarga requiere recorrer todos los partidos terminados y puede tardar decenas de minutos. No lanzar otra descarga simultánea:

```bash
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T collector collect --league cl_primera_b --max-requests 600 --seconds 7200
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T collector validate --league cl_primera_b
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T publisher publish --league cl_primera_b
```

El último comando valida la compatibilidad con la BD sin publicar. Si todos terminan con código 0:

```bash
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T publisher publish --league cl_primera_b --apply
```

Para continuar una descarga incompleta, usar `collect --league cl_primera_b --resume` con los mismos límites; no borrar el checkpoint ni publicarlo como si estuviera completo.
Mantener detenidos los schedulers mientras se trabaja manualmente sobre sus carpetas.

## Actualización semanal de Primera B

Después de completar la primera carga y comprobar acceso desde el servidor:

```bash
docker compose --env-file .env.portal -f docker-compose.sync.yml --profile primera-b up -d --build scheduler-primera-b
```

El servicio es optativo: el comando de despliegue habitual del portal o de Primera no lo activa.
Primera continúa los martes a las **06:15 UTC**; Primera B se programa a las **07:15 UTC** para escalonar el trabajo.
Cada liga mantiene su propia agenda, checkpoint y resumen. El mutex de Sofascore es común, para evitar descargas simultáneas.
El cooldown del proveedor también es común: `data/recovery/sofascore-cooldown.json` respeta el `Retry-After` más largo; una denegación sin plazo aplica una espera de 24 horas.
No borrar ese archivo para forzar consultas. No duplicar estas tareas mediante cron ni lanzar recolectores manuales mientras estén activas.

```bash
docker compose --env-file .env.portal -f docker-compose.sync.yml --profile primera-b logs --tail 50 scheduler-primera-b
cat data/recovery/cl-primera-b-2026/scheduler-state.json
cat data/recovery/cl-primera-b-2026/weekly-summary.json
```

La publicación requiere `status=published` y `applied=true` en el resumen semanal. Un contenedor arrancado no demuestra que el servidor tenga acceso a Sofascore.

## Medir el crecimiento de Supabase

El script mide el tamaño físico de PostgreSQL y de las tablas de scouting, incluyendo índices y TOAST. Solo ejecuta consultas agregadas en una transacción de lectura.
Antes de añadir una liga:

```bash
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T --entrypoint python publisher scripts/measure_scouting_storage.py --output data/recovery/storage-before.json
```

Después de publicar:

```bash
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T --entrypoint python publisher scripts/measure_scouting_storage.py --output data/recovery/storage-after.json --compare data/recovery/storage-before.json
```

La comparación conserva el cambio de bytes de la BD y de cada tabla. No oculta deltas negativos: PostgreSQL puede reutilizar o liberar espacio, y otra actividad concurrente puede influir.
Los conteos por liga permiten comprobar qué datos se añadieron. El incremento físico observado no es una cuota garantizada para futuras cargas.
**Almacenamiento y transferencia (egress) son límites diferentes.** Las consultas, cachés y respaldos también deben vigilarse al ampliar cobertura; las pruebas no deben consultar producción.

## Argentina, Uruguay y activación conjunta

El catálogo incluye las tres competiciones de Argentina y Uruguay, con IDs comprobados mediante el catálogo de temporadas y el calendario de Sofascore el **20 de noviembre de 2026**.
Las muestras de Argentina Primera y Primera Nacional incluían estadísticas detalladas. En Uruguay una muestra reciente no tenía estadísticas de jugador, mientras que una anterior sí: un HTTP 200 no garantiza cobertura completa.
El colector rechaza partidos sin estadísticas suficientes y conserva el checkpoint. No los sustituye por ceros ni publica una temporada incompleta como completa; revisar el error y repetir posteriormente con `--resume` cuando el proveedor disponga de los datos.
Registrar una liga en el catálogo no significa que ya esté publicada en Supabase. El selector la muestra como pendiente; sus métricas estarán disponibles cuando se publique su primer lote válido.

### Primera carga de cada nueva liga

El mismo procedimiento de Primera B sirve para `ar_primera`, `ar_primera_nacional` y `uy_primera`. Ejecutar una liga cada vez; no lanzar la siguiente si hay 403/429 ni borrar el cooldown compartido.
Ejemplo para Primera Argentina, antes de activar los schedulers:

```bash
docker compose --env-file .env.portal -f docker-compose.sync.yml build collector publisher
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T collector probe --league ar_primera
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T collector collect --league ar_primera --max-requests 1200 --seconds 14400
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T collector validate --league ar_primera
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T publisher publish --league ar_primera
docker compose --env-file .env.portal -f docker-compose.sync.yml run --rm -T publisher publish --league ar_primera --apply
```

Continuar únicamente con código 0 en cada paso. Si solo se agotó el presupuesto, conservar lo ya descargado y continuar con `collect --league ar_primera --resume --max-requests 1200 --seconds 14400`.
Si faltan estadísticas o hay denegación del proveedor, revisar primero el motivo; `--resume` no corrige datos ausentes.
Una carga inicial grande puede necesitar varios tramos. No elevar el límite semanal para hacerla pasar por una actualización incremental.
Si se entrega una caché privada validada, extraerla en la raíz antes de activar servicios, sin sobrescribir un checkpoint más reciente. El paquete debe conservar las carpetas de cada liga y no contener `.env`, contraseñas ni respaldos.

### Una sola activación para las cinco ligas

Después de integrar el cambio, comprobar acceso desde EC2, completar/sembrar las primeras cargas y retirar cron duplicados:

```bash
git pull --ff-only origin main
docker compose --env-file .env.portal -f docker-compose.portal.yml up -d --build portal
docker compose --env-file .env.portal -f docker-compose.sync.yml --profile leagues up -d --build scheduler scheduler-primera-b scheduler-argentina scheduler-argentina-nacional scheduler-uruguay
```

Los cinco procesos se mantienen en segundo plano con reinicio automático. No publican puertos ni cambian el servicio web.
Al instalar por primera vez solo programan la siguiente ejecución: **no descargan en el arranque**.

| Servicio | Liga | Martes, UTC |
|---|---|---|
| `scheduler` | Chile Primera | 06:15 |
| `scheduler-primera-b` | Chile Primera B | 07:15 |
| `scheduler-argentina` | Argentina Primera | 08:15 |
| `scheduler-argentina-nacional` | Argentina Primera Nacional | 09:15 |
| `scheduler-uruguay` | Uruguay Primera | 10:15 |

Cada intento mantiene el presupuesto de **240 peticiones / 30 minutos**, pausa mínima de cinco segundos y revisión de los últimos 14 días; reutiliza el resto de la caché. Comparte lock y cooldown con las demás ligas; si otro worker tiene el lock, registra `busy` y no descarga simultáneamente.
La temporada configurada es **2026**: no cambia automáticamente a 2027. Verificar los IDs antes de cambiar de campaña.

```bash
docker compose --env-file .env.portal -f docker-compose.sync.yml --profile leagues ps
docker compose --env-file .env.portal -f docker-compose.sync.yml --profile leagues logs --tail 50 scheduler-primera-b scheduler-argentina scheduler-argentina-nacional scheduler-uruguay
```

Revisar `scheduler-state.json` y `weekly-summary.json` dentro de la carpeta de cada liga. `waiting` solo confirma que hay una agenda; una publicación real requiere `status=published` y `applied=true` en el resumen semanal.
Para mantenimiento manual, detener los cinco schedulers con el mismo Compose y `stop scheduler scheduler-primera-b scheduler-argentina scheduler-argentina-nacional scheduler-uruguay`. Mantener `data/recovery` en disco.
