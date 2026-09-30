# COMET · Seguimiento deportivo (solicitud de Pablo)

Siete pantallas nuevas dentro del módulo COMET del portal unificado, solo para el rol **Admin**.
Las cinco pantallas anteriores (Resumen ejecutivo, Desarrollo juvenil, Rendimiento competitivo,
Análisis de jugadores y Estructura del plantel) no cambian. Scout sigue sin acceso a COMET.

| Pantalla | Qué resuelve |
|---|---|
| **Partido semanal** | Planilla completa de cada partido de la semana |
| **Rankings por categoría** | Minutos, goles, tarjetas y partidos ganados con el jugador en cancha |
| **Ficha del jugador** | Perfil, historial, categoría vs edad, evolución de minutos, marcas y períodos de selección |
| **Indicadores** | Participación, victorias, edad, antigüedad, minutos de jugadores más chicos, partidos por rol, disciplina y goles |
| **Alertas** | Las cuatro alertas automáticas, con color |
| **Jugadores adelantados** | Quienes juegan en categorías superiores a su edad |
| **Seguimiento y configuración** | Reglas y pendientes, alertas y colores, marcas y períodos, resumen semanal, calidad de datos |

Capturas de cada pantalla (datos ficticios) en [`comet-seguimiento/capturas`](comet-seguimiento/capturas).

## Regla de oro: nada inventado ni ocultado

* **Un dato que falta se ve como «—», nunca como 0.** Un 0 solo aparece cuando es cierto (por ejemplo, los minutos de un suplente que no ingresó).
* **Ninguna regla supuesta se presenta como aprobada por Pablo.** Cada regla tiene origen (`pablo` o `supuesto`) y las pantallas
  que dependen de un supuesto muestran un aviso «Criterios provisionales» con la etiqueta *Supuesto: pendiente de confirmar*.
  Solo pasan a *Confirmada por el club* cuando un administrador lo marca en Seguimiento y configuración.
* **Sin datos reales en el repositorio.** Las pruebas y las capturas usan datos ficticios (`scripts/comet_demo_data.py`).

## Cobertura de la solicitud

Estado: ✅ implementado · 🟠 implementado con una regla provisional (pendiente de confirmar) · ⛔ no posible con los datos actuales de COMET.

### Partido semanal

| Requisito | Estado | Dónde / cómo |
|---|---|---|
| Competición, categoría, fecha y rival | ✅ | Tabla de la semana y cabecera del partido |
| Local / visita y resultado | ✅ | Marcador final = fase «Segundo tiempo», la misma definición que ya usa `comet_dashboard` |
| Jugadores titulares | ✅ | Bloque *Titulares* |
| Suplentes que ingresaron | ✅ | Bloque *Suplentes que ingresaron* |
| Suplentes que no ingresaron | ✅* | Bloque propio. *Requiere que COMET entregue a los suplentes sin ingresar; el control de calidad avisa si no lo hace |
| No citados que no participaron | 🟠 | Referencial: figuran en otra planilla de la misma competición. No se conoce a quien nunca fue citado |
| Minutos jugados por jugador | ✅ | Columna *Minutos* |
| Goles y tarjetas amarillas / rojas | ✅ | Columnas por jugador |
| Goles recibidos por arquero | ✅ | Bloque *Goles recibidos por arquero* |
| Resultado con el jugador en cancha | 🟠 | Resultado final del partido en que el jugador sumó al menos el mínimo de minutos (por defecto 1) |

### Ranking por categoría

Minutos jugados ✅ · Goles ✅ · Tarjetas amarillas y rojas ✅ · Partidos ganados con el jugador en cancha 🟠.
Filtro por temporada y categoría; los empates comparten posición; quien no tiene datos o está en 0 no entra.

### Información individual

Perfil con datos personales y deportivos ✅ (nombre, nacimiento, edad, nacionalidad, nivel y estado; ver dependencias) ·
Historial de minutos, partidos, goles y tarjetas ✅ · Categoría en que juega vs categoría por edad 🟠 ·
Evolución de minutos por mes o semestre ✅ (solo períodos con partidos; un mes sin partidos no se dibuja como 0).

### Indicadores

| Indicador | Estado |
|---|---|
| % de participación (minutos jugados / minutos posibles) | 🟠 |
| % de victorias con el jugador en cancha | 🟠 |
| Promedio de edad por categoría | 🟠 (depende de la fecha de corte) |
| Promedio de antigüedad por categoría | 🟠 (mínimo: desde el primer partido registrado) |
| Relación edad y categoría actual | 🟠 |
| Minutos totales de la serie y de jugadores 1, 2 y 3 años menores | 🟠 (se agrega «4 o más» para que cuadre el total) |
| Partidos por jugador: titular, suplente que ingresó, solo citación | ✅ |
| Amarillas y rojas | ✅ |
| Goles marcados y goles recibidos por arqueros | ✅ |

### Alertas y seguimiento

