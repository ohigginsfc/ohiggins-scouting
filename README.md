# Scouting Platform

Plataforma de scouting deportivo: informes subjetivos, estadísticas objetivas,
comparación entre temporadas y actualización de datos desde la interfaz.

## Base de datos y operación

La aplicación puede utilizar PostgreSQL local o PostgreSQL en Supabase. La base
remota utiliza el esquema `scouting` y una credencial propia; COMET conserva sus
tablas separadas. Supabase aloja los datos, no la aplicación Streamlit.

La conexión se selecciona al iniciar el proceso:

- `SCOUTING_DATABASE_URL` tiene prioridad sobre las variables `DB_*`.
- Para Supabase, configurar también `DB_SCHEMA=scouting` y `sslmode=require`
  en la conexión. Usar el Session pooler cuando se necesite conectividad IPv4.
- Fuera de Docker, la aplicación carga `.env` automáticamente. Un archivo como
  `.env.scouting-production` **no se carga por su nombre**: sus variables deben
  cargarse explícitamente en el entorno antes de iniciar Streamlit.
- Tener los datos publicados en Supabase no cambia la conexión de una aplicación
  que ya está ejecutándose. Tras cambiar el entorno, reiniciar Streamlit.

Consultar [configuración y permisos de Supabase](docs/supabase-scouting.md).
No versionar conexiones ni contraseñas.

### Cobertura publicada

La publicación remota verificada el 23 de septiembre de 2026 contiene únicamente
datos reales, con esta cobertura:

| Temporada | Partidos con estadísticas / esperados | Registros de métricas |
|-----------|--------------------------------------|-----------------------|
| 2024 | 239 / 240 | 18.353 |
| 2025 | 240 / 240 | 19.607 |
| 2026, corte del 22 de septiembre de 2026 a las 23:35 UTC | 183 / 183 | 21.419 |

El partido Unión La Calera–Cobresal de 2024 (`12021741`) sigue pendiente:
Sofascore devolvió 404 para sus alineaciones. No se sustituye por ceros; la
interfaz advierte la cobertura parcial. El corte de 2026 incluye partidos
finalizados al recogerlos, con inicio anterior al corte.

### Extracción y automatización

El worker Docker local ha permitido descargar datos con el cliente HTTP original
basado en `curl_cffi`, sin VPN en esa ejecución. En un runner alojado por GitHub,
la prueba del mismo código original y de la misma versión de `curl_cffi` recibió
403 tanto en la portada como en los dos hosts de la API, incluso continuando
después del fallo de la portada.

Docker reproduce el entorno de software, pero no la conexión de salida a
Internet. El origen de red es una hipótesis principal para esta diferencia;
las pruebas no demuestran que la IP sea la única causa.

