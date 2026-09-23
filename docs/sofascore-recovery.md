# Recuperación remota de Sofascore

El workflow **Sofascore encrypted recovery** descarga Primera División de Chile
2024 y 2025 en un contenedor Docker de GitHub Actions. Por defecto utiliza
`transport=http`, con la sesión `curl_cffi` y el perfil Chrome 131 del scraper
original. `transport=browser` permite seleccionar Selenium explícitamente.
No cambia de transporte ni de host automáticamente ante un bloqueo. No utiliza
PostgreSQL, VPN ni credenciales del club. Docker empaqueta el runtime; la IP de
salida es la del runner. Sofascore puede rechazarla: una muestra correcta no
garantiza una temporada completa ni un servicio estable.

## Preparación

El workflow solo ejecuta código de `main` y se activa manualmente. No tiene cron.
Necesita `SOFASCORE_ARTIFACT_KEY` en GitHub Secrets: 32 bytes aleatorios codificados
en base64. Mantener una copia privada de esa misma clave fuera de Git para
descifrar localmente. No imprimirla en logs, pegarla en incidencias ni incluirla
en artefactos. No cambiarla durante una recuperación: los archivos anteriores
requieren la clave original. El repositorio es público; únicamente se suben
paquetes cifrados AES-256-GCM, nunca respuestas JSON, cookies ni CSV en claro.

## Operación en Actions

1. `mode=probe`, `season=2024`, `checkpoint=new`, `transport=http`: comprobar
   acceso HTTP, calendario y un partido finalizado con estadísticas. El
   resumen debe indicar `probe_ok: true`. El probe **no** es un paquete de temporada.
2. `mode=collect`, `season=2024`, `checkpoint=new`: iniciar recuperación.
3. Repetir `mode=collect`, `season=2024`, `checkpoint=latest` hasta `validated`.
   También puede indicarse un `run_id` concreto de este mismo workflow en `main`.
4. Repetir el procedimiento para 2025; no iniciar ambas temporadas en paralelo.
5. Opcionalmente ejecutar `mode=validate`, temporada y checkpoint deseados, para
   revisar el paquete sin acceder a Sofascore.

Cada lote limita la descarga a 25 partidos, 300 peticiones y 45 minutos de
transporte, con al menos cinco segundos entre peticiones. Los presupuestos
incluyen la apertura HTTP inicial, paginación, incidentes, estadísticas individuales y reintentos. El
workflow completo tiene un límite de 60 minutos, incluyendo construcción y
subida. No descargar biografías adicionales: conservar los datos embebidos y
los campos no disponibles como ausentes.

Se guarda un checkpoint cifrado después de cada página y partido completo.
Una cancelación abrupta del runner puede perder el lote en curso: la siguiente
ejecución retoma el último artefacto subido, no supone que esos partidos se
completaron. Los errores controlados conservan el avance mediante `always()`.

### Estados

| Estado | Significado y acción |
|---|---|
| `partial` | Avance guardado; reanudar con `latest`. No importable. |
| `blocked` | HTTP 401/403/429; detener y diagnosticar. No reintento automático ni cambio de IP. |
| `invalid` | Respuesta, runtime o datos no válidos; revisar antes de continuar. |
| `validated` | Calendario completo y todos los partidos finalizados resueltos, sin errores pendientes. |

El workflow puede terminar correctamente con `partial`: significa un lote
guardado, no sincronización completa. El resumen muestra temporada, esperados,
completados y errores. Un 429 guarda `Retry-After`; si falta, aplica una espera
mínima de 24 horas. Las reanudaciones se rechazan hasta que termine ese plazo.
Los fallos transitorios de red/5xx admiten dos reintentos, tras 30 y 120 segundos.

Los checkpoints no se guardan en Git ni en la caché de Actions. Los artefactos
caducan a los 90 días; descargar una copia privada al completar cada temporada.
`latest` busca entre las últimas 100 ejecuciones completadas; si el archivo falta,
caducó o está fuera de esa ventana, falla explícitamente. Indicar su `run_id` o
iniciar `new` de forma consciente. `refresh=true` descarta el avance y vuelve a
descargar toda la temporada; no se aplica automáticamente.

## Validación e importación local

Instalar los requirements del proyecto y disponer de `gh` autenticado cuando se
descargue por ejecución. Exportar `SOFASCORE_ARTIFACT_KEY` desde la copia privada;
los comandos siguientes no contienen la clave.

```bash
python scripts/sofascore_recovery.py local --season 2024 --run-id RUN_ID
python scripts/sofascore_recovery.py local --season 2024 --package data/recovery/downloads/2024-RUN_ID.sofa
```

Ambos comandos solo descifran y validan en memoria. Para aplicar:

```bash
python scripts/sofascore_recovery.py local --season 2024 --run-id RUN_ID --apply --pg-dump /ruta/a/pg_dump
```

`--apply` acepta exclusivamente `scouting_local` en localhost, crea primero un
dump privado en `data/recovery/backups` y publica métricas y estados de los IDs
exactos en una sola transacción. Una clave incorrecta, checksum inválido,
temporada distinta, paquete parcial o backup fallido impide la importación.
Reaplicar el paquete reemplaza su ámbito sin duplicar métricas. Los datos demo
y otras temporadas se conservan. La integración con la BD del club es otro hito.

## Pruebas sin Sofascore

```bash
python -m pytest -q
docker compose -f docker-compose.recovery.yml build collector
docker compose -f docker-compose.recovery.yml run --rm --entrypoint python collector scripts/test_selenium_runtime.py
```

La prueba Selenium abre una página local; no certifica acceso al proveedor. CI
usa una clave sintética y PostgreSQL de prueba. El criterio de recuperación es
obtener los dos paquetes completos, importarlos y verificar el panel y la
comparación 2024/2025 con datos reales.
