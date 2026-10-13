# Resultado con el jugador en la cancha (COMET y Scouting)

Pedido de Pablo en la reunión del 13-10-2026, para **los dos módulos**: no basta el resultado final del partido en que el jugador
jugó. Hay que mostrar **cuál era el marcador cuando entró y cuando salió, y si el resultado se modificó** mientras estuvo en la cancha.

> **Estado:** el cálculo está hecho y probado (`src/scouting/onpitch.py`). **Ninguna pantalla lo usa todavía**, porque ninguna de las dos
> fuentes entrega hoy los datos que necesita. Este documento dice cuáles son, dónde están y qué hay que decidir o autorizar.

## Cómo se calcula

`scouting.onpitch.on_pitch_result(goals, final, entered=None, left=None, same_minute='durante')` recibe:

* los **goles del partido con su minuto** y el equipo al que suman (un autogol del rival suma a favor);
* el **marcador final**: los goles deben sumarlo exactamente;
* el **minuto de entrada** (nada si fue titular) y el **minuto de salida** (nada si siguió hasta el final).

Devuelve el marcador al entrar y al salir, los goles a favor y en contra mientras estuvo, si el resultado (*ganando / empatando / perdiendo*)
cambió entre una cosa y otra, y el resultado final aparte. `describe()` lo escribe en una frase:

> Entró a los 60' con 0-0 (empatando); terminó el partido con 2-0 (ganando): el resultado cambió mientras estuvo en la cancha

Reglas:

| Caso | Qué hace |
|---|---|
| Los goles no suman el marcador final, o falta el marcador | **Sin dato** (`None`): la cronología está incompleta o se contradice. No se reemplaza por el resultado final ni se inventa un gol |
| 0-0 sin goles | Es una cronología completa: el resultado no cambió |
| Descuento (45+2') | Se ordena dentro de su tiempo: un gol de 45+2 ocurre después de una salida a los 45+1 |
| Gol en el mismo minuto que su entrada o su salida | **Supuesto sin confirmar:** cuenta con el jugador dentro (`'durante'`). La alternativa (`'fuera'`) está implementada y probada: es solo cambiar el argumento |
| Salida por expulsión | La salida es el minuto de la roja; la fuente debe indicarlo como salida |
| Entrada y salida en el mismo minuto, con regla «fuera» | Intervalo vacío: cero goles mientras estuvo y el mismo marcador al entrar y salir |
| Minuto, descuento o marcador inválidos | Se rechazan valores negativos, fraccionarios o desconocidos; no se calcula con `NaN` |

Ejemplos comprobados a mano: titular que juega todo con 1-0 y 1-1 (empate, no cambió); suplente que entra a los 60' con 0-0 y el equipo termina
2-0 (cambió a favor); titular que sale a los 55' perdiendo 0-1 porque el rival marcó mientras estaba (cambió en contra, aunque el partido termine 1-1).

## Qué datos necesita cada fuente

| Dato | COMET | Scouting (Sofascore) |
|---|---|---|
| Marcador final | ✅ Ya se lee: fase «Segundo tiempo» de `partidos_fases` | ✅ Ya está: el calendario trae el marcador final de cada partido |
| Goles con minuto y equipo | ⛔ Tabla `eventos_partido`: **el lector del portal no tiene acceso y no se conoce su estructura** | 🟠 La respuesta de incidentes (`/event/{id}/incidents`) **ya se descarga** en cada partido, pero el código solo conserva las tarjetas; los goles se descartan |
| Minuto de entrada y de salida | ⛔ Mismo: los cambios figurarían en `eventos_partido` si existen | 🟠 Los cambios vienen en los mismos incidentes y también se descartan. Los titulares se distinguen en la alineación (`substitute`) |
| Salida por roja | ⛔ Mismo | 🟠 La tarjeta roja con su minuto ya se extrae al descargar (`cardMinutes`), pero queda solo en los archivos del partido, no en la base |
| Dónde se guardaría | Se leería en cada carga, como el resto de COMET (no se guarda nada) | ⛔ **Hoy no hay ninguna tabla por partido**: la base solo guarda métricas agregadas por jugador y temporada |

### COMET: lo que falta

1. **Estructura de `eventos_partido`**: nombres y tipos de columnas y los valores posibles del tipo de evento (gol, cambio, tarjeta…), y si
   el minuto trae descuento. Sin eso no se puede escribir la consulta ni saber si la cobertura alcanza las categorías formativas.
2. **Permiso de lectura.** Hoy el rol `comet_reader` no tiene `SELECT` sobre esa tabla (a propósito: no se concedió ningún permiso). Haría falta una
   migración que dé solo lectura sobre esa tabla, con su política de seguridad por filas, **que revise y aplique el propietario de la base**. Este repositorio
   no la aplica; se redacta cuando se conozca la tabla. La separación COMET/Scouting no cambia: se amplía lo que el lector de COMET puede leer dentro de COMET.
3. **Calidad**: cuántos partidos tienen eventos y si los goles suman el marcador (el cálculo lo comprueba y descarta el partido si no cuadra).

### Scouting: lo que falta

1. **Conservar goles y cambios** al descargar cada partido (hoy se descartan) y guardarlos **por partido**: una tabla nueva y su migración, y una importación
   atómica como la de métricas. Los datos agregados actuales no sirven: perdieron el minuto.
2. **Volver a descargar** los partidos ya publicados (2024, 2025 y el corte de 2026) para tener sus incidentes. La extracción de Sofascore está limitada
   (5 segundos entre peticiones y bloqueo 403 desde los ejecutores de GitHub), así que se haría con el procedimiento manual local ya documentado.
3. **Formato real de los incidentes.** El repositorio solo conoce los incidentes de tarjeta. Los de gol y cambio (campos de minuto, descuento, equipo
   local o visitante, jugador que entra y sale) hay que **confirmarlos con una muestra real** de un partido antes de escribir el lector.

## Qué hay que decidir

* **Gol en el mismo minuto que un cambio** (supuesto actual: cuenta con el jugador dentro). Es una regla futbolística: ¿lo define Pablo?
* **Dónde mostrarlo.** Propuesta: en COMET, columnas *Entró / Salió / Marcador al entrar / Marcador al salir / ¿Cambió?* en la planilla de *Partido semanal*,
  el historial de la *Ficha del jugador* y un conteo de partidos en que el resultado cambió a favor mientras estuvo; en Scouting, una tabla por partido
  en la ficha del jugador. Si Pablo prefiere otra cosa, se ajusta.
* **Qué pasa con los partidos sin eventos:** se muestran con «—» (sin dato) y el resultado final aparte, nunca como un cambio de resultado supuesto.

## Qué necesito para seguir

1. La estructura de `eventos_partido` (basta con los nombres de columnas, sus tipos y los valores del tipo de evento; no hace falta compartir datos de jugadores).
2. Si COMET se puede consultar con permiso para esa tabla, o si hay otra fuente de goles y cambios con minuto para las categorías formativas.
3. Una muestra de la respuesta `/event/{id}/incidents` de un partido de la Primera División de Chile (puede ser la copia de un partido cualquiera).
4. La decisión sobre el gol del mismo minuto.

Relacionado: [seguimiento deportivo de COMET](comet-seguimiento-deportivo.md) (pregunta 1 del listado de reglas).
