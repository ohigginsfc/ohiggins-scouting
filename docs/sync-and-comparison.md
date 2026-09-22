# Sincronización y comparación: contrato operativo

## Sincronización Sofascore

Una ejecución satisfactoria requiere salida JSON válida, al menos una competición revisada y cero errores en todas las competiciones. Un proceso que termina con código cero sin ese resumen no confirma una sincronización.

- Un calendario vacío o una página no disponible se informa como error; no se publica una consulta parcial como calendario completo.
- La consulta `--dry-run` no inicializa registros de partidos procesados.
- `pending_total` incluye `pending_import`: partidos descargados cuyo checkpoint aún debe importarse. Si falta el checkpoint, se informa el error y se debe recuperar el archivo o solicitar una recarga explícita.
- La actualización conserva la temporada utilizada en la consulta previa.
- El panel ejecuta el worker mediante Docker Compose. `DISABLE_SOFASCORE_UPDATE=1` bloquea esa acción. Estas condiciones son independientes de la disponibilidad del proveedor.

La disponibilidad se comprueba desde el transporte y entorno que ejecutarán el worker: una respuesta 403 del cliente HTTP no demuestra que la sesión normal de Chrome falle también. Las ligas configuradas deben corresponder a la temporada que se quiere cargar; las entradas existentes son principalmente de 2025.

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
SOFASCORE_FETCH_MODE=browser
DISABLE_SOFASCORE_UPDATE=0
```

Reiniciar Streamlit después de cambiar estas variables. El worker usa `sys.executable`, conserva las credenciales `DB_*` y fuerza la importación directa sin Docker. El modo Docker sigue siendo el predeterminado; este cambio no modifica el servidor.

Para una revisión acotada desde el entorno Python del proyecto:

```bash
python scripts/update_sofascore_incremental.py --only cl_primera_2025 --season 2025 --dry-run --json-summary
```

Quitar `--dry-run` permite descargar e importar esa liga, únicamente después de comprobar el destino `DB_*`.

`browser` utiliza Chrome/Selenium y consulta JSON desde la sesión del navegador, sin ejecutar primero el cliente HTTP. Requiere Chrome/Chromium; Selenium Manager resuelve ChromeDriver localmente si no hay rutas explícitas. `http` utiliza requests sin Chrome. Sin configurar la variable se conserva el flujo `auto`: HTTP y, ante errores recuperables, Selenium. Un 401, 403 o 429 en el transporte seleccionado se informa como error; no se publica como descarga vacía.

## Identificadores de Chile verificados en el navegador

El 22 de septiembre de 2026 se contrastó el selector de temporadas de la web de Sofascore (torneo 11653):

| Temporada | Identificador | Página |
| --- | --- | --- |
| 2024 | 57883 | https://www.sofascore.com/football/tournament/chile/primera-division/11653#id:57883 |
| 2025 | 71131 | https://www.sofascore.com/football/tournament/chile/primera-division/11653#id:71131 |
| 2026 | 88493 | https://www.sofascore.com/football/tournament/chile/primera-division/11653#id:88493 |

La configuración anterior etiquetaba 88493 como 2025 y 71131 como 2024. Se corrigen el worker, el selector histórico, el scraper y el seed ejecutable para conservar los años solicitados. Las migraciones antiguas se mantienen como historial; no se ha ejecutado una modificación de la base del club.

No reutilizar checkpoints ni publicaciones anteriores de esos ámbitos sin verificar su temporada: podrían estar etiquetados con un año incorrecto. Esta corrección no acredita que existan datos contaminados ni modifica registros existentes. Los demás torneos todavía requieren contrastar sus identificadores.

La validación local del modo `browser` recuperó el calendario de Chile 2025 (240 partidos finalizados), las estadísticas de 36 jugadores de O'Higgins–Ñublense (evento 13443447) y permitió importar 734 métricas en un esquema PostgreSQL de prueba aislado. Es una comprobación de descarga e importación de una muestra, no una carga completa de temporada ni una validación del servidor de producción.
