# Resultado con el jugador en cancha

## COMET: uso en el portal

Solo **Admin**. En **Partido semanal** y **Ficha del jugador → Partidos** se muestran:

- Entró / Salió: inicio, final o minuto absoluto, incluido el descuento.
- Marcador y estado al entrar y al salir: ganando, empatando o perdiendo.
- ¿Cambió el resultado?: compara el estado a la entrada con el estado a la salida.
- Goles a favor y en contra durante ese intervalo.
- Cronología: calculado o motivo del dato ausente.

El marcador final permanece separado. Un cambio transitorio que acaba en el mismo
estado no se marca como cambio entre entrada y salida. Los rankings y porcentajes
históricos de victorias siguen usando el **resultado final de partidos jugados**;
no son rankings derivados de esta cronología.

## Lectura y despliegue

Después de `db/portal/002_comet_reader.sql`, el propietario de PostgreSQL aplica
explícitamente [004_comet_events_reader.sql](../db/portal/004_comet_events_reader.sql).
Es idempotente y concede exclusivamente `SELECT` a `comet_reader`, con una política
RLS para eventos de partidos de O'Higgins. Conserva las políticas y el estado de RLS
previos; aborta si la tabla no tiene RLS habilitado. No concede permisos a Scout ni
a otros roles, no modifica datos deportivos.

El administrador del servidor actualiza el portal siguiendo
[el manual de despliegue](unified-portal.md). No hay cambio de contraseña ni de
`.env.portal`. La aplicación no ejecuta la migración al arrancar. La caché de datos
caduca a los 10 minutos; reconstruir el portal renueva el proceso.

Si la tabla o sus columnas no son visibles para el lector, el portal conserva las
otras funciones y muestra «Eventos no disponibles». Scout no puede consultar COMET,
incluidos los datos que Admin ya cargó en caché.

## Contrato del export COMET

`scouting.comet.events` adapta `eventos_partido` al cálculo probado
`scouting.onpitch.on_pitch_result`:

| Dato | Interpretación |
|---|---|
| `uid` | Identificador del evento: duplicados idénticos cuentan una vez; versiones diferentes invalidan el partido |
| `matcheventtype` | `Gol` y `Penal` suman al equipo del evento; `Autogol` suma al contrario; tanda y penales fallados se excluyen |
| `teamid` | Se valida contra ambos equipos del partido; la consulta conserva los goles rivales |
| `displayminute` y `stoppagetime` | Reloj absoluto: `41'` en una serie de tiempos de 40 minutos, `45'+2'` en descuento |
| `minute` | Se reinicia en cada tiempo: no sirve directamente como reloj absoluto |
| Sustitución | `personid` entra; `secondpersonid` sale |
| Roja / expulsión / segunda amarilla | Termina el intervalo si ocurre mientras está dentro; una tarjeta posterior a su salida no lo hace |

No se deduce el minuto de un cambio a partir del total de minutos jugados. Para
confirmar que alguien siguió hasta el final se contrastan sus minutos con la
duración nominal y registrada; una discrepancia deja el dato ausente. Reentradas,
cambios contradictorios, titularidad desconocida y goles sin reloj no se inventan.

**Regla provisional:** un gol en el mismo minuto que entrada/salida cuenta con el
jugador dentro. No hay segundos para ordenar esos eventos; la pantalla lo indica.
Un suplente sin participar no recibe un supuesto 0-0.

## Cobertura y goles rivales

La inspección del 13-10-2026, después de sincronizar COMET, encontró 4.767 eventos
en 536 partidos; 539 partidos de O'Higgins tienen marcador final. Bajo el conteo
de gol, penal convertido y autogol, 131 reconstruyen ese marcador. Es una cobertura
preliminar de goles, **no 131 partidos con todos los intervalos de jugadores validados**.
Todos los eventos goleadores disponibles pertenecen a O'Higgins: no hay eventos de
goleadores rivales. Un autogol propio sí puede explicar un gol recibido.
Con el adaptador completo, la comprobación de lectura calculó 1.948 intervalos de
jugadores en 125 partidos; el resto permanece sin dato por cobertura insuficiente.

Si los goles no reconstruyen exactamente **ambos** marcadores finales, el resultado
en cancha queda «— / Cronología de goles incompleta». Un 0-0 necesita que exista
algún evento del partido para distinguir una cronología vacía de un export ausente.

Para ampliar la cobertura:

1. En COMET Data Platform, revisar el informe **Eventos de partido**: solicitar
   eventos de **ambos equipos en los partidos de O'Higgins**, manteniendo el ámbito
   de partidos y temporadas del club. El importador del repo unificado conserva los
   equipos recibidos; no elimina goles rivales.
2. Si cambia el enlace del informe, actualizar privadamente `LINK` en la pestaña
   `ENDPOINTS` de la hoja configurada en el worker COMET; no publicar su `API_KEY`.
3. Ejecutar la [sincronización COMET](comet-synchronization.md) y contrastar otra vez goles y
   marcador final, además de la cobertura de cambios. Revisar los catálogos de
   equipos, competidores y personas para respetar las relaciones del importador.
4. Si el informe no permite esa cobertura, COMET documenta una API de exportación
   por partido: `/api/export/comet/match/{matchFifaId}/events`. Es **otra API**;
   no se debe reutilizar ni asumir válida la clave del informe. El superusuario
   COMET de la organización debe facilitar el Swagger del tenant y una clave con
   ámbito autorizado. No se ha conectado esa API ni obtenido esa clave en esta PR.

Fuentes oficiales: [eventos por partido y sincronización](https://kb.analyticom.de/comet/additional-guidelines),
[acceso y filtros de COMET LIVE API](https://kb.analyticom.de/live/comet-live-api).

## Scouting: integración pendiente

El cálculo genérico también sirve para Sofascore, pero la BD de scouting conserva
métricas agregadas por jugador/temporada. Hay que guardar goles y cambios de los
incidentes por partido, validar su contrato y volver a importar los históricos.
Esta PR conecta **COMET**, sin modificar la sincronización ni las pantallas de Sofascore.
