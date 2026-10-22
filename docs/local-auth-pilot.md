# Piloto local de autenticación alternativa

Este experimento permite comprobar el acceso al portal sin llamar a Supabase Auth.
**Supabase sigue siendo el proveedor por defecto**. No existe cambio automático de
proveedor cuando una petición falla. El piloto no está preparado para desplegarse
como sustituto de autenticación en el servidor del club.

## Alcance

- Credenciales sintéticas locales, con contraseñas Argon2id y sesiones firmadas de
  una hora mediante ItsDangerous. El archivo privado no guarda roles ni contraseñas
  en claro. Los roles, estado activo y revisión se consultan en `portal.accounts`.
- Admin accede a COMET y scouting. Scout conserva únicamente los permisos de
  scouting, incluidos los informes ocultos según las reglas actuales.
- Cambiar la revisión/estado de una cuenta o sus credenciales invalida las sesiones
  correspondientes. La autorización sigue ejecutándose antes de entregar caché.
- El piloto rechaza conexiones remotas y escucha únicamente en localhost. Utiliza
  el puerto **18503** y una BD local **`portal_pilot`**. Las pruebas usan otra BD,
  **`scouting_test`**, por lo que no eliminan los datos de la demostración.
- La administración de cuentas es de solo lectura. El piloto no crea usuarios de
  Supabase, no cambia sus contraseñas y no migra ni modifica producción.
- Cinco intentos de acceso por usuario cada quince minutos. Este límite es por
  proceso y se reinicia al reiniciar el piloto; no es un limitador distribuido
  apropiado para un servicio público.

Las lecturas deportivas de Supabase continuarían consumiendo cuota si en el futuro
se prepara un proveedor alternativo de producción. Este experimento local no
demuestra disponibilidad futura de Supabase ni elimina sus restricciones actuales.

## Preparar la demostración

Usar una rama de trabajo y un entorno Python independiente:

```bash
python -m venv .venv-pilot
# Activar el entorno según el sistema operativo.
python -m pip install -r requirements-dev.txt
```

Crear una instancia PostgreSQL **local y desechable**, con dos bases:
`scouting_test` para las pruebas y `portal_pilot` vacía para la demostración.
Puede usarse Docker con el puerto publicado solo en `127.0.0.1`. Nunca utilizar
una conexión de Supabase o un volumen que contenga datos del club.

Configurar `PORTAL_PILOT_SETUP_DSN` con una conexión de propietario a `portal_pilot`
en loopback. No pasar contraseñas como argumentos ni subir archivos privados a Git.
Ejecutar desde la raíz:

```bash
python scripts/create_local_auth_pilot.py
python scripts/run_local_auth_pilot.py
```

El primer comando comprueba que el destino es local y está vacío antes de crear
tablas. Genera una mini-competición COMET, dos informes ficticios de scouting y
dos perfiles: `admin@pilot.test` y `scout@pilot.test`. Conserva el esquema y las
comprobaciones de permisos del portal. Reutiliza datos sintéticos de la suite;
no descarga información de COMET, Sofascore ni Supabase.

Los archivos generados quedan excluidos de Git en `.local_checks/local-auth-pilot/`:

- `credentials.private.json`: hashes de contraseña y secreto de firma.
- `environment.private.json`: conexiones locales y selección del proveedor.
- `access.private.txt`: cuentas y contraseñas aleatorias para probar la demo.

El segundo comando abre el servidor en <http://127.0.0.1:18503/>. La interfaz indica
«Piloto local · Datos sintéticos». El launcher evita heredar conexiones de producción.
En Windows, conservar estos archivos dentro de la cuenta privada del operador;
los permisos POSIX no sustituyen las ACL de NTFS.

## Validar y volver a la versión habitual

Ejecutar pytest con `SCOUTING_TEST_DATABASE_URL` apuntando únicamente a la BD
`scouting_test` de loopback. La suite cubre credenciales incorrectas, expiración,
manipulación, cambio de rol/estado, cierre de sesión, aislamiento admin/scout,
bloqueo de destinos remotos y continuidad del proveedor Supabase por defecto.

En el navegador, probar el login con ambas cuentas, COMET como admin y scouting
como scout. No utilizar cuentas ni contraseñas productivas para esta demostración.

Para abandonar el piloto, detener su proceso local. El despliegue habitual sigue
usando `supabase` y no necesita restaurar datos ni contraseñas. No copiar el archivo
de entorno del piloto a `.env.portal` del servidor del club. La imagen Docker
productiva no instala estas dependencias opcionales ni incorpora las credenciales.

Bibliotecas: [Argon2](https://argon2-cffi.readthedocs.io/en/stable/howto.html) e
[ItsDangerous](https://itsdangerous.palletsprojects.com/en/stable/url_safe/).