| Requisito | Estado | Detalle |
|---|---|---|
| Jugador con 4 amarillas | 🟠 | Alerta con 4 **o más**, dentro de cada competición (ciclo pendiente) |
| Menos del 20 % de los minutos posibles | 🟠 | Estrictamente menor que 20 %, sobre la categoría principal de la temporada |
| Jugando en categorías superiores | 🟠 | Con minutos en una categoría superior a la que le corresponde por edad |
| Más de 2 temporadas sin promoción | 🟠 | 3 o más temporadas seguidas en la misma categoría, según el historial disponible; un hueco de temporadas corta el conteo |
| Adelantados: quiénes, minutos, % por categoría, permanencia, comparación con su grupo de edad | 🟠 | Pantalla *Jugadores adelantados* |
| Configurar alertas y colores | ✅ | Umbral, activación y color por alerta (el nombre siempre acompaña al color) |
| Resúmenes y alertas semanales | 🟠 | Vista previa y descarga en pantalla; script `scripts/send_comet_weekly_digest.py`. **No hay envío programado ni activado** |
| Jugadores proyectados o de selección | ✅ | Desde la ficha del jugador |
| Períodos de microciclo, Sudamericano o Mundial | ✅ | Desde la ficha; opcionalmente descuentan minutos posibles (regla apagada por defecto) |

Marcas, períodos y reglas se guardan en Supabase y **requieren aplicar la migración 003** (ver más abajo).
Sin ella las pantallas funcionan con los valores por defecto y en solo lectura.

## Reglas y preguntas pendientes para Pablo

Estas son las siete cosas que el documento pedía confirmar. Cada una tiene un criterio provisional ya aplicado,
visible en pantalla, y se cambia o se confirma desde *Seguimiento y configuración → Reglas y pendientes*.

