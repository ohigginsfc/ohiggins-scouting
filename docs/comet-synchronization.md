# Sincronización COMET → Supabase

El repo unificado incluye su propio importador, `scripts/sync_comet.py`, y el workflow
**Sync COMET to Supabase**. El portal lee las tablas publicadas con `comet_reader`;
la sincronización se ejecuta aparte, con una credencial de servidor. No necesita
Docker, Selenium, Gmail ni el runtime de Sofascore.

## Configuración del worker

En **Settings → Secrets and variables → Actions** del repo unificado:

| Tipo | Nombre | Uso |
|---|---|---|
| Secret | `GOOGLE_SV_B64` | JSON Base64 de cuenta de servicio con acceso a la hoja del catálogo. El worker solicita solo lectura de Sheets |
| Secret | `COMET_SUPABASE_URL` | URL HTTPS del proyecto Supabase, sin ruta ni contraseña |
| Secret | `COMET_SUPABASE_SERVICE_ROLE_KEY` | Clave de servidor para publicar COMET; nunca se entrega al portal ni al navegador |
| Variable | `COMET_ENDPOINT_SOURCE` | `sheets` por defecto; `env` como alternativa explícita |
| Variable | `COMET_SHEET_ID` | ID de la hoja de endpoints; por defecto el catálogo ya usado por el club |
| Variable | `COMET_WORKSHEET` | `ENDPOINTS` por defecto; columnas `NOMBRE`, `LINK` y `NUMERO` opcional |
| Variable | `COMET_REQUEST_DELAY` | 3 segundos por defecto; configurable entre 3 y 60 |
| Variable | `COMET_SCHEDULE_ENABLED` | `false` durante la transición. `true` activa lunes y miércoles a las 06:00 UTC |

Para `COMET_ENDPOINT_SOURCE=env`, configurar el secret `COMET_ENDPOINTS` con JSON
directo o Base64. Formato: `[{"name":"Nombre del informe","api_key":"CLAVE_PRIVADA"}]`.
La fuente es explícita: un fallo de Sheets no cambia silenciosamente al catálogo
del entorno. Las claves de los informes no se publican ni se imprimen en los logs.

Los secrets del repo anterior no se heredan por pertenecer a la misma organización.
El administrador puede configurarlos directamente o trasladarlos cifrados para la
clave pública del repo receptor mediante la
[API oficial de GitHub](https://docs.github.com/en/rest/guides/encrypting-secrets-for-the-rest-api).
Nunca exportar credenciales en claro ni incluirlas en artifacts o documentación.

## Ejecución en Actions

1. Abrir **Actions → Sync COMET to Supabase → Run workflow**.
2. Mantener marcado **dry_run** para descargar y transformar sin escribir.
3. Para publicar, seleccionar `main` y desmarcar **dry_run**. La publicación del
   workflow rechaza cualquier otra rama.
4. Comprobar que el job termina correctamente y descargar el artifact
   `comet-sync-summary`: solo incluye conteos por tabla y auditoría de limpieza.

Un dry-run correcto **no** certifica permisos de escritura ni claves foráneas
remotas. La publicación debe terminar con todas las filas preparadas publicadas.
Los jobs del repo unificado se serializan y no cancelan una publicación en curso.
Esa exclusión no cruza repositorios: durante la transición no ejecutar a la vez
el sincronizador anterior y el nuevo.

## Ejecución manual local o en el servidor

Crear un entorno independiente e instalar `requirements-comet-sync.txt`. Copiar
`.env.comet-sync.example` a **`.env.comet-sync.local`**, que está ignorado por Git,
y completar las credenciales privadas. No reutilizar `.env.portal`, la conexión
de lectura COMET ni la credencial del esquema scouting.

```bash
python -m venv .venv-comet
# Linux: source .venv-comet/bin/activate
# Windows PowerShell: .\.venv-comet\Scripts\Activate.ps1
python -m pip install -r requirements-comet-sync.txt
python scripts/sync_comet.py --env-file .env.comet-sync.local --dry-run
python scripts/sync_comet.py --env-file .env.comet-sync.local --publish --summary-json data/runtime/comet-sync-summary.json
```

El comando sin `--publish` siempre es de validación. No carga automáticamente
archivos `.env`; con `--env-file`, las variables ya exportadas tienen prioridad.
La salida no contiene registros de jugadores, enlaces privados ni claves.

## Alcance y garantías

Se mantiene el contrato de producción del importador anterior y el orden de
publicación de las doce tablas de `public`: competiciones, equipos, competidores,
partidos, jugadores, posiciones, fases, eventos, cambios de estado de partido y
equipo, actuaciones de jugadores y arqueros. `competidores` usa la clave natural
`id,clubid`, respaldada por el índice único existente.

- Todas las descargas y transformaciones terminan antes de la primera escritura.
- Un fallo o catálogo esencial vacío detiene la publicación. Un informe hijo
  válidamente vacío no implica borrar registros históricos.
- Los upserts usan claves estables; reejecutar no duplica las mismas filas.
- Las peticiones COMET tienen pausa entre páginas **y entre informes**. Los 429
  respetan `Retry-After`, con reintentos y esperas limitados. No se evaden bloqueos.
- La publicación reintenta fallos transitorios sobre el mismo lote idempotente;
  400/401/403/409 y fallos de contrato detienen el job, sin exponer cuerpos remotos.
- Cada lote es una petición independiente. **No hay una transacción global de
  las doce tablas**: un fallo durante la publicación puede dejar padres/lotes ya
  actualizados. Corregir la causa y reejecutar; no se devuelve éxito parcial.
- No se escribe en `scouting` ni en `portal`, no se aplican migraciones, no se
  eliminan datos ni se reinicia la web.

El job de ingestión no envía correos ni modifica Sheets. Después de una sincronización
correcta, el mismo workflow puede publicar los reportes por categoría y alertas,
enviar el resumen deportivo semanal y notificar el estado final. Todos esos procesos
viven en el repo unificado: ver [reportes y correos COMET](comet-reports-email.md).
Los dos workflows operativos de `dataProject` deben permanecer desactivados.

## Finalizar la transición

1. Mergear la PR y validar en `main` una descarga y una publicación del nuevo job.
2. Desactivar explícitamente el workflow de sincronización del repo deprecado.
   Revisar también su **Weekly Report**: no dar por retirado ese envío aparte.
3. Confirmar que no quedan ejecuciones antiguas en curso ni publicaciones parciales.
4. Solo entonces poner `COMET_SCHEDULE_ENABLED=true` en el repo unificado.
5. Verificar la primera ejecución programada y que el portal lee los datos
   actualizados. Revisar [cobertura de eventos y goles rivales](resultado-con-jugador-en-cancha.md).

Si el nuevo job falla tras el cambio, mantener el schedule desactivado y usar la
ejecución manual del importador del repo unificado. No activar dos schedules a la vez.
