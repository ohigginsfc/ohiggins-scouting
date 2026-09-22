# Sincronización y comparación: contrato operativo

## Sincronización Sofascore

Una ejecución satisfactoria requiere salida JSON válida, al menos una competición revisada y cero errores en todas las competiciones. Un proceso que termina con código cero sin ese resumen no confirma una sincronización.

- Un calendario vacío o una página no disponible se informa como error; no se publica una consulta parcial como calendario completo.
- La consulta `--dry-run` no inicializa registros de partidos procesados.
- `pending_total` incluye `pending_import`: partidos descargados cuyo checkpoint aún debe importarse. Si falta el checkpoint, se informa el error y se debe recuperar el archivo o solicitar una recarga explícita.
- La actualización conserva la temporada utilizada en la consulta previa.
- El panel ejecuta el worker mediante Docker Compose. `DISABLE_SOFASCORE_UPDATE=1` bloquea esa acción. Estas condiciones son independientes de la disponibilidad del proveedor.

Un HTTP 403 del proveedor requiere resolver el acceso permitido desde el entorno de ejecución. Estos cambios no evitan restricciones de acceso ni acreditan una descarga real. Las ligas configuradas deben corresponder a la temporada que se quiere cargar; las entradas existentes son principalmente de 2025.

## Ranking frente a la cohorte

El puesto 1 representa el mejor valor según la dirección registrada para cada métrica. Los empates comparten puesto. El denominador del puesto incluye el registro del jugador evaluado; el mínimo de muestra sigue contando jugadores pares distintos.

Una observación corresponde a jugador, temporada, competición y métrica. Se colapsan duplicados idénticos y se excluyen observaciones con valores contradictorios o no finitos. Solo se comparan unidades coincidentes. Si la cohorte combina temporadas o ligas, el ranking se identifica como ranking de registros jugador/temporada/liga, no de jugadores únicos.

El percentil de rendimiento mantiene la inversión de métricas negativas en la capa de servicio. Estas reglas afectan al ranking y percentil de posición; no certifican todas las medias, enlaces de identidad o comparaciones históricas del sistema.

## Validación

`python -m pytest -q` ejecuta las regresiones de sincronización y ranking. Las pruebas PostgreSQL requieren `SCOUTING_TEST_DATABASE_URL` apuntando a una base local desechable llamada `scouting_test`; nunca usan las credenciales operativas del panel.

## Ejecución local sin Docker

El panel y el worker pueden compartir el mismo entorno Python y la base PostgreSQL local. En el `.env` local:

```dotenv
SOFASCORE_WORKER_MODE=local
SOFASCORE_IMPORT_MODE=direct
SOFASCORE_FETCH_MODE=http
DISABLE_SOFASCORE_UPDATE=0
```

Reiniciar Streamlit después de cambiar estas variables. El worker usa `sys.executable`, conserva las credenciales `DB_*` y fuerza la importación directa sin Docker. El modo Docker sigue siendo el predeterminado; este cambio no modifica el servidor.

Para una revisión acotada desde el entorno Python del proyecto:

```bash
python scripts/update_sofascore_incremental.py --only cl_primera_2025 --season 2025 --dry-run --json-summary
```

Quitar `--dry-run` permite descargar e importar esa liga, únicamente después de comprobar el destino `DB_*`. El modo HTTP no necesita Chrome: informa los errores HTTP del proveedor y no intenta eludirlos usando otros mecanismos de acceso. Un error 403 o 429 impide confirmar sincronización aunque PostgreSQL esté disponible.
