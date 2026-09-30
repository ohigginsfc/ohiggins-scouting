# Portal unificado O'Higgins

Una aplicación Streamlit con módulos COMET y Scouting. Las sincronizaciones siguen
independientes: COMET permanece en dataProject/Actions; Sofascore conserva su worker
y cron. No se mezclan las tablas deportivas ni se usa un iframe entre aplicaciones.

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
| Crear informes | Sí | Sí |
| Editar evaluación y recomendación | Todos | Solo propios visibles |
| Ocultar, restaurar o eliminar informes | Sí | No |
| Asignar propietario a informes migrados | Sí | No |
| Gestionar cuentas y roles | Sí | No |
| Lanzar sincronizaciones desde el portal | No; usar procesos operativos | No |

El autor se fija desde la identidad autenticada y se conserva en
`raw_payload.portal_owner_id`. Los informes migrados sin ese identificador se
pueden consultar, pero solo el admin puede editarlos. No se asigna propiedad por
coincidencia de nombre. Administración permite asignarla explícitamente a una
cuenta activa, conservando el contenido y registrando quién y cuándo la asignó.

Los permisos se comprueban antes de cargar COMET, consultar sus datos y devolver
resultados de caché, y también en los servicios que modifican informes. La conexión
de scouting se rechaza si puede leer tablas de `public`. COMET utiliza una conexión
distinta, de solo lectura. No se enriquece scouting con información federada.
La migración `002_comet_reader.sql` incluye políticas RLS de SELECT para ese
lector: conceder SELECT sin una política RLS puede devolver cero filas aunque
las tablas tengan datos. Validar conteos no vacíos al configurar COMET.

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
   también `db/portal/003_comet_followup.sql` (solo esquema `portal`; sin ella esas pantallas
   funcionan con valores por defecto y en solo lectura). Ver
   [Seguimiento deportivo COMET](comet-seguimiento-deportivo.md).
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

- Testear login real y las pantallas de COMET/scouting con el admin.
- Testear scout, URL/estado manipulado, caché COMET previamente cargada, informe
  ajeno/propio/migrado, cuentas desactivadas, cambios de rol y último admin.
- Conservar conteos de informes/valoraciones y comprobar que la integración no
  reimporta ni modifica datos deportivos al iniciar.
- Ejecutar pytest con una BD desechable `scouting_test` local para las pruebas SQL;
  nunca usar la conexión de producción en `SCOUTING_TEST_DATABASE_URL`.
- Rollback: detener solo el servicio portal y conservar la web anterior. No borrar
  esquemas, cuentas, imágenes ni informes para deshacer un cambio de interfaz.

## Procedencia de COMET

`app/comet_dashboard.py` incorpora las cinco pantallas de dataProject/main,
commit `c6a0024b11b2e5b4fd3722017e08aadc101db180`, adaptadas al login común y a la
conexión de lectura exclusiva del admin. No se importan ni duplican los automatismos
de COMET. Los requisitos nuevos del club (partido semanal, rankings, ficha individual,
indicadores, alertas, adelantados, marcas y resumen semanal) están descritos en
[Seguimiento deportivo COMET](comet-seguimiento-deportivo.md); leen COMET con la misma
conexión de solo lectura y no modifican `dataProject`.

## Estado de los informes antiguos

El administrador anterior completó su migración. El 30/09/2026 se verificaron en
Supabase 109 informes y 2.564 valoraciones. No volver a ejecutar la migración antigua
como parte de este despliegue. Su documentación queda como referencia histórica.
