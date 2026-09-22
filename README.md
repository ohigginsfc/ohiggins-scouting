# Scouting Platform

Plataforma de scouting deportivo: informes subjetivos, estadísticas objetivas,
comparación entre temporadas y actualización de datos desde la interfaz.

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

Para recuperar Chile 2024/2025 desde GitHub Actions sin consultar Sofascore desde
el portátil, usar el [worker de recuperación cifrada](docs/sofascore-recovery.md).
Genera checkpoints reanudables y paquetes completos importables localmente;
no conecta Actions a PostgreSQL ni despliega en el servidor del club.

Con demo, el Dashboard ofrece **Descargar datos reales** (histórico 2024 + temporada activa).
Después: **Buscar nuevos partidos** (incremental, solo temporada activa).
Los demo se conservan y no se mezclan con datos reales.

## Variables

| Variable | Descripción |
|----------|-------------|
| `DB_*` | PostgreSQL |
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

## Despliegue EC2

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
