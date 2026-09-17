# Scraper de estadísticas Sofascore

Recopila estadísticas agregadas por jugador de una temporada de liga vía la API pública de Sofascore (Selenium + Chrome).

Por defecto descarga **Chile Primera** (`tournament_id=11653`, `season_id=88493`) en `sofascore_output/`.

---

## Archivos generados

En el directorio indicado con `--output-dir`:

| Archivo | Contenido |
|---|---|
| `teams.json` | Equipos de la clasificación |
| `events.json` | Partidos de la temporada (filtrados a terminados para el scrape) |
| `player_stats.json` | Estadísticas agregadas por jugador (JSON) |
| `player_stats.csv` | Mismo contenido en tabla ancha |
| `checkpoint_raw.json` | Checkpoint cada 5 partidos (por si se interrumpe) |

---

## Requisitos

```bash
pip install -r requirements-scraper.txt
```

Incluye `selenium`, `requests` y **`curl_cffi`** (imprescindible para evitar `403 challenge` de Akamai en peticiones HTTP directas).

**Google Chrome** instalado en el sistema (ChromeDriver gestionado por Selenium). Selenium se usa como respaldo (XHR en contexto del navegador + GET del JSON en `<pre>`).

### Diagnóstico si standings/events salen vacíos

Sofascore puede responder `{"error": {"code": 403, "reason": "challenge"}}` en lugar de datos.

```bash
# Scraper con artefactos de depuración
cd web_scraping_sofascore
python3 sofascore_scraper.py --debug-fetch --tournament-id 155 --season-id 87913 --output-dir sofascore_output/ar_primera_2025
```

Revisa `web_scraping_sofascore/debug_sofascore/`:
- `last_response.txt` / `last_response.html` — cuerpo de la última respuesta
- `last_response_meta.json` — URL, content-type, tamaño, preview
- `screenshot.png` — captura del navegador (modo `--debug-fetch`)

Orden de fetch: **curl_cffi** → requests → **Selenium XHR** (tras abrir sofascore.com) → Selenium GET.

---

## Uso (CLI)

Desde `web_scraping_sofascore/`:

```bash
python3 sofascore_scraper.py --help
```

### Chile Primera (defaults)

Equivalente a ejecutar sin argumentos:

```bash
python3 sofascore_scraper.py
```

O explícito:

```bash
python3 sofascore_scraper.py \
  --tournament-id 11653 \
  --season-id 88493 \
  --output-dir sofascore_output/cl_primera_2025
```

### Chile Segunda

```bash
python3 sofascore_scraper.py \
  --tournament-id 1240 \
  --season-id 89007 \
  --output-dir sofascore_output/cl_segunda_2025
```

### Argentina Primera

```bash
python3 sofascore_scraper.py \
  --tournament-id 155 \
  --season-id 87913 \
  --output-dir sofascore_output/ar_primera_2025
```

### Argentina Segunda

```bash
python3 sofascore_scraper.py \
  --tournament-id 703 \
  --season-id 87940 \
  --output-dir sofascore_output/ar_segunda_2025
```

### Uruguay Primera

```bash
python3 sofascore_scraper.py \
  --tournament-id 278 \
  --season-id 89288 \
  --output-dir sofascore_output/uy_primera_2025
```

### Uruguay Segunda

```bash
python3 sofascore_scraper.py \
  --tournament-id 1908 \
  --season-id 91195 \
  --output-dir sofascore_output/uy_segunda_2025
```

---

## Argumentos

| Argumento | Default | Descripción |
|-----------|---------|-------------|
| `--tournament-id` | `11653` | ID del torneo en Sofascore |
| `--season-id` | `88493` | ID de la temporada |
| `--output-dir` | `sofascore_output` | Carpeta de salida |
| `--no-headless` | (headless activo) | Muestra la ventana de Chrome |
| `--delay-lineup` | `1.5` | Segundos tras peticiones de alineaciones |
| `--delay-events` | `1.5` | Segundos tras peticiones de partidos/clasificación |
| `--delay-details` | `1.0` | Segundos tras perfil de jugador |
| `--delay-fallback` | `1.0` | Segundos tras stats individuales (fallback) |
| `--debug-fetch` | desactivado | Guarda `debug_sofascore/`, logs DEBUG y `screenshot.png` |

---

## Integración con scouting-platform

El flujo habitual es el Dashboard (**Descargar datos reales** / **Buscar nuevos partidos**).

Manual (raíz del repo):

1. `scripts/stage_sofascore_output.py`
2. `python -m scouting.ingestion.import_sofascore_player_stats_csv` (en el contenedor `app` o worker)

---

## Fuente de datos

**Sofascore** — `https://www.sofascore.com`

Uso exclusivamente interno. Los IDs de torneo/temporada también están en `external_competitions` de la base de datos del proyecto.
