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
* **Un total con un sumando desconocido es desconocido.** Si COMET no trae los minutos de un partido en que el jugador jugó, sus minutos y su participación
  se ven como «—»; no se muestra la suma de los demás partidos como si fuera el total (ver *Minutos desconocidos* más abajo).
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
| Goles y tarjetas amarillas / rojas | ✅ | Columnas por jugador, más *2.ª amarilla* (`secondyellow`) y *Autogoles* (`owngoals`), que existen en COMET y se muestran aparte |
| Goles recibidos por arquero | ✅ | Bloque *Goles recibidos por arquero* |
| Filas repetidas jugador/partido | ✅ | Idénticas: se cuenta una. Contradictorias: no se elige ninguna, el partido lo avisa y el jugador queda con cifras incompletas |
| Resultado con el jugador en cancha | 🟠 | Resultado final del partido en que el jugador sumó al menos el mínimo de minutos (por defecto 1) |

### Ranking por categoría

Minutos jugados ✅ · Goles ✅ · Tarjetas amarillas y rojas ✅ · Partidos ganados con el jugador en cancha 🟠.
Filtro por temporada y categoría; los empates comparten posición; quien no tiene datos o está en 0 no entra.
Los jugadores con planillas contradictorias (ver más abajo) no entran y se listan en un aviso.
El ranking de minutos tampoco incluye a quien tiene algún partido sin minutos conocidos (se lista en un aviso): goles y tarjetas sí cuentan en sus rankings.

### Información individual

Perfil con datos personales y deportivos ✅ (nombre, nacimiento, edad por aniversario, nacionalidad, nivel, estado, `datefrom`, estatura y peso
con cobertura parcial: lo que falta se ve como «—», sin convertir unidades) ·
Historial de minutos, partidos, goles y tarjetas ✅ · Categoría en que juega vs categoría por edad 🟠 ·
Evolución de minutos por mes o semestre ✅ (solo períodos con partidos; un mes sin partidos no se dibuja como 0).

### Indicadores

| Indicador | Estado |
|---|---|
| % de participación (minutos jugados / minutos posibles) | 🟠 (numerador y denominador salen del mismo conjunto de partidos; el porcentaje no se redondea antes de compararlo con un umbral; la participación de una serie deja fuera, en numerador y denominador, a quien tiene partidos sin minutos conocidos) |
| % de victorias con el jugador en cancha | 🟠 |
| Promedio de edad por categoría | 🟠 (depende de la fecha de corte) |
| Promedio de antigüedad por categoría | 🟠 (por defecto desde el primer partido registrado, que es un mínimo; la regla permite usar `datefrom`, sin dato si falta) |
| Relación edad y categoría actual | 🟠 |
| Minutos totales de la serie y de jugadores 1, 2 y 3 años menores | 🟠 (se agrega «4 o más» para que cuadre el total) |
| Partidos por jugador: titular, suplente que ingresó, solo citación | ✅ |
| Amarillas y rojas | ✅ |
| Goles marcados y goles recibidos por arqueros | ✅ |

### Alertas y seguimiento

| Requisito | Estado | Detalle |
|---|---|---|
| Jugador con 4 amarillas | 🟠 | Alerta con 4 **o más**, dentro de cada competición (ciclo pendiente). Las segundas amarillas se avisan en el detalle pero no se suman |
| Menos del 20 % de los minutos posibles | 🟠 | Estrictamente menor que 20 %, comparando minutos × 100 con umbral × posibles (1199 de 6000 = 19,98 % alerta; 1200 no), sobre la categoría principal de la temporada. Quien tiene algún partido sin minutos conocidos no se evalúa (se lista aparte) |
| Jugando en categorías superiores | 🟠 | Con minutos en una categoría superior a la que le corresponde por edad |
| Más de 2 temporadas sin promoción | 🟠 | 3 o más temporadas seguidas en la misma categoría, según el historial disponible; un hueco de temporadas corta el conteo |
| Adelantados: quiénes, minutos, % por categoría, permanencia, comparación con su grupo de edad | 🟠 | Pantalla *Jugadores adelantados* |
| Configurar alertas y colores | ✅ | Umbral, activación y color por alerta (el nombre siempre acompaña al color) |
| Resúmenes y alertas semanales | 🟠 | Vista previa y descarga en pantalla; script `scripts/send_comet_weekly_digest.py` con el mismo cálculo que las pantallas y registro de entregas. **No hay envío programado ni activado** |
| Jugadores proyectados o de selección | ✅ | Desde la ficha del jugador |
| Períodos de microciclo, Sudamericano o Mundial | ✅ | Desde la ficha; opcionalmente descuentan minutos posibles solo de partidos que el jugador no jugó (regla apagada por defecto) |