- [Prueba HTTP desde GitHub Actions](https://github.com/ohigginsfc/ohiggins-scouting/actions/runs/35831454593): rechazada por el proveedor, sin escrituras en la BD.
- [Verificación de Supabase desde Actions](https://github.com/ohigginsfc/ohiggins-scouting/actions/runs/35829941551): conexión y lectura correctas.

**La sincronización semanal todavía no está activa.** Queda integrar y validar
el recorrido incremental de 2026 hasta su publicación atómica en Supabase y
programarlo en un entorno con acceso comprobado a Sofascore. Un runner propio
es una alternativa pendiente de configurar y probar. Los históricos 2024/2025
se conservan; no necesitan una descarga completa cada semana.

## Requisitos

- Docker
- Docker Compose v2

## Puesta en marcha

```bash
git clone <repositorio>
cd scouting-platform
cp .env.example .env
docker compose up -d --build
```

Docker Compose carga `.env` automáticamente; no es necesario ejecutar `source .env`
ni exportar variables a mano.

En `.env` configura solo secretos (`DB_PASSWORD`, usuario y hash de acceso).
En local **no** hace falta `HOST_PROJECT_ROOT`: Compose monta el directorio del proyecto.

Abrir: [http://localhost:8501](http://localhost:8501)

Al arrancar, `db-init` aplica migraciones, carga competiciones e inserta demo
si no hay datos reales (201 métricas 2024 + 424 de 2025).

Validar que app, db-init y postgres reciben la misma contraseña (solo hashes):

```bash
python scripts/check_compose_db_credentials.py
```

La UI fuerza **tema claro** vía `.streamlit/config.toml` (versionado). No depende del
modo claro/oscuro del sistema operativo ni del navegador.

## Datos demo y datos reales

El [worker de recuperación cifrada](docs/sofascore-recovery.md) permite intentar
la recuperación de Chile 2024/2025 y genera checkpoints reanudables y paquetes
completos importables localmente. Su extracción depende del acceso a Sofascore:
la prueba actual en runners alojados por GitHub devuelve 403. Este workflow de
recuperación no publica en PostgreSQL ni despliega la aplicación.

Con demo, el Dashboard ofrece **Descargar datos reales** (histórico 2024 + temporada activa).
Después: **Buscar nuevos partidos** (incremental, solo temporada activa).
Los demo se conservan y no se mezclan con datos reales.
Estos controles no implican que la sincronización semanal de 2026 ya esté
configurada o validada.

## Variables

| Variable | Descripción |
|----------|-------------|
| `DB_*` | PostgreSQL |
| `SCOUTING_DATABASE_URL` | Conexión PostgreSQL completa; tiene prioridad sobre `DB_*` |
| `DB_SCHEMA` | Esquema PostgreSQL; usar `scouting` para la base remota |
| `SCOUTING_USERNAME` / `SCOUTING_PASSWORD_HASH` | Acceso (hash bcrypt; cada `$` como `$$` en `.env`) |
| `SOFASCORE_ACTIVE_SEASON` | Temporada activa |
| `SOFASCORE_HISTORICAL_SEASON` | Temporada histórica |
| `SHOW_ADMIN_TAB` | `1` = pestaña Administración |
| `HOST_PROJECT_ROOT` | Opcional. Vacío = `.` (local). Ruta absoluta solo si el montaje debe apuntar a otro sitio. |

```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'TU_PASSWORD', bcrypt.gensalt()).decode())"
# Luego escapa cada '$' como '$$' al pegarlo en .env
```

### Contraseña PostgreSQL y volúmenes

`DB_PASSWORD` se aplica al **crear** el volumen PostgreSQL. Cambiarla en `.env`
después no actualiza automáticamente el rol.

- Desarrollo (borra datos locales): `docker compose down -v`
- Entorno con datos: `ALTER ROLE ... PASSWORD '...'` (no borrar el volumen)

Si el shell exporta `DB_PASSWORD` distinta a la de `.env`, Compose usa la del shell
para **todos** los servicios (app, db-init y postgres). Evita `export DB_PASSWORD=...`
salvo que sea intencional.

## Estructura

```
app/                      # Streamlit (UI)
src/scouting/             # Dominio, repositorios, servicios
db/                       # init.sql + migraciones
scripts/                  # init, seed, pipeline Sofascore
web_scraping_sofascore/   # Scraper (worker)
data/                     # Imágenes UI, ejemplos; runtime gitignored
docs/                     # Despliegue EC2
tests/
```

## Producción: dashboard conectado a Supabase

Servidor del club: [http://34.247.191.149:18501/](http://34.247.191.149:18501/).
Lucas debe ejecutar los siguientes pasos en ese servidor. El merge del repositorio
no actualiza por sí solo la web ni cambia su conexión.

### 1. Actualizar el código

Dentro del checkout existente, conservar el `.env` privado y comprobar que no hay
cambios locales pendientes antes de actualizar:

```bash
git status --short
git switch main
git pull --ff-only
```

Si aún no hay un checkout, clonarlo:

```bash
git clone https://github.com/ohigginsfc/ohiggins-scouting.git
cd ohiggins-scouting
```

### 2. Configurar el `.env` del servidor

Crear o editar `.env` en la raíz del checkout, manteniendo las credenciales de
acceso actuales del dashboard. Añadir o actualizar:

```dotenv
SCOUTING_DATABASE_URL='<conexion PostgreSQL privada del rol scouting_runtime con sslmode=require>'
DB_SCHEMA=scouting
SCOUTING_APP_PORT=18501
SCOUTING_USERNAME=<usuario del dashboard>
SCOUTING_PASSWORD_HASH='<hash bcrypt del dashboard; cada $ escapado como $$>'
```

Obtener la conexión del responsable del proyecto por un canal privado. Debe ser
la conexión **PostgreSQL Session pooler del rol dedicado a scouting**, no la URL
web de Supabase, una API key, ni una credencial administrativa de COMET. No pegar
estos valores en GitHub, issues, capturas o logs. El secret de Actions no se
transfiere automáticamente al servidor. El Compose inyecta `DB_SCHEMA=scouting`
y las temporadas 2026/2025 explícitamente.

```bash
chmod 600 .env
docker compose -f docker-compose.supabase.yml config -q
docker compose -f docker-compose.supabase.yml build app
```

### 3. Sustituir la instancia anterior

Identificar qué servicio ocupa el puerto 18501 y detener solo la instancia
anterior de scouting. Si se desplegó con el Compose EC2 de este repositorio,
ejecutar desde su checkout original (y con su mismo nombre de proyecto):

```bash
docker compose -f docker-compose.ec2.yml stop app
```

Si usa otro gestor o nombre de proyecto, detener esa instancia con su mecanismo
original. No borrar volúmenes ni ejecutar `down -v`: la BD anterior se conserva
como respaldo. Con el puerto libre, desde el checkout actualizado:

```bash
docker compose -f docker-compose.supabase.yml up -d app
docker compose -f docker-compose.supabase.yml ps
```

Este archivo es independiente: **no combinarlo con el Compose EC2 o local**.
Inicia Streamlit sin PostgreSQL local, migraciones ni seed demo. Mantiene la
descarga desde la interfaz desactivada mientras se valida la sincronización
incremental; la lectura y comparación de datos remotos están disponibles.

### 4. Verificar la conexión real

```bash
docker compose -f docker-compose.supabase.yml exec -T app python -c "from scouting.db import get_connection; c=get_connection(); c.execute('SET TRANSACTION READ ONLY'); print('schema, metrics:', c.execute('SELECT current_schema(), count(*) FROM objective_metrics').fetchone()); c.close()"
curl --fail http://127.0.0.1:18501/_stcore/health
```

La consulta debe mostrar `scouting` y actualmente 59.379 métricas; el conteo puede
cambiar tras nuevas publicaciones. El healthcheck debe responder `ok`, pero por
sí solo no valida la BD. Abrir la URL del servidor, iniciar sesión y comprobar
Dashboard y Comparación. La cobertura parcial de 2024 debe seguir visible.

Si la nueva instancia falla, detenerla con
`docker compose -f docker-compose.supabase.yml stop app` y volver a arrancar
la aplicación anterior con su configuración y gestor originales.

## Actualizar los datos desde una máquina local

La extracción manual se ejecuta en la máquina del operador con Docker Desktop
activo (o Docker Engine en Linux), no en el servidor web. Supabase puede seguir
sirviendo la última publicación mientras se prepara la siguiente. No hay que
activar una VPN por defecto: la descarga local anterior funcionó sin ella.

### Preparar y comprobar el worker

Actualizar el checkout local de `main`. Para las pruebas aisladas, configurar
en el `.env` privado `SOFASCORE_ARTIFACT_KEY`: una clave base64 de 32 bytes,
conservada entre ejecuciones para poder descifrar los checkpoints. Puede usarse
la copia privada existente; no regenerarla si ya hay paquetes que dependan de ella.

```bash
docker compose -f docker-compose.recovery.yml build collector
docker compose -f docker-compose.recovery.yml run --rm --entrypoint python collector scripts/test_selenium_runtime.py
docker compose -f docker-compose.recovery.yml run --rm collector run --mode probe --season 2025 --transport http --checkpoint new --output /app/data/recovery/probe-2025
```

El primer test comprueba Selenium sin consultar al proveedor. El segundo prueba
acceso real y debe mostrar `probe_ok: true`; no publica nada en PostgreSQL.
Este worker aislado no recibe credenciales de Supabase. Ante 401/403/429 detener
la extracción y conservar el checkpoint; un contenedor sano no garantiza acceso
a Sofascore.

### Recuperar un histórico solo cuando sea necesario

2024 y 2025 ya están publicados: no repetir su descarga completa para una
actualización ordinaria. Si hay que reconstruir 2025, el recolector versionado
permite comenzar y luego reanudar por lotes:

```bash
docker compose -f docker-compose.recovery.yml run --rm collector run --mode collect --season 2025 --transport http --checkpoint new --output /app/data/recovery/manual-2025
docker compose -f docker-compose.recovery.yml run --rm collector run --mode collect --season 2025 --transport http --input-package /app/data/recovery/manual-2025/recovery.sofa --output /app/data/recovery/manual-2025
```

Ejecutar el primer comando una sola vez; repetir el segundo mientras el estado
sea `partial`. El archivo persiste en `data/recovery/manual-2025/recovery.sofa`
del host. No usar `--refresh` para reanudar. Consultar la
[guía de recuperación](docs/sofascore-recovery.md) para validación y aplicación
en una BD local de prueba. Su opción `local --apply` **no publica en Supabase**.
Un paquete 2024 con el partido pendiente tampoco satisface la validación de
temporada completa de ese recolector.

### Actualización manual de 2026: paso pendiente de integrar

La descarga y publicación inicial de 2026 están realizadas, pero todavía no hay
un comando versionado y validado que repita de punta a punta la actualización
incremental hacia Supabase. Los scripts privados de recuperación inicial no se
distribuyen con un `git clone`. Antes de entregar este paso como operativo:

1. Configurar la temporada Sofascore `88493` del torneo `11653` y un ámbito
   explícito Chile/Primera/2026. El pipeline incremental actual configura Chile
   2025; pasar `--season 2026` no cambia por sí solo el ID remoto del torneo.
2. Incorporar el checkpoint completo del corte ya publicado. Descargar los
   partidos nuevos y volver a revisar una ventana reciente para correcciones;
   mantener los históricos y los partidos ya recogidos.
3. Validar IDs, temporada, cobertura y estadísticas; guardar un candidato
   completo y trazable. No sustituir una temporada por un CSV que solo contenga
   los partidos nuevos, ni asumir que el checksum del calendario detecta todos
   los cambios de estadísticas.
4. Respaldar el ámbito de destino y publicar métricas y estados de ingestión en
   una transacción con la credencial de `scouting`, conservando la publicación
   anterior si falla la validación o la importación.
5. Verificar la nueva cobertura, el lote de importación y las comparaciones del
   dashboard antes de dar la actualización por terminada.

Estos pasos describen el trabajo pendiente, no comandos ya habilitados. Hasta
validarlo, mantener `DISABLE_SOFASCORE_UPDATE=1` en producción y conservar el
corte existente. La programación semanal se decidirá después de disponer de una
actualización manual reproducible.

### Otras opciones de despliegue

Para producción con la BD existente en Supabase, utilizar
[`docker-compose.supabase.yml`](docker-compose.supabase.yml) y seguir la
[guía de despliegue con Supabase](docs/supabase-scouting.md).

Para una instalación con PostgreSQL propio en el servidor:

[`docs/ec2-deployment.md`](docs/ec2-deployment.md) · `docker-compose.ec2.yml`

## Pruebas

La imagen runtime de `app` no incluye pytest. Ejecuta la suite con el servicio
opcional `test` (profile `test`):

```bash
docker compose --profile test run --rm --build test
```

## Comprobar Selenium (worker)

```bash
docker compose --profile worker build sofascore-worker
docker compose --profile worker run --rm sofascore-worker \
  python scripts/test_selenium_runtime.py
```

## Pruebas de integridad de importación

Consultar [atomicidad y validación PostgreSQL](docs/atomic-import-review.md) para
ejecutar los escenarios de fallo y revisar el alcance de la protección del
importador. La integración requiere una base local desechable explícita; las
pruebas no utilizan las credenciales de producción.
