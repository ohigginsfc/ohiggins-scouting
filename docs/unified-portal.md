# Portal unificado O'Higgins

Una aplicación Streamlit con módulos COMET y Scouting. Las sincronizaciones siguen
independientes dentro del repo unificado: COMET tiene su [importador y workflow](comet-synchronization.md);
Sofascore conserva su worker y su procedimiento de actualización. La programación
COMET se activa con `COMET_SCHEDULE_ENABLED=true` después de retirar el job antiguo. No se
mezclan las tablas deportivas ni se usa un iframe entre aplicaciones.

## Identidad y permisos

Las cuentas personales y contraseñas viven en **Supabase Auth**, esquema `auth`.
El esquema privado **portal** contiene perfiles, roles y cambios de cuentas. No
guarda contraseñas y no debe exponerse en la Data API. Los esquemas `public`
(COMET) y `scouting` se conservan. Auth sin perfil activo no permite acceder.

| Capacidad | Admin | Scout |
|---|---|---|
| Datos federados/menores de COMET | Sí, lectura | No |
| Seguimiento deportivo COMET (partido semanal, rankings, ficha, indicadores, alertas, adelantados) | Sí | No |
| Configurar reglas y alertas COMET; marcar jugadores proyectados o de selección y sus períodos | Sí | No |
| Scouting visible, estadísticas y comparaciones | Sí | Sí |
| Consultar informes ocultos y sus valoraciones | Sí | Sí |
| Crear informes | Sí | Sí |
| Editar evaluación y recomendación | Todos | Propios visibles y todos los ocultos |
| Restaurar o eliminar informes ocultos | Sí | Sí |
| Ocultar o eliminar informes visibles | Sí | No |
| Asignar propietario a informes migrados | Sí | No |
| Gestionar cuentas y roles | Sí | No |
| Lanzar sincronizaciones desde el portal | No; usar procesos operativos | No |

El autor se fija desde la identidad autenticada y se conserva en
`raw_payload.portal_owner_id`. Los informes migrados sin ese identificador se
pueden consultar; si están visibles, solo el admin puede editarlos. Los ocultos
pueden ser gestionados por ambos roles. No se asigna propiedad por
coincidencia de nombre. Administración permite asignarla explícitamente a una
cuenta activa, conservando el contenido y registrando quién y cuándo la asignó.

Los permisos se comprueban antes de cargar COMET, consultar sus datos y devolver
resultados de caché, y también en los servicios que modifican informes. La conexión
de scouting se rechaza si puede leer tablas de `public`. COMET utiliza una conexión
distinta, de solo lectura. No se enriquece scouting con información federada.
La migración `002_comet_reader.sql` incluye políticas RLS de SELECT para ese
lector: conceder SELECT sin una política RLS puede devolver cero filas aunque
las tablas tengan datos. Validar conteos no vacíos al configurar COMET.

El contador y la sección **Informes ocultos** están disponibles para ambos roles.
Scout puede consultar, editar, restaurar y eliminar cualquier informe oculto,
incluidos los migrados o creados por otros scouts. El borrado requiere confirmación.
Al restaurarlo, se vuelven a aplicar los permisos habituales de los informes visibles:
scout solo edita los propios y no puede ocultarlos ni eliminarlos. La propiedad se
conserva al editar. Los permisos se comprueban en los servicios y no requieren una migración.

Cada sesión se valida contra Supabase Auth y el perfil privado en cada ejecución
de Streamlit. Cambiar rol/estado/contraseña desde el portal revoca las sesiones del
portal mediante su revisión. Al caducar el token se solicita iniciar sesión de nuevo;
no se guarda refresh token ni se comparte un cliente Auth global entre sesiones.
Supabase controla los límites de intentos. Se conserva siempre un admin activo.

## Preparación y despliegue en paralelo

1. Aplicar explícitamente `db/portal/001_accounts.sql` y `002_comet_reader.sql` como
   propietario de la BD, después de revisarlos. No son migraciones automáticas de
   scouting. Definir privadamente las contraseñas de `portal_runtime` y `comet_reader`.
   Para guardar reglas, alertas, marcas y períodos del seguimiento deportivo de COMET, aplicar
   también `db/portal/003_comet_followup.sql` (solo esquema `portal`; incluye el registro de
   entregas del resumen semanal, sin el cual el script no envía nada; sin ella esas pantallas
   funcionan con valores por defecto y en solo lectura). Ver
   [Seguimiento deportivo COMET](comet-seguimiento-deportivo.md).
   Para el marcador al entrar y salir, aplicar `db/portal/004_comet_events_reader.sql`
   después de la 002: lectura de eventos de partidos del club, sin escritura ni
   permisos nuevos para scout. Ver [cobertura y goles rivales](resultado-con-jugador-en-cancha.md).