Marcas, períodos y reglas se guardan en Supabase y **requieren aplicar la migración 003** (ver más abajo).
Sin ella las pantallas funcionan con los valores por defecto y en solo lectura.

## Reglas y preguntas pendientes para Pablo

Estas son las siete cosas que el documento pedía confirmar. Cada una tiene un criterio provisional ya aplicado,
visible en pantalla, y se cambia o se confirma desde *Seguimiento y configuración → Reglas y pendientes*.

| # | Pregunta en lenguaje sencillo | Criterio provisional |
|---|---|---|
| 1 | Cuando dicen «resultado con el jugador en cancha», ¿es el resultado final del partido en que jugó (aunque haya entrado a los 85') o el marcador mientras estuvo dentro? | Resultado final del partido en que sumó al menos 1 minuto. Lo segundo necesita el minuto de goles y cambios: podría estar en la tabla `eventos_partido`, a la que el lector del portal aún no tiene acceso (falta una revisión autorizada de su contenido) |
| 2 | ¿Qué partidos cuentan como «minutos posibles»? ¿Todos los de la serie o solo desde que el jugador llegó? ¿Entran amistosos y copas? ¿Sirve la duración reglamentaria (`matchlength`) o los minutos realmente jugados? ¿Qué estados de partido (`matchstatus`) no cuentan? | Todos los partidos ya jugados de la competición donde el jugador fue citado; duración = el minuto más largo registrado (regla elegible: nominal); sin el dato elegido el partido no cuenta; estados excluidos: ninguno |
| 3 | ¿De dónde sale la lista oficial del plantel de cada serie para saber quién no fue citado? | Quienes figuran en otra planilla de la misma competición |
| 4 | ¿A qué fecha se mide la edad para decir en qué categoría le corresponde jugar a un jugador? ¿Un jugador de 14 años en U-15 es «adelantado»? | 31 de diciembre del año de la temporada; la categoría por edad es la U-N más pequeña cuyo tope alcanza para su edad |
| 5 | ¿La antigüedad es desde que entró al club? La ficha trae `datefrom` para la mayoría: ¿es la fecha de ingreso? ¿Qué es «promoción»: subir de serie al año siguiente o también jugar partidos en la superior? ¿U-19 y Primer Equipo entran en la alerta? | Antigüedad = desde el primer partido registrado (un mínimo; la regla permite `datefrom`). Promoción = la categoría principal de la temporada es mayor que la del año anterior; Primer Equipo no se evalúa |
| 6 | ¿Las amarillas se acumulan por campeonato o por temporada? ¿Se borran al cumplir una fecha de suspensión? ¿La segunda amarilla (`secondyellow`) cuenta como una o como dos amarillas? | Por competición; las segundas amarillas se muestran y se avisan, pero no se suman; sin descontar suspensiones |
| 7 | ¿Quiénes reciben el resumen semanal, qué día y a qué hora? Incluye nombres de menores: ¿se puede enviar por correo? | Sin destinatarios: no se envía nada |

## Datos de COMET: qué se usa, qué hay que confirmar y qué falta

No se modifica `dataProject` ni se conceden permisos. Esta tabla también está en *Seguimiento y configuración → Calidad de datos y dependencias*.
Ninguna fila dice que un dato «falta» sin haberlo comprobado: un dato sin acceso no es un dato ausente.

| Dato | Estado | Para qué | Qué se hace hoy |
|---|---|---|---|
| Citación completa (con suplentes que no ingresaron) | No disponible en los datos leídos | Suplentes que no ingresaron, «solo citación» | Se usan las filas marcadas como que no jugaron; si no vienen, quedan vacías y el control de calidad lo avisa |
| Plantel oficial por categoría y temporada | No disponible en los datos leídos | No citados; minutos posibles exactos | Referencial por planillas |
| Cronología del partido: tabla `eventos_partido` | Sin acceso del lector del portal | Marcador mientras el jugador estuvo en cancha | La tabla existe; no se comprobó su contenido ni se concedieron permisos. Falta una inspección autorizada. Mientras tanto, resultado final del partido |
| `jugadores.datefrom` | Existe: significado por confirmar | Antigüedad en el club | La mayoría de las fichas la trae. Por defecto la antigüedad cuenta desde el primer partido; la regla permite `datefrom` (sin dato si falta, sin sustituirla) |
| Historial de categorías anterior al primer año leído | No disponible en los datos leídos | Temporadas sin promoción | La muestra leída llega a 2025-2026: la alerta no puede certificarse con ese horizonte |
| `competiciones.matchlength` y `partidos.matchstatus` | Existe: significado por confirmar | Minutos posibles | Se leen. Duración registrada y nominal difieren en algunos partidos y ninguna es «la correcta» por sí sola: una regla elige la fuente y otra excluye estados. Falta contrastar con el club |
| `actuaciones_jugadores.secondyellow` | Existe: en uso | Ciclo de tarjetas | Se muestra y se avisa en la alerta; no se suma. Falta definir cómo cuenta y las suspensiones cumplidas |
| `actuaciones_jugadores.owngoals` | Existe: en uso | Goles por jugador vs marcador | Se muestra aparte; no cuenta como gol a favor. Las filas son solo de O'Higgins |
| Estatura y peso del jugador | Existe: en uso (cobertura parcial) | Perfil deportivo | Se muestran con «—» cuando faltan y sin convertir unidades. Posición y pie hábil no figuran en las columnas leídas |

Las columnas opcionales se piden solo si `information_schema` dice que existen; si falta alguna, llega como dato ausente y la pantalla no se rompe.
Los nombres de estatura y peso se buscan entre `height`/`heightcm`/`estatura`/`altura` y `weight`/`weightkg`/`peso`; si COMET usa otros, hay que añadirlos a `HEIGHT_CANDIDATES`/`WEIGHT_CANDIDATES` en `queries.py`.

## Seguridad y datos

* **Permisos.** Todas las funciones nuevas (carga de datos, contexto y pantallas) llevan `@admin_only` **por fuera de la caché**, igual que `comet_dashboard`:
  un resultado en caché no se entrega a quien no sea Admin. `portal.py` sigue llamando `require_admin()` antes de importar nada de COMET.
  Las pruebas lo verifican por cada función, con Scout y sin sesión, y comprueban que no se abre ninguna conexión.
* **COMET solo se lee**, con el rol `comet_reader` existente (solo `SELECT`). Las consultas piden las columnas que ya consultan las pantallas actuales, más las opcionales
  que `information_schema` confirma (solo de las cinco tablas que el portal usa), y solo las filas de O'Higgins y los jugadores de sus planillas
  (minimización de datos de menores). No se concede ningún permiso nuevo. No se cruza con scouting.
* **La configuración vive en el esquema privado `portal`** (nunca en `public`), con la conexión `portal_runtime` que ya usan las cuentas.
  Cada fila guarda el **último** autor y fecha; las reglas y marcas se actualizan en el lugar, así que **no son una auditoría histórica completa**
  (no conservan versiones anteriores). No hay `DELETE`: marcas y períodos se desactivan (el retiro de un período registra quién y cuándo).
* **Sin secretos.** Nada de contraseñas, `.env` ni datos reales en el repositorio; el correo se configura por variables de entorno.

### Migración `db/portal/003_comet_followup.sql` (no aplicada)

Crea `portal.comet_settings`, `portal.comet_player_marks`, `portal.comet_selection_periods` y `portal.comet_digest_deliveries` (registro de entregas del resumen semanal), con RLS y permisos solo para `portal_runtime`
(nada para `anon`, `authenticated`, `scouting_runtime` ni `comet_reader`). Es idempotente. **Debe aplicarla el propietario de la BD después de revisarla**,
igual que `001` y `002`; esta PR no la aplica ni cambia producción. Reversión: no borrar esquemas; basta dejar de usar las pantallas (las tablas no afectan otras funciones).

## Resumen semanal por correo

`scripts/send_comet_weekly_digest.py` genera el resumen (partidos de la semana anterior, goleadores, tarjetas, goles recibidos y alertas vigentes).
**Por defecto solo muestra una vista previa.** Usa el mismo cálculo que las pantallas (`scouting.comet.pipeline`): mismas reglas, mismos períodos de selección
y mismas alertas, así que el correo y la pantalla no pueden discrepar para la misma semana.

Con `--send` envía únicamente si: (1) la regla de destinatarios tiene correos y está *confirmada por el club*,
(2) hay servicio de correo (`COMET_DIGEST_SMTP_HOST` y `COMET_DIGEST_SMTP_FROM`; la clave solo por entorno), (3) hay registro de entregas
(`PORTAL_AUTH_DATABASE_URL` con la migración 003) y (4) se pasó `--send`. Si falta algo, sale con código 2 sin enviar.

**Como mucho una entrega por semana y destinatario.** Cada correo se reserva en `portal.comet_digest_deliveries` (clave primaria semana + destinatario, `INSERT` atómico)
*antes* de enviarse. Dos ejecuciones de la misma semana no lo repiten aunque corran a la vez. Un rechazo definitivo queda `fallido` y se reintenta en la próxima
ejecución hasta `--max-attempts` (3 por defecto). Una reserva que quedó sin cerrar (el proceso murió a medias) **no se reenvía sola**: el correo pudo haber salido, así que
se informa como «en duda» para confirmarla a mano. Código de salida 1 si algo quedó fallido, agotado o en duda.

Solo se reintentan rechazos SMTP definitivos o fallos anteriores al envío. Si se pierde la conexión o la confirmación durante `send_message`, la reserva queda **en duda**: el servidor pudo aceptar el correo. No se reenvía automáticamente; el administrador debe comprobar la entrega antes de resolver la reserva.

Las variables `COMET_DIGEST_SMTP_HOST`, `COMET_DIGEST_SMTP_FROM`, `COMET_DIGEST_SMTP_PORT` (587 por defecto), `COMET_DIGEST_SMTP_USER`, `COMET_DIGEST_SMTP_PASSWORD` y `COMET_DIGEST_SMTP_STARTTLS` (1 por defecto) se guardan únicamente en `.env.portal`. Compose las transmite al contenedor. Dejarlas vacías mantiene el envío deshabilitado. Después de revisar la vista previa y confirmar destinatarios, añadir `--send` al comando siguiente para enviar; sin ese argumento nunca envía.

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
| `src/scouting/comet/` | Cálculos puros: categorías, reglas, datos, métricas, alertas, indicadores, adelantados, calidad, `pipeline` (cálculo compartido con el resumen), resumen, correo, `ledger` (registro de entregas), consultas y almacén de configuración |
| `app/comet_context.py` | Carga de datos y contexto con permisos y caché |
| `app/comet_followup.py`, `app/comet_insights.py` | Las siete pantallas |
| `app/ui/comet_widgets.py` | Formato «—», etiquetas de estado, colores accesibles |
| `db/portal/003_comet_followup.sql` | Migración de configuración (no aplicada) |
| `scripts/send_comet_weekly_digest.py` | Resumen semanal (vista previa por defecto) |
| `scripts/comet_demo_*.py`, `scripts/demo_comet_followup.py` | Datos ficticios y demostración local |
| `tests/test_comet_*.py`, `tests/comet_tiny.py` | Pruebas (cálculos a mano, seguridad, pantallas, SQL y migración) |

## Correcciones tras la revisión del 30-09-2026

Cada hallazgo se reprodujo primero con datos ficticios y después se corrigió con pruebas (`tests/test_comet_review_fixes.py`, `tests/test_comet_postgres.py`).

| # | Hallazgo | Corrección |
|---|---|---|
| 1 | La ficha fallaba con nacimientos `datetime64[ns, UTC]` (restaba `ctx.today`, sin zona) | El nacimiento se normaliza como **fecha civil** (`facts.civil_date`: el día en UTC, sin convertir a la hora de Santiago, que retrocedería un día). La edad se calcula por **aniversario** (`age_on`, 29 de febrero incluido), sin dividir días por 365,25. Prueba con `timestamptz` real en PostgreSQL y con la pantalla |
| 2 | Las filas repetidas jugador/partido inflaban minutos, goles y titularidades | Se distinguen: **idénticas** se cuentan una vez; **contradictorias** no se resuelven adivinando (la fuente no trae versión ni fecha de corrección): sus valores quedan sin dato, el jugador se marca *incompleto* y sale de rankings y alertas, y el partido, el ranking, la ficha y el resumen lo avisan. Aplica también a arqueros. Detalle en *Calidad de datos* |
| 3 | 1199/6000 = 19,98 % se mostraba como 20,0 % y no alertaba | Los porcentajes ya no se redondean en el cálculo; la alerta compara `minutos × 100 < umbral × posibles`. Solo la pantalla redondea; el detalle de la alerta trunca a 2 decimales para no mostrar «20,00 %» bajo un umbral de 20 % |
| 4 | Excluir períodos de selección daba 175 % de participación | Numerador y denominador salen del **mismo conjunto de partidos** (`possible_grid`). Un partido dentro de un período solo se descuenta si el jugador **no lo jugó**; si lo jugó cuenta y la contradicción se avisa. No se recorta a 100 %: *Calidad de datos* avisa cualquier participación mayor a 100 %, los períodos solapados y los partidos jugados dentro de un período |
| 5 | El resumen por correo ignoraba los períodos y podía enviarse dos veces | El script usa el mismo `pipeline` que las pantallas. Nuevo registro de entregas con reserva atómica, reintento limitado y sin reenvío ante la duda (ver arriba). No hay envío activado ni programado |
| 6 | Se declaraban ausentes datos que existen en COMET | Se leen `matchlength`, `matchstatus`, `secondyellow`, `owngoals`, `datefrom`, estatura y peso (si existen). Nuevas reglas: fuente de duración (registrada/nominal), estados de partido que no cuentan y fuente de antigüedad (primer partido/`datefrom`). `eventos_partido` figura como «sin acceso del lector», no como ausente; no se concedió ningún permiso |

**Sobre el alcance de la muestra.** La alerta de más de dos temporadas sin promoción no puede certificarse con solo las temporadas 2025 y 2026: tiene implementación y pruebas sintéticas, pero su resultado real depende de un historial más largo.
Las temporadas históricas de Sofascore pertenecen a Scouting y no cuentan aquí.

## Cierre de la segunda auditoría

Los indicadores de adelantados, permanencia y comparación excluyen a jugadores con planillas contradictorias en cualquier categoría de la temporada seleccionada. La pantalla muestra cuántos se excluyen. Las actuaciones válidas siguen disponibles en la ficha y los partidos; una contradicción de otra temporada no bloquea la actual. La explicación de antigüedad refleja la fuente seleccionada (`datefrom` o primer partido).

## Minutos desconocidos (revisión del 06-10-2026)

**Problema.** Si COMET no traía los minutos de un partido en que el jugador jugó, el total de minutos sumaba solo los partidos que sí los traían y se mostraba
como si fuera exacto. Un jugador que jugó dos partidos y de uno no tiene minutos aparecía con «80 minutos» y «33,3 % de participación», se ordenaba en el
ranking de minutos con esa cifra y, con pocos minutos conocidos, disparaba la alerta de «menos del 20 %». Del mismo modo, una fila sin la marca de jugó y sin
minutos se contaba como «0 minutos», y una fila marcada «no jugó» con minutos distintos de cero ignoraba esos minutos en silencio.

**Regla.** Un total con un sumando desconocido es desconocido. Se considera que no se sabe cuántos minutos jugó un jugador en un partido cuando:

| Situación en la planilla | Antes | Ahora |
|---|---|---|
| Jugó (marca de jugó) y no trae minutos | Suma parcial de los demás partidos | Minutos y participación «—» |
| No trae marca de jugó ni minutos | 0 minutos y 0 goles inventados | Minutos «—» (los goles solo si la fila los trae) |
| Marca «no jugó» pero trae minutos | Minutos ignorados (0) | Minutos «—»: la fuente se contradice y no se elige una versión |

Las apariciones (partidos citado, titular, suplente, jugó), los goles y las tarjetas del jugador **no cambian**, y los minutos *posibles* tampoco dependen de este dato.
Las filas repetidas contradictorias siguen su propia política (ver arriba) y no cuentan además como «minutos desconocidos».

**Efecto en las pantallas.** Cada una lo avisa con el nombre del jugador y manda a *Calidad de datos*, donde hay un control nuevo, *Jugadores con minutos desconocidos*.

| Dónde | Qué pasa con un jugador con minutos desconocidos |
|---|---|
| Ficha | Minutos, participación y minutos en categoría superior en «—»; el mes afectado no se dibuja como una suma parcial |
| Ranking de minutos | No entra y se lista en un aviso; en goles, tarjetas y partidos ganados sí figura |
| Alerta «menos del 20 %» | No se evalúa (en ninguna categoría de la temporada: sin minutos no se sabe cuál es su categoría principal) y se lista en la pantalla de alertas |
| Alerta «juega en categoría superior» | Sigue vigente; el detalle dice «minutos incompletos» en vez de citar una suma parcial |
| Participación de la serie (indicadores) | Se calcula sin él en numerador **y** denominador; los minutos totales de la serie avisan cuántas actuaciones quedaron fuera |
| Jugadores adelantados | Quedan fuera de los indicadores basados en minutos (minutos arriba, permanencia, comparación) y se avisa cuántos son |
| Resumen semanal (pantalla y correo) | Las mismas alertas, más una nota con cuántos jugadores no se evalúan en la de participación |

**Ejemplo antes / después** (mini-torneo ficticio de `tests/comet_tiny.py`: U-15 con tres partidos de 80 minutos; P1 jugó los partidos 1 y 2, y de los minutos del 2 COMET no trae el dato):

| | Antes | Ahora |
|---|---|---|
| Minutos de P1 | 80 | — |
| Participación de P1 | 33,3 % | — |
| Ranking de minutos U-15 | 1.º P2 (190), 2.º P3 (160), 3.º **P1 (80)** | 1.º P2 (190), 2.º P3 (160); P1 en el aviso |
| Participación de la serie U-15 | 44,8 % | 48,6 % = (190 + 160 + 0) / (3 × 240) |
| Si P1 jugó los 3 partidos y solo se conocen 10 minutos | Alerta «4,16 % · 10 de 240 min posibles» | Sin alerta; P1 figura como jugador sin minutos completos |

Pruebas: `tests/test_comet_unknown_minutes.py` (cálculos y pantallas) y una prueba con un `NULL` real en `tests/test_comet_postgres.py`.
**No se pudo comprobar con datos reales ni en la web:** se ignora cuántas veces ocurre esto en COMET. El control de calidad lo cuenta; si es 0, esta corrección no cambia ninguna cifra.

### Hallazgos de esta revisión que NO se corrigieron

Quedan documentados con su reproducción para decidir cuál sigue (varios dependen de una regla que aún debe confirmar Pablo):

| # | Hallazgo | Reproducción con el mini-torneo | Qué falta |
|---|---|---|---|
| 1 | **Edad ausente = «no adelantado» y 0 minutos arriba.** Sin fecha de nacimiento, `ahead_minutes` queda en 0 (no «—») y el «% de adelantados» de la categoría los cuenta en el denominador | P2 sin nacimiento: la ficha muestra 0 minutos arriba y la categoría U-15 «0 de 3 adelantados (0,0 %)» en vez de «sin dato» | Excluir del denominador a quien no tiene edad y mostrar «—» |
| 2 | **Con la duración «nominal», un partido ya pasado sin planilla ni marcador cuenta como minutos posibles** (con la duración «registrada», la de por defecto, no) | Un partido extra U-15 sin planilla: minutos posibles de P1 pasan de 240 a 320 y su participación de 58,3 % a 43,8 % | Que Pablo elija la fuente de duración y qué estados de partido no cuentan |
| 3 | **Un jugador citado una sola vez en una serie suma todos los partidos de la serie como minutos posibles** (por defecto), lo que desinfla la participación de la serie | Seis invitados citados una vez en la U-15: participación de la serie de 51,0 % a 20,4 % | Pregunta 2 de Pablo (¿desde que llegó o toda la serie?) y, si se confirma, un mínimo de citaciones para contar como parte de la serie |
| 4 | **«N temporadas seguidas en U-14» tras un descenso**: la racha cuenta temporadas sin subir de categoría, pero el texto afirma que estuvo todo ese tiempo en la categoría actual | Jugador en U-15 (2024) y U-14 (2025, 2026): «3 temporadas seguidas en U-14 (desde 2024)» | Pregunta 5 de Pablo (qué es «promoción»); mientras tanto, corregir el texto |
| 5 | **Amarillas con ciclo «por temporada»: la categoría mostrada es la de la última fila de la planilla**, no la principal | P2 (U-15 principal, U-14 secundaria) aparece con categoría U-14 | Mostrar la categoría principal |
| 6 | **«Adelantados» y «Grupo de edad» comparten jugadores** cuando alguien reparte minutos entre su categoría y la superior | P2 figura en los dos grupos de la categoría por edad U-14 | Decidir si el grupo de comparación debe excluir a los adelantados |

## Hallazgos que no se tocaron

* `get_squad_by_age_category` (`comet_dashboard.py`) asigna categorías con rangos de edad que se solapan (15 aparece en U-16 y U-15; 14 en U-15 y U-13) y nunca devuelve U-14. Las pantallas nuevas no lo usan; se dejó intacto para no cambiar funciones existentes.
* Las pantallas nuevas no muestran ni cruzan datos de Sofascore.
