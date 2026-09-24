# Migrar los informes subjetivos del PostgreSQL antiguo a Supabase

La instalación anterior aloja PostgreSQL en el servicio `postgres` de
`docker-compose.ec2.yml`, con un volumen persistente
`ohiggins_scouting_postgres_data`. El dashboard antiguo muestra informes que no
están en Supabase. Esta operación copia **jugadores con informes, informes y
valoraciones por atributo** al esquema `scouting`; las métricas Sofascore
publicadas en Supabase permanecen en su sitio.

## 1. Exportar desde el servidor anterior

El administrador debe situarse en el checkout que usó para desplegar el
Compose anterior. Confirmar que el servicio `postgres` responde:

```bash
docker compose -f docker-compose.ec2.yml ps postgres
```

Si está detenido, arrancar **solo** ese servicio con
`docker compose -f docker-compose.ec2.yml start postgres`. No ejecutar
`down -v`, borrar el volumen ni restaurar nada sobre él. Crear un respaldo
privado de las tres tablas, conservando esquema, claves y datos:

```bash
umask 077
docker compose -f docker-compose.ec2.yml exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-acl \
  -t public.players -t public.scouting_reports -t public.report_attribute_ratings' \
  > scouting-informes-antiguos.dump
```

Verificar que el archivo no está vacío y enviarlo por un canal privado al
operador de la migración. Este respaldo contiene información de scouting del
club; no adjuntarlo a issues ni guardarlo en Git. Si algún `image_path` de los
jugadores apunta a archivos locales, exportar también esos archivos de `data/`
o las imágenes no aparecerán después de migrar las filas.

## 2. Restaurar en una base local desechable

Crear **otra base de datos** PostgreSQL en la máquina de trabajo y restaurar
allí el respaldo. Nunca restaurarlo directamente en Supabase ni en la base de
producción. Ejemplo con herramientas PostgreSQL instaladas localmente:

```bash
createdb -h 127.0.0.1 -U postgres scouting_legacy_staging
pg_restore -h 127.0.0.1 -U postgres -d scouting_legacy_staging \
  --no-owner --no-acl scouting-informes-antiguos.dump
```

Adaptar host, puerto y usuario a la instalación local. Comprobar los conteos de
`public.scouting_reports` y `public.report_attribute_ratings` en esta base.
`SCOUTING_LEGACY_DATABASE_URL` debe apuntar a ella; la migración abre la fuente
en transacción de **solo lectura**.

## 3. Previsualizar y aplicar

Configurar de forma privada `SCOUTING_LEGACY_DATABASE_URL` (base de staging),
`SCOUTING_DATABASE_URL` (rol dedicado de Supabase con `sslmode=require`) y
`DB_SCHEMA=scouting`. Ejecutar desde la raíz del checkout actualizado:

```bash
python scripts/migrate_legacy_reports.py
```

El comando sin `--apply` no escribe en Supabase. Muestra cantidad de informes,
valoraciones, jugadores nuevos y jugadores que coinciden por nombre normalizado.
Excluye los informes marcados explícitamente como datos de demostración por
`scripts/seed_demo_data.py`, aunque su `source_type` diga `manual`. El resumen
indica cuántos se excluyeron. Si no queda ningún informe real, se detiene;
revisar el respaldo antes de modificar el criterio.
Revisar también el número de `image_paths`; estas rutas pueden requerir copiar
los archivos correspondientes. Si hay un jugador con el mismo nombre normalizado
pero fecha de nacimiento distinta, se detiene para revisión de identidad.

Tras revisar la previsualización y guardar el respaldo de origen:

```bash
python scripts/migrate_legacy_reports.py --apply
```

La importación es una transacción: reutiliza jugadores de Supabase cuyo nombre
normalizado coincide, crea los ausentes, conserva los IDs originales de informes
y valoraciones, actualiza las secuencias y verifica los conteos. **Rechaza**
un destino que ya tenga informes subjetivos para no duplicarlos ni sobrescribir
trabajo nuevo. Es una migración única; no forma parte de la sincronización
semanal de Sofascore.

## 4. Comprobar el dashboard

Verificar en Supabase los conteos de `scouting.scouting_reports` y
`scouting.report_attribute_ratings`, y en el dashboard los jugadores scouteados,
informes activos/ocultos, scouts y el detalle de varias valoraciones. Comparar
los conteos de origen y destino. Mantener el respaldo del PostgreSQL antiguo y
sus archivos de imágenes hasta que el administrador valide la migración.