2. Copiar `.env.portal.example` a `.env.portal` y completar las tres conexiones
   independientes y las claves de Supabase Auth. La clave secreta solo va al backend;
   nunca a URLs, repositorio, navegador o logs. Usar el session pooler y SSL.
3. Desactivar altas públicas en Supabase Auth para operar por cuentas gestionadas.
   Aunque existan altas externas, no adquieren perfil ni acceso al portal.
4. Construir y crear el primer admin con correo personal previamente verificado:

```bash
docker compose --env-file .env.portal -f docker-compose.portal.yml build portal
docker compose --env-file .env.portal -f docker-compose.portal.yml run --rm portal python scripts/bootstrap_portal_admin.py
docker compose --env-file .env.portal -f docker-compose.portal.yml up -d portal
```

El bootstrap solo funciona si no hay perfiles. No envía correos. Las contraseñas se
introducen de forma interactiva, no como argumentos. Para una identidad Auth que ya
exista, vincular su UUID al perfil desde SQL privado en lugar de recrearla o cambiar
su contraseña. Si Auth crea la identidad pero falla guardar el perfil, permanece
sin acceso al portal; revisar y vincular ese UUID, sin borrar usuarios automáticamente.

El Compose publica solo en `127.0.0.1:18502` por defecto. Para el club, colocar un
proxy HTTPS delante y mantener el puerto interno privado. No reemplazar la web
actual hasta validar ambos roles. No se monta el socket Docker ni se permite lanzar
scrapers desde esta web. El volumen de imágenes de scouting se conserva.

Desde Administración, crear las demás cuentas indicando correo personal verificado,
nombre, rol y contraseña inicial; compartirla privadamente. El usuario cambia su
contraseña desde los mecanismos de Auth o solicita un reinicio al admin. Esta primera
versión no implementa un flujo de recuperación por correo ni envía invitaciones.

## Validación y reversión

Si aparece «No se pudo iniciar sesión», comprobar Auth **y la conexión de perfiles**;
ese mensaje no identifica por sí solo una contraseña incorrecta. El `.env` de la web
antigua de scouting no sustituye `.env.portal`: completar sus seis variables de Auth
y conexiones con los valores privados reales, nunca `replace-me` ni los ejemplos.
Las cuentas existentes no se recrean al actualizar.

```bash
docker compose --env-file .env.portal -f docker-compose.portal.yml exec -T portal python scripts/check_portal_config.py
```

El comprobador solo lee y muestra PASS/FAIL, tipos de fallo y códigos HTTP; no imprime
claves, DSN, correos ni tokens. Si se corrige `.env.portal`, recrear el contenedor:

```bash
docker compose --env-file .env.portal -f docker-compose.portal.yml up -d --build --force-recreate portal
```

Usar el mismo `--env-file .env.portal` y archivo Compose tanto al arrancar como al
comprobar. Revisar variables exportadas en la shell: pueden tener prioridad sobre el
archivo. Comprobar primero en el puerto interno; después en la URL del proxy.

- Testear login real y las pantallas de COMET/scouting con el admin.
- Testear scout, URL/estado manipulado, caché COMET previamente cargada, informe
  ajeno/propio/migrado, cuentas desactivadas, cambios de rol y último admin.
- Conservar conteos de informes/valoraciones y comprobar que la integración no
  reimporta ni modifica datos deportivos al iniciar.
- Ejecutar pytest con una BD desechable `scouting_test` local para las pruebas SQL;
  nunca usar la conexión de producción en `SCOUTING_TEST_DATABASE_URL`.
- Rollback: detener solo el servicio portal y conservar la web anterior. No borrar
  esquemas, cuentas, imágenes ni informes para deshacer un cambio de interfaz.

## Dashboard de Scouting: campogramas y vista preliminar de informes ocultos

Cambios pedidos por Pablo en la reunión del 13-10-2026. Valen para Admin y Scout (ambos ya gestionan informes ocultos).

**Dos campogramas.** El mapa de posiciones del Dashboard pasó de uno a dos, lado a lado: *jugadores chilenos* y *jugadores extranjeros*.
Cada uno cuenta, por posición, los jugadores y los informes visibles de su grupo; tiene su propia selección (hacer clic en una posición
filtra la tabla de jugadores de ese grupo, y «Limpiar filtro» solo limpia ese mapa). Los informes ocultos no cuentan, igual que antes.

La nacionalidad de la ficha es texto libre (Sofascore trae «Chile»; el alta manual se escribe a mano), así que se agrupa así:

