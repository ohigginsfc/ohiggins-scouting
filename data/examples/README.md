# Formatos de ingesta (referencia)

Esta carpeta **no** contiene datasets demo. Los datos objetivos reales entran por el pipeline Sofascore (`data/staging/sofascore/…`).

## Informes subjetivos (Excel)

Importar con:

```bash
docker compose exec app python -m scouting.ingestion.import_excel /ruta/a/tu_informes.xlsx
```

Columnas obligatorias y opcionales: ver sección **Formato del Excel de informes** en el `README.md` raíz.

## Valoraciones por atributo (CSV)

Tras existir un `scouting_reports` por jugador y fecha:

```bash
docker compose exec app python -m scouting.ingestion.import_attribute_ratings_csv /ruta/a/atributos.csv
```

## Métricas objetivas manuales (CSV)

Solo para fuentes **no Sofascore** y datos reales. Para ligas Sofascore usar el pipeline en README.

```bash
docker compose exec app python -m scouting.ingestion.import_objective_metrics_csv /ruta/a/metricas.csv
```
