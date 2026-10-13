# Reportes y correos COMET

El workflow **Sync COMET to Supabase** reúne la operación COMET del repo unificado:

1. Descarga, valida y actualiza las doce tablas de `public`.
2. Publica las pestañas por categoría y las tres alertas en la hoja de reportes.
3. Envía el resumen deportivo de la semana anterior a los destinatarios confirmados.
4. Envía un aviso técnico del estado final al responsable de operación.

No requiere clonar `dataProject`, ejecutar su código ni mantener sus workflows activos.
El portal web no lanza estos procesos ni recibe las credenciales del worker.

## Configuración de Actions

Además de los secrets del [importador COMET](comet-synchronization.md), configurar:

| Tipo | Nombre | Uso |
|---|---|---|
| Secret | `COMET_REPORT_SMTP_USER` | Cuenta remitente de Gmail |
| Secret | `COMET_REPORT_SMTP_PASSWORD` | Contraseña de aplicación Gmail; nunca contraseña de la BD |
| Secret | `COMET_REPORT_SMTP_PORT` | `465` para TLS implícito o `587` para STARTTLS |
| Secret | `COMET_DATABASE_URL` | Conexión COMET de solo lectura, con SSL |
| Secret | `PORTAL_AUTH_DATABASE_URL` | Conexión privada del portal para configuración y registro de entregas |
| Variable | `COMET_REPORTS_ENABLED` | `true` publica reportes después de sincronizar |
| Variable | `COMET_DIGEST_ENABLED` | `true` habilita el resumen deportivo semanal |
| Variable | `COMET_NOTIFICATIONS_ENABLED` | `true` habilita avisos técnicos de éxito/error |
| Variable | `COMET_REPORT_NOTIFICATION_TO` | Correos del responsable de operación, separados por coma |
| Variable | `COMET_REPORT_SMTP_HOST` | `smtp.gmail.com` por defecto |
| Variable | `COMET_REPORT_SHEET_ID` | ID de la hoja de reportes; por defecto la hoja usada anteriormente por el club |
| Variable | `COMET_REPORT_SEASON` | `2026` por defecto; ajustar al cambiar de temporada |

La cuenta de servicio `GOOGLE_SV_B64` necesita permiso **Editor** sobre la hoja de
reportes. El catálogo de endpoints mantiene scope de solo lectura; el publicador usa
solo el scope Sheets, sin Drive. Comprobar SMTP autentica con TLS sin enviar correo.

En **COMET → Seguimiento y configuración**, guardar los correos de **Destinatarios
del resumen semanal** y marcarlos como confirmados. Requiere la migración
`db/portal/003_comet_followup.sql`, que incluye `portal.comet_digest_deliveries`.
Si falta un destinatario confirmado, SMTP o el registro, el envío falla y no se
presenta como completado. No se añaden destinatarios por nombres de jugadores o scouts.

## Horario y control de duplicados

Con `COMET_SCHEDULE_ENABLED=true`, Actions ejecuta lunes y miércoles a las **06:00 UTC**.
El resumen deportivo comprende la semana anterior, lunes a domingo, según Chile.
La primera ejecución correcta envía; la del miércoles omite los destinatarios que
ya recibieron ese resumen. Si SMTP rechaza explícitamente el correo, admite hasta
tres intentos en ejecuciones posteriores. Si la aceptación quedó en duda, la reserva
no se reenvía automáticamente: revisarla con el administrador del servidor.

El aviso técnico se envía por ejecución y lleva estado y enlace privado al run;
no contiene jugadores, claves ni trazas. Se avisa también de un fallo de reportes o
del resumen semanal. Un correo aceptado por SMTP no prueba su llegada al buzón.

## Reportes de la hoja

Conserva las pestañas por categoría: minutos, partidos/citaciones, titularidad,
entradas desde el banco, goles, tarjetas, goles recibidos por arqueros, participación,
edad, antigüedad y rankings. `Partidos_ganados` y `% Victorias` cuentan el **resultado
final** de los partidos en los que participó; no son el marcador durante su intervalo.
El resultado con el jugador en cancha se consulta en el portal y necesita cronología.

Las tres pestañas de alertas conservan los cálculos anteriores:

- **Alertas Amarillas**: avisos del ciclo 5, 8, 10, 12…; la segunda amarilla no se
  acumula en ese ciclo. Es una interpretación operativa anterior, no certificación de una sanción federativa.
- **Jugadores Poco Utilizados**: menos del 20 % de minutos posibles de la serie.
- **Jugadores en Categoría Superior**: categoría deportiva superior a la edad.

Estas pestañas mantienen compatibilidad con la hoja anterior. Las alertas del resumen
deportivo usan las reglas y períodos configurados en el portal; no sustituyen ese
ciclo antiguo por una regla nueva silenciosamente. Revisar esas reglas con el club.

Primero se calculan todos los reportes. Sin datos jugados para club/temporada, se
detiene la publicación y conserva lo anterior. Una alerta válidamente vacía conserva
encabezados y elimina sus filas antiguas. Cada pestaña se reemplaza en una sola
petición [UpdateCells de Sheets](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/request#updatecellsrequest),
sin vaciarla antes; se conservan formatos y los textos no se interpretan como fórmulas.
No existe una transacción global entre pestañas: ante un fallo, corregir y reejecutar.
Las pestañas ajenas o categorías ausentes de la consulta no se borran.

## Ejecución manual

En **Actions → Sync COMET to Supabase → Run workflow**:

- **dry_run** marcado: no publica ni envía correos.
- **reports_only** marcado: recalcula desde la BD existente sin descargar otra vez COMET.
- Para publicar y enviar: elegir `main`, marcar **reports_only** y desmarcar **dry_run**.
- Para sincronizar y luego reportar: elegir `main`, desmarcar ambas opciones.

La publicación y los correos se rechazan desde otras ramas. Las ejecuciones del
workflow comparten exclusión mutua. Verificar el estado de todos los jobs y los
artifacts `comet-sync-summary` y/o `comet-reports-summary`: solo contienen conteos,
nunca registros de menores, contenido del correo ni credenciales.

Para operar manualmente desde un entorno independiente del servidor:

```bash
python -m pip install -r requirements-comet-reports.txt
# Copiar .env.comet-reports.example a .env.comet-reports.local y completar en privado.
python scripts/publish_comet_reports.py --env-file .env.comet-reports.local
python scripts/publish_comet_reports.py --env-file .env.comet-reports.local --publish --summary-json data/runtime/comet-reports-summary.json
```

Para correo, exportar explícitamente las variables privadas del worker antes de ejecutar:

```bash
python scripts/notify_comet_run.py --check-smtp
python scripts/send_comet_weekly_digest.py --quiet             # prepara, no envía
python scripts/send_comet_weekly_digest.py --quiet --send      # exige las condiciones anteriores
```

`send_comet_weekly_digest.py` y `notify_comet_run.py` no cargan archivos `.env`
automáticamente. No usar la conexión de scouting para COMET ni configurar las
credenciales de servidor en el navegador. Para pausar cada función, poner su variable
`*_ENABLED=false`; mantener desactivados los workflows antiguos de sincronización y Weekly Report.