| Grupo | Criterio |
|---|---|
| Chileno | Alguna nacionalidad es chilena: «Chile», «chilena», «CHILENO», «Chile / Argentina». La doble nacionalidad con Chile no cuenta como extranjero; las tildes y las mayúsculas no importan |
| Extranjero | Tiene nacionalidad y ninguna es chilena |
| Sin dato | No tiene nacionalidad. **No se supone ninguna**: no aparece en ninguno de los dos mapas y una nota debajo dice cuántos jugadores e informes quedan fuera |

La suma de los tres grupos es el conteo por posición de antes (una prueba contra PostgreSQL lo comprueba). La regla vive en
`src/scouting/services/nationality_service.py`. Si el club decide tratar la doble nacionalidad de otra manera, se cambia en un solo lugar.

**Vista preliminar de informes ocultos.** El Dashboard muestra, bajo «Actividad reciente», los 5 informes ocultos más recientes
(jugador, posición, scout, fecha, valoración, recomendación, inicio del resumen, cuándo y quién lo ocultó) y cuántos hay en total, con un
botón para ir a *Informes ocultos*, donde se editan, restauran o eliminan. Es solo lectura. *(Se interpretó «vista preliminar» como una
vista previa en el Dashboard; la página de gestión ya mostraba el detalle completo de cada informe.)*

## Mejoras de Scouting del 30-10-2026

Pedidas por el club tras revisar el Dashboard y «Consultar jugador». Valen para Admin y Scout, con los permisos de siempre. **No hay
migraciones ni cambios de esquema**: solo código de la aplicación.

### Posición y valoración en «Actividad reciente»

| Lo que se veía | Qué lo causaba (según el código) | Qué cambia |
|---|---|---|
| Posición «None» | La tabla mostraba la posición de la **ficha del jugador**; si la ficha no la tiene (jugadores creados por importación, o sin posición), salía el vacío de la base de datos escrito como «None» | Se muestra la posición de la ficha; si no hay, la **posición observada** que el scout anotó en ese informe; si tampoco, «—». Nunca «None» y nunca se inventa una posición |
| Todas las valoraciones en 6 | El control «Rating general» del alta manual **arrancaba en 6** y su valor se guardaba siempre, aunque el scout no lo tocara | La valoración general ahora es **opcional**: hay que marcar «Registrar una valoración general» para enviarla. Sin marcar, el informe queda sin valoración («—») y no se guarda ningún valor de relleno |

En las tablas de informes (Actividad reciente, vista previa de ocultos y lista de ocultos) **cualquier celda sin dato se ve «—»**, no «None»
(también valoración, scout, competición y recomendación), y la valoración sale sin decimales de sobra (6.5, no 6.500000).

**Lo que no se hizo a propósito:** no se tocan los informes ya guardados. Un 6 elegido de verdad y un 6 puesto por el valor inicial del control
son idénticos en la base de datos, así que no hay forma segura de distinguirlos; borrar o cambiar valoraciones en bloque sería inventar datos.
Quien tenga acceso de lectura a Supabase puede ver cuántos hay antes de decidir nada (consultas de solo lectura; en Supabase el esquema es `scouting`):

```sql
-- Distribución de valoraciones de los informes visibles
SELECT rating, count(*) FROM scouting.scouting_reports WHERE NOT COALESCE(is_hidden, false) GROUP BY rating ORDER BY count(*) DESC;
-- Valoraciones y 6 exactos por origen del informe (manual, importado…)
SELECT source_type, source_name, count(*) AS informes, count(*) FILTER (WHERE rating = 6) AS con_6
FROM scouting.scouting_reports GROUP BY 1, 2 ORDER BY informes DESC;
-- Informes cuyo jugador no tiene posición en la ficha
SELECT count(*) FILTER (WHERE p.position IS NULL OR trim(p.position) = '') AS sin_posicion_en_ficha, count(*) AS informes
FROM scouting.scouting_reports sr JOIN scouting.players p ON p.id = sr.player_id WHERE NOT COALESCE(sr.is_hidden, false);
```

Si el equipo confirma que los 6 eran el valor inicial, cada informe se corrige con «Actualizar informe» (abajo). Cualquier corrección masiva
debe decidirla y ejecutarla quien administra la base de datos; este cambio no la hace.

### Botones para actualizar

*La petición decía «un botón para actualizar el informe haciendo clic en el momento». Puede significar dos cosas y se cubrieron las dos:*

* **«Actualizar»** (sobre la tabla de «Actividad reciente»): vuelve a leer los informes de la base de datos al instante.
* **«Actualizar informe»** (en «Gestión de informes» y en la página «Informes ocultos»): corrige en el momento la **posición observada**, la
  **valoración general** (de 0 a 10, o «sin valoración») y, **solo si la ficha del jugador no tiene posición**, esa posición (la usan el
  campograma y las tablas por posición). Nunca pisa una posición que ya existe. Valida todo antes de guardar: o se guarda todo o nada.
  Permisos: los mismos que editar un informe (el Scout, sus informes visibles y cualquier oculto; el Admin, todos). En el piloto de solo lectura no aparece.

