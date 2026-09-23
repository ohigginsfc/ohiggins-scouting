# PostgreSQL remoto con esquema scouting

## Desplegar el dashboard con Supabase

Usar el archivo independiente `docker-compose.supabase.yml` (no combinarlo con
el Compose local o EC2). Arranca únicamente Streamlit, conectado al esquema
existente: no levanta otro PostgreSQL ni ejecuta migraciones o datos demo.

En el `.env` privado del servidor configurar `SCOUTING_DATABASE_URL` con la
credencial de scouting y `sslmode=require`, `SCOUTING_USERNAME`,
`SCOUTING_PASSWORD_HASH` y opcionalmente `SCOUTING_APP_PORT` (por defecto 18501).
Escapar cada `$` del hash bcrypt como `$$` para la interpolación de Compose.
No copiar las credenciales en el repositorio ni en una imagen Docker.

```bash
git pull --ff-only
docker compose -f docker-compose.supabase.yml config -q
docker compose -f docker-compose.supabase.yml up -d --build app
docker compose -f docker-compose.supabase.yml exec -T app python -c "from scouting.db import get_connection; c=get_connection(); c.execute('SET TRANSACTION READ ONLY'); print('schema, metrics:', c.execute('SELECT current_schema(), count(*) FROM objective_metrics').fetchone()); c.close()"
```

La última comprobación debe indicar `scouting` y el número de métricas remoto.
Abrir `http://IP_DEL_SERVIDOR:18501` o el dominio configurado por el administrador.
Si otra instalación ocupa ese puerto, coordinar su parada o elegir otro puerto;
conservar sus volúmenes de PostgreSQL como respaldo.

Este despliegue mantiene desactivada la descarga desde la interfaz hasta validar
la sincronización incremental. No programa un cron. Publicar este archivo en
GitHub no reinicia una web existente: el administrador debe ejecutar estos
comandos en el servidor con sus variables privadas.

## Conexión y permisos

La aplicación y los importadores admiten `SCOUTING_DATABASE_URL` como conexión
PostgreSQL completa (URI o formato libpq). Si está definida, tiene prioridad sobre
las variables locales `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`.
Mantener `sslmode=require` para conexiones remotas.

Configurar `DB_SCHEMA=scouting` limita el search_path de cada conexión a ese
esquema, sin fallback a public. La aplicación rechaza esquemas inexistentes o
inaccesibles antes de ejecutar consultas de negocio. No modifica el search_path
global de la base de datos ni de COMET.

Usar una credencial propia con USAGE sobre scouting, permisos de lectura/escritura
sobre sus tablas y USAGE sobre secuencias. Las migraciones se ejecutan con una
credencial administrativa separada. No exponer el esquema a la Data API ni dar
permisos a anon/authenticated cuando solo se utiliza la conexión PostgreSQL.

En una máquina con IPv4, copiar la conexión Session pooler desde Connect de
Supabase; no deducir el hostname. Conservar las credenciales en el entorno del
servidor o en Secrets de GitHub, nunca en archivos versionados.

La conexión remota no despliega Streamlit ni garantiza acceso a Sofascore desde
el runner. Verificar por separado: extracción, validación, publicación atómica
en PostgreSQL y lectura de la aplicación. Una respuesta 403 del proveedor debe
detener la extracción y conservar los datos previamente publicados.

La publicación inicial contiene solo datos reales de 2024, 2025 y el corte de
2026. El partido pendiente de 2024 conserva estado failed y no se rellena con
ceros. Los informes de demostración locales no se trasladan a la base remota.
