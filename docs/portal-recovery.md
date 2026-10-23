# Recuperar el portal con administración y scout

Este modo recupera el acceso a COMET y scouting cuando Supabase Auth no está
disponible pero PostgreSQL sí responde. No evita las cuotas: las lecturas siguen
consumiendo transferencia y Supabase puede restringir también PostgreSQL.

Las contraseñas de recuperación se verifican en el servidor con Argon2id; no se
llama a Supabase Auth. Los usuarios, roles, estado activo y revisión siguen siendo
los registros existentes de `portal.accounts`. No se crean cuentas en la BD ni se
cambian contraseñas de Supabase. No se reutilizan contraseñas de la demo.

| Perfil | Acceso durante recuperación |
|---|---|
| Administración | COMET en consulta, scouting y listado de cuentas |
| Scout | Scouting, incluidos los informes ocultos |

Por defecto las tres conexiones están en solo lectura. Para crear y editar informes,
se habilita explícitamente **solo el escritor de scouting**, conservando los permisos
habituales: scout edita sus informes visibles y gestiona los ocultos; administración
gestiona todos. Los informes se guardan en el mismo esquema `scouting` de Supabase.
COMET, cuentas y configuración siguen en solo lectura. Las sincronizaciones y el
envío de correos no se activan desde este despliegue.

## Administrador del servidor: primera instalación

Ejecutar desde la carpeta del repositorio, **después de fusionar la PR**. Conservar
el `.env.portal` privado existente: contiene las tres conexiones independientes.
No subirlo a Git, enviarlo al navegador ni imprimir `docker compose config`.

```bash
git pull --ff-only origin main
mkdir -p .local_checks/portal-recovery
chmod 700 .local_checks/portal-recovery
```

Añadir al `.env.portal` privado:

```dotenv
PORTAL_RECOVERY_SUPABASE_PROJECT=smjicdkycruyholhlbfd
PORTAL_RECOVERY_CREDENTIALS_FILE=./.local_checks/portal-recovery/credentials.private.json
PORTAL_RECOVERY_SCOUTING_WRITES=1
```

Mantener las conexiones `portal_runtime`, `scouting_runtime` y `comet_reader` del
session pooler de Supabase en puerto 5432 con SSL. No usar el rol `postgres`.

Construir la imagen y elegir **dos contraseñas nuevas de recuperación** mediante
las preguntas de la terminal (12-128 caracteres). Se guardan únicamente hashes y
un secreto de firma en el archivo privado, montado en modo de solo lectura.

```bash
docker compose --env-file .env.portal -f docker-compose.portal-recovery.yml build
docker compose --env-file .env.portal -f docker-compose.portal-recovery.yml run --rm provision-recovery
```

El alta local consulta que `pcalandria@ohigginsfc.cl` siga siendo administrador y
`scouting@ohigginsfc.cl` siga siendo scout activo. Si no coinciden, se detiene.
El archivo debe ser nuevo: nunca sobrescribe credenciales existentes. Entregar las
contraseñas elegidas a sus destinatarios por el canal privado acordado.

Validar **antes de reemplazar el portal**:

```bash
docker compose --env-file .env.portal -f docker-compose.portal-recovery.yml run --rm --no-deps --entrypoint python portal scripts/check_portal_recovery.py
```

Debe terminar con `PASS` para `portal`, `scouting`, `public`, los privilegios del
escritor de scouting y los dos perfiles. El diagnóstico **siempre consulta en solo
lectura**, incluso si la aplicación permitirá escribir. Verifica existencia/permisos
y escribe contadores de acceso en un volumen
local; no hace cambios en Supabase. Si falla, conservar el despliegue anterior.

## Activar y comprobar

El servicio y el proyecto Compose son los mismos del portal habitual: el siguiente
comando reemplaza su contenedor y conserva el volumen local de intentos.

```bash
docker compose --env-file .env.portal -f docker-compose.portal-recovery.yml up -d --build --force-recreate portal
docker compose --env-file .env.portal -f docker-compose.portal-recovery.yml ps
```

Publicar detrás de un proxy con **HTTPS** y soporte WebSocket. El enlace histórico
`http://34.247.191.149:18502` usa HTTP: no transmitir contraseñas por ese enlace.
Mantener `PORTAL_BIND_ADDRESS=127.0.0.1` para que el proxy local sea el punto de acceso.
Si todavía no existe HTTPS, el administrador puede validar mediante un túnel SSH
al puerto local; habilitar el acceso público cuando TLS esté configurado.

Entrar con ambos perfiles y comprobar «Modo recuperación · Scouting operativo»:
administración abre COMET y scouting; scout no dispone de COMET ni Administración.
Scouting ofrece creación y edición según el rol; COMET y cuentas no ofrecen
escrituras. Con `PORTAL_RECOVERY_SCOUTING_WRITES=0`, el rótulo cambia a «Solo consulta»
y también se bloquean las escrituras de scouting. Una respuesta HTTP saludable del
contenedor no demuestra por sí sola que las tres conexiones funcionan.

Los intentos se limitan a cinco por cuenta y quince minutos, y sesenta globales
por ventana. El estado SQLite persiste en `portal_recovery_state` tras recrear el
contenedor. No contiene contraseñas, correos ni datos deportivos. Utilizar una
sola instancia del servicio con su volumen; no usar `down -v` al actualizar.

## Actualizaciones posteriores y retorno al proveedor habitual

Con las credenciales ya creadas:

```bash
git pull --ff-only origin main
docker compose --env-file .env.portal -f docker-compose.portal-recovery.yml up -d --build --force-recreate portal
```

Cuando Supabase Auth vuelva a responder, mantener las claves originales del
`.env.portal` y ejecutar:

```bash
docker compose --env-file .env.portal -f docker-compose.portal.yml up -d --build --force-recreate portal
```

Se vuelve al login y permisos operativos habituales. Los informes creados o editados
permanecen en Supabase; no hay que migrar ni restaurar registros. No existe fallback
automático entre proveedores. Conservar los archivos privados con permisos 600 y
rotarlos si se pierden, comparten fuera del canal acordado o termina este uso temporal.

## Validación antes de desplegar

Las pruebas de crear/editar/restaurar informes se ejecutan únicamente contra
`scouting_test` en PostgreSQL local desechable, con un rol separado para scouting.
Comprueban también la autoría y el bloqueo de COMET para scout. En Supabase se
comprueban lecturas y privilegios sin insertar registros de prueba. Los privilegios
SQL no garantizan por sí solos que cada regla RLS o dato real sea válido; la primera
alta real del club debe verificarse por un usuario autorizado después del despliegue.