### Campograma de los informes ocultos

Debajo de la vista preliminar de ocultos del Dashboard (solo si hay informes ocultos) y encima de la lista en la página **Informes ocultos**
hay un campograma como los demás, con los **informes ocultos por posición**, y al lado una tabla con jugadores e informes por posición.

* Cuenta según la **posición de la ficha del jugador**, igual que los otros dos campogramas. *(Interpretación: «ocultos por posición» se
  tomó así por coherencia; ver las preguntas abajo.)*
* En el Dashboard, hacer clic en una posición muestra debajo los informes ocultos de esa posición. En la página «Informes ocultos» filtra la
  lista y el selector de informe; «Limpiar filtro» vuelve a mostrar todos.
* Lo que **no se puede ubicar** en el campo no desaparece: los jugadores sin posición en la ficha y los que tienen una posición que el campograma
  no reconoce aparecen igualmente en la tabla (y en una nota con su número). La suma de la tabla es el total de informes ocultos.
* Es de solo lectura: se puede mirar en el piloto de solo lectura y no añade ningún botón de edición.

### «Consultar jugador»: equipos del jugador

* **Lista de jugadores:** si la ficha de scouting no tiene equipo (antes salía «(—)»), se muestra el **último equipo que figura en sus datos
  objetivos**, con su temporada: `Nombre (Temuco · 2025)`. El año evita confundirlo con el equipo actual. Si la ficha tiene equipo, manda la ficha.
* **Ficha del jugador:** nueva tabla **Historial de equipos** (temporada, competición, equipo), de la más reciente a la más antigua.
* Fuente: `objective_metrics.raw_payload` de datos **reales de Sofascore**; los datos demo se excluyen (un equipo de prueba no es un equipo anterior).
  Un bloque temporada + competición sin equipo en el dato no aparece. Si en una misma temporada hay dos competiciones, se muestra primero la que tiene más métricas.
* **Límite conocido:** solo hay historial para jugadores con datos objetivos. La ficha de scouting guarda **un único** equipo (el primero que se anotó;
  los informes siguientes no lo cambian) y no conserva los anteriores, así que un jugador visto solo por scouts, sin Sofascore, no tiene «antiguos
  equipos» que mostrar; el texto de la ficha lo dice en vez de inventarlos.

### Preguntas para Pablo (nuevas)

1. **Valoración 6:** ¿los scouts solían dejar el 6 que traía el control? Si sí, ¿quiere que esos informes pasen a «sin valoración» (lo haría quien administra la base de datos, no la aplicación)?
2. **Campograma de ocultos:** ¿debe contar por la posición de la **ficha** del jugador (como ahora) o por la posición **observada en cada informe**?
3. **Antiguos equipos de jugadores sin Sofascore:** ¿quieren que el scout anote el club en **cada** informe (o un historial de clubes en la ficha) para poder mostrarlos? Hoy no se guardan.
4. **«Actualizar informe»:** ¿bastaba refrescar la lista, o querían editar posición y valoración como se hizo?

### Lo que no se pudo comprobar

* Con datos reales: cuántos informes tienen posición vacía o un 6 por defecto, y si «None» venía solo de fichas sin posición. Las causas salen de leer el código; las consultas de arriba permiten comprobarlo.
* El aspecto con datos reales: se revisó en el navegador (campograma de ocultos con su filtro, «Actualizar informe», lista de jugadores con
  equipo, Historial de equipos y las tablas de informes), pero **solo con datos ficticios**, sin base de datos. Esa revisión encontró que la
  valoración vacía se veía «None» en las tablas y se corrigió. Las pruebas automáticas (AppTest) comprueban contenido y comportamiento.

## Procedencia de COMET

`app/comet_dashboard.py` incorpora las cinco pantallas de dataProject/main,
commit `c6a0024b11b2e5b4fd3722017e08aadc101db180`, adaptadas al login común y a la
conexión de lectura exclusiva del admin. El [importador](comet-synchronization.md), los
[reportes y correos](comet-reports-email.md) también viven en este repo, en workers
independientes del portal. Los requisitos nuevos del club (partido semanal, rankings, ficha individual,
indicadores, alertas, adelantados, marcas y resumen semanal) están descritos en
[Seguimiento deportivo COMET](comet-seguimiento-deportivo.md); leen COMET con la misma
conexión de solo lectura y no modifican `dataProject`.

## Estado de los informes antiguos

El administrador anterior completó su migración. El 30/09/2026 se verificaron en
Supabase 109 informes y 2.564 valoraciones. No volver a ejecutar la migración antigua
como parte de este despliegue. Su documentación queda como referencia histórica.
