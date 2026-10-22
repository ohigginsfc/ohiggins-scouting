# Control de transferencia de Supabase

El límite de **Egress** mide los datos enviados desde Supabase, no el espacio ocupado
por las tablas ni las descargas realizadas desde Sofascore o COMET hacia los workers.
Una BD pequeña puede agotar el límite si se vuelve a consultar completa en cada interacción.

## Consultas de scouting

Las comparaciones objetivas conservan el JSON original en `objective_metrics.raw_payload`
para trazabilidad, pero sus consultas de cohorte devuelven únicamente los campos que
usan: posición objetiva y, cuando hace falta mostrarla, equipo. El cálculo sigue
resolviendo la posición en Python con la misma prioridad de campos y sin inferirla
de la posición manual del scout.

Para contar jugadores comparables, `DISTINCT` se aplica a jugador y posición objetiva
proyectada. Los datos de depuración o las copias del JSON de cada métrica no deben
crear miles de filas redundantes para el mismo jugador. Los promedios, percentiles,
unidades, mínimos de muestra y filtros de origen conservan sus reglas.

Los reportes COMET por REST también usan una lista explícita de columnas. Al cambiar
sus cálculos, actualizar `REPORT_COLUMNS` y comprobar que cubre todas las lecturas;
no usar `select=*` como solución a una columna ausente.

## Operación

### Caché del portal

Las pantallas de lectura de scouting reutilizan durante **15 minutos** los bloques
objetivos de un jugador y los resultados de conteos, promedios y percentiles de sus
cohortes. Se guardan como máximo **128 entradas** en memoria del proceso, sin
persistencia en disco. Cambiar de jugador, temporada, competición, métricas, origen
o ámbito de comparación utiliza una entrada diferente. La conexión real (servidor,
BD, rol y opciones de esquema) también forma parte de la clave.

La sesión se comprueba **antes de cada acceso**, incluso si el resultado está en
caché. No se cachean sesiones, permisos, informes subjetivos ni escrituras. COMET
conserva su caché de diez minutos y su acceso exclusivo de administración. Los
workers e importadores no activan la caché del portal.

Después de una sincronización, las pantallas pueden conservar el resultado anterior
hasta que caduque esa entrada, como máximo quince minutos desde su carga. Reiniciar
el contenedor del portal vacía su caché. Cada réplica o demo tiene su propia caché;
no comparte memoria con otros procesos, aunque todos usen la misma BD y cuota.

### Pruebas sin consumo de producción

Ejecutar la suite desde la raíz del repositorio:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

El `conftest.py` de la raíz instala el aislamiento **antes de recopilar las pruebas**:
retira las variables de credenciales heredadas, desactiva la carga de `.env`, bloquea
HTTP real de `requests` y `curl_cffi`, y bloquea conexiones de socket externas. Las
respuestas de proveedores se simulan en las pruebas. Los socketpairs locales siguen
habilitados para que funcionen los bucles de eventos de Streamlit.
La prueba de cabeceras HTTP habilita únicamente el puerto de su propio servidor
sintético mientras lo utiliza, sin seguir redirecciones. No habilita el acceso al
dashboard local ni a ningún servicio externo.

PostgreSQL solo admite un destino explícito loopback (`localhost`, `127.0.0.1` o
`::1`) y una base llamada **`scouting_test`**, mediante las conexiones de `psycopg`.
La suite nunca toma `SCOUTING_DATABASE_URL` como sustituto de su conexión de pruebas.
Si no se configura `SCOUTING_TEST_DATABASE_URL`, se omiten los casos de integración
PostgreSQL. Si esa variable apunta a otro destino, se aborta antes de recopilar.

Para los casos PostgreSQL, crear primero una instancia local desechable o utilizar
el servicio sintético de GitHub Actions. Ejemplo para una instancia local ya creada:

```bash
SCOUTING_TEST_DATABASE_URL='postgresql://scouting_test:synthetic-test-password@127.0.0.1:5432/scouting_test' python -m pytest -q
```

En PowerShell, asignar la variable con `$env:SCOUTING_TEST_DATABASE_URL='...'` y
ejecutar `python -m pytest -q` después. No utilizar credenciales productivas ni
`.env.portal`. Estas protecciones corresponden al proceso de pytest; no convierten
un navegador, script de diagnóstico o contenedor iniciado por separado en un entorno
aislado. Una demostración conectada a Supabase sigue consumiendo transferencia.

### Seguimiento del consumo

1. En la organización de Supabase, consultar **Usage → Egress** para el ciclo vigente.
   El tooltip de cada día distingue Shared Pooler, PostgREST, Auth y otros servicios.
2. Shared Pooler incluye las consultas PostgreSQL del servidor, demos locales y procesos
   de operación que apuntan al mismo proyecto. Una demo conectada a producción no es
   una base aislada de pruebas.
3. Revisar las consultas con más filas devueltas en `pg_stat_statements`. Sus contadores
   acumulan desde `stats_reset` y no equivalen automáticamente al ciclo de facturación.
4. Para medir una mejora, calcular conteos/tamaños agregados en el servidor. No descargar
   toda la tabla o el JSON completo para medir cuánto ocupa. El tamaño serializado de una
   consulta no es un recibo de bytes facturados ni incluye todo el tráfico del proyecto.
5. Ejecutar pruebas de cálculos/SQL con la BD local desechable `scouting_test` o el
   PostgreSQL de CI. Reservar las comprobaciones sobre datos reales a casos concretos
   y de solo lectura; evitar rondas extensivas de AppTest contra producción.
6. Mantener caché de datos deportivos donde proceda. No usar una caché de datos para
   omitir comprobaciones de sesión, cuenta activa o permisos.

## Si el proyecto está restringido

`HTTP 402` con `exceed_egress_quota` indica una restricción del proyecto que también
puede impedir iniciar sesión. No se resuelve cambiando la contraseña de un usuario.
Consultar el ciclo y las opciones de recuperación en la consola. Las optimizaciones
reducen tráfico futuro, pero no restituyen lo consumido. No cambiar el plan, el límite
de gasto ni las credenciales como parte de un despliegue de código.

Fuentes oficiales: [Egress](https://supabase.com/docs/guides/platform/manage-your-usage/egress)
y [códigos HTTP](https://supabase.com/docs/guides/troubleshooting/http-status-codes).
