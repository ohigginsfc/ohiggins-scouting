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