| # | Pregunta en lenguaje sencillo | Criterio provisional |
|---|---|---|
| 1 | Cuando dicen «resultado con el jugador en cancha», ¿es el resultado final del partido en que jugó (aunque haya entrado a los 85') o el marcador mientras estuvo dentro? | Resultado final del partido en que sumó al menos 1 minuto. Lo segundo necesita el minuto de goles y cambios, que COMET no entrega |
| 2 | ¿Qué partidos cuentan como «minutos posibles»? ¿Todos los de la serie o solo desde que el jugador llegó? ¿Entran amistosos y copas? ¿Cuánto dura un partido en cada categoría? | Todos los partidos ya jugados de la competición donde el jugador fue citado; duración = el minuto más largo registrado en ese partido (sin minutos registrados, el partido no cuenta) |
| 3 | ¿De dónde sale la lista oficial del plantel de cada serie para saber quién no fue citado? | Quienes figuran en otra planilla de la misma competición |
| 4 | ¿A qué fecha se mide la edad para decir en qué categoría le corresponde jugar a un jugador? ¿Un jugador de 14 años en U-15 es «adelantado»? | 31 de diciembre del año de la temporada; la categoría por edad es la U-N más pequeña cuyo tope alcanza para su edad |
| 5 | ¿La antigüedad es desde que entró al club? ¿Qué es «promoción»: subir de serie al año siguiente o también jugar partidos en la superior? ¿U-19 y Primer Equipo entran en la alerta? | Antigüedad = desde el primer partido registrado (es un mínimo). Promoción = la categoría principal de la temporada es mayor que la del año anterior; Primer Equipo no se evalúa |
| 6 | ¿Las amarillas se acumulan por campeonato o por temporada? ¿Se borran al cumplir una fecha de suspensión? ¿La doble amarilla cuenta? | Por competición, solo amarilla simple, sin descontar suspensiones |
| 7 | ¿Quiénes reciben el resumen semanal, qué día y a qué hora? Incluye nombres de menores: ¿se puede enviar por correo? | Sin destinatarios: no se envía nada |

## Datos que debería aportar el pipeline de COMET

No se modifica `dataProject`. Esta lista también está en *Seguimiento y configuración → Calidad de datos y dependencias*.

| Dato que falta | Para qué | Qué se hace hoy |
|---|---|---|
| Citación completa (incluidos suplentes que no ingresaron) | Suplentes que no ingresaron, «solo citación» | Se usan las filas marcadas como que no jugaron; si no vienen, quedan vacías y el control de calidad lo avisa |
| Plantel oficial por categoría y temporada | No citados; minutos posibles exactos | Referencial por planillas |
| Minuto de cada gol, tarjeta y cambio | Marcador mientras el jugador estuvo en cancha | Resultado final del partido |
| Fecha de ingreso al club | Antigüedad real | Desde el primer partido registrado |
| Historial de categorías anterior al primer año disponible | Temporadas sin promoción | Solo el historial que hay; el aviso indica desde qué año |
| Duración por categoría y estado del partido (suspendido, W.O.) | Minutos posibles | Minuto más largo registrado |
| Doble amarilla, expulsión por acumulación, suspensiones cumplidas | Ciclo de tarjetas | Solo amarilla simple |
| Ficha ampliada (posición, pie, estatura, peso) | Perfil deportivo | Nombre, nacimiento, nacionalidad, nivel y estado |
| Autogoles diferenciados | Goles por jugador vs marcador | El control de calidad avisa si no suman |

## Seguridad y datos

* **Permisos.** Todas las funciones nuevas (carga de datos, contexto y pantallas) llevan `@admin_only` **por fuera de la caché**, igual que `comet_dashboard`:
  un resultado en caché no se entrega a quien no sea Admin. `portal.py` sigue llamando `require_admin()` antes de importar nada de COMET.
  Las pruebas lo verifican por cada función, con Scout y sin sesión, y comprueban que no se abre ninguna conexión.
* **COMET solo se lee**, con el rol `comet_reader` existente (solo `SELECT`). Las consultas usan únicamente columnas que ya consultan las pantallas actuales y piden solo las filas
  de O'Higgins y los jugadores de sus planillas (minimización de datos de menores). No se cruza con scouting.
* **La configuración vive en el esquema privado `portal`** (nunca en `public`), con la conexión `portal_runtime` que ya usan las cuentas.
  Cada escritura registra quién y cuándo. No hay `DELETE`: marcas y períodos se desactivan y conservan su historial.
* **Sin secretos.** Nada de contraseñas, `.env` ni datos reales en el repositorio; el correo se configura por variables de entorno.

### Migración `db/portal/003_comet_followup.sql` (no aplicada)

Crea `portal.comet_settings`, `portal.comet_player_marks` y `portal.comet_selection_periods`, con RLS y permisos solo para `portal_runtime`
(nada para `anon`, `authenticated`, `scouting_runtime` ni `comet_reader`). Es idempotente. **Debe aplicarla el propietario de la BD después de revisarla**,
igual que `001` y `002`; esta PR no la aplica ni cambia producción. Reversión: no borrar esquemas; basta dejar de usar las pantallas (las tablas no afectan otras funciones).

## Resumen semanal por correo

`scripts/send_comet_weekly_digest.py` genera el resumen (partidos de la semana anterior, goleadores, tarjetas, goles recibidos y alertas vigentes).
**Por defecto solo muestra una vista previa.** Con `--send` envía únicamente si: (1) la regla de destinatarios tiene correos y está *confirmada por el club*,
(2) hay servicio de correo (`COMET_DIGEST_SMTP_HOST` y `COMET_DIGEST_SMTP_FROM`; la clave solo por entorno) y (3) se pasó `--send`. Si falta algo, sale con código 2 sin enviar.

```bash
docker compose --env-file .env.portal -f docker-compose.portal.yml run --rm portal \
  python scripts/send_comet_weekly_digest.py --week-of 2026-09-21
```

No está programado en ningún lado. Cuando Pablo confirme destinatarios, día y hora, se programa con el planificador del servidor (por ejemplo, `cron` los lunes) pasando además las variables `COMET_DIGEST_SMTP_*`.
El resumen contiene nombres de menores: confirmar antes que el club autoriza su envío por correo.

## Cómo revisar

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt     # Windows; en Linux: .venv/bin/pip
PYTHONPATH=src python -m pytest -q                                            # con SCOUTING_TEST_DATABASE_URL las pruebas SQL también corren
PYTHONPATH=src streamlit run scripts/demo_comet_followup.py --server.address=127.0.0.1
```

La demostración usa datos ficticios y un almacén en memoria, no lee variables de conexión y se niega a arrancar si detecta credenciales en el entorno o si no escucha solo en el equipo local.

Comprobación de accesos con el portal real: Admin ve las doce secciones de COMET; Scout solo ve el módulo *Scouting* (`tests/test_comet_security.py` lo verifica contra el enrutador real, con estado y URL manipulados).

## Estructura

| Ruta | Contenido |
|---|---|
| `src/scouting/comet/` | Cálculos puros: categorías, reglas, datos, métricas, alertas, indicadores, adelantados, calidad, resumen, correo, consultas y almacén de configuración |
| `app/comet_context.py` | Carga de datos y contexto con permisos y caché |
| `app/comet_followup.py`, `app/comet_insights.py` | Las siete pantallas |
| `app/ui/comet_widgets.py` | Formato «—», etiquetas de estado, colores accesibles |
| `db/portal/003_comet_followup.sql` | Migración de configuración (no aplicada) |
| `scripts/send_comet_weekly_digest.py` | Resumen semanal (vista previa por defecto) |
| `scripts/comet_demo_*.py`, `scripts/demo_comet_followup.py` | Datos ficticios y demostración local |
| `tests/test_comet_*.py`, `tests/comet_tiny.py` | Pruebas (cálculos a mano, seguridad, pantallas, SQL y migración) |

## Hallazgos que no se tocaron

* `get_squad_by_age_category` (`comet_dashboard.py`) asigna categorías con rangos de edad que se solapan (15 aparece en U-16 y U-15; 14 en U-15 y U-13) y nunca devuelve U-14. Las pantallas nuevas no lo usan; se dejó intacto para no cambiar funciones existentes.
* Las pantallas nuevas no muestran ni cruzan datos de Sofascore.
