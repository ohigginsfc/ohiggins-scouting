# Piloto local con datos reales de Supabase

Prueba opcional de acceso local con los perfiles existentes. No es un despliegue
ni cambia el proveedor habitual de producción. Las lecturas siguen consumiendo
transferencia de Supabase y su disponibilidad debe comprobarse en cada ejecución.

## Preparación

Usar esta rama y las dependencias de `requirements-dev.txt` en un entorno privado.
Tener el archivo privado `.env.portal` con las tres conexiones independientes:
`PORTAL_AUTH_DATABASE_URL`, `SCOUTING_DATABASE_URL` y `COMET_DATABASE_URL`.
Se admiten únicamente los roles `portal_runtime`, `scouting_runtime` y `comet_reader`
del proyecto explícito, mediante session pooler en 5432 y SSL. No usar `postgres`.

Desde la raíz, indicar la ruta del archivo privado, sin escribir claves en comandos:

```bash
python scripts/run_supabase_readonly_pilot.py --env-file /ruta/privada/.env.portal --check-only
python scripts/run_supabase_readonly_pilot.py
```

El primer comando consulta los perfiles activos de administración y scouting,
comprueba `transaction_read_only` en las tres conexiones y obtiene unos pocos
conteos. No crea tablas, usuarios, roles ni registros. Genera contraseñas locales
temporales vinculadas a los identificadores existentes; no cambia Supabase Auth.
Los archivos privados quedan en `.local_checks/supabase-readonly-pilot/`, fuera de Git:
`access.private.txt`, `credentials.private.json`, `environment.private.json` y
`validation.private.json`. Restringir también sus permisos NTFS al operador.

El segundo comando escucha exclusivamente en <http://127.0.0.1:18504/>. La demo
sintética de 18503 puede continuar en paralelo. No exponer el piloto a Internet.

## Comprobaciones

- Administración: entrar en COMET y revisar el resumen; entrar en scouting.
- Scout: ver scouting e informes ocultos; COMET y Administración no están disponibles.
- Los formularios de creación/edición y seguimiento están bloqueados. No hay
  sincronizaciones ni credenciales SMTP/Auth en el proceso.
- Las conexiones abren transacciones de solo lectura, incluso después de commit
  o rollback. La suite demuestra el rechazo de escrituras únicamente en PostgreSQL
  local desechable; nunca se intenta escribir como prueba en Supabase.

La suite mantiene su bloqueo de conexiones externas. No ejecutar pytest con las
conexiones reales. Para terminar, detener exclusivamente el proceso local de 18504;
no hay cambios de producción que restaurar. Este piloto no soluciona la cuota ni
habilita automáticamente una autenticación alternativa en la web pública.
