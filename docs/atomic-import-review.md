# Primera entrega para revisión: importación Sofascore atómica

## Objetivo y alcance

Una importación CSV fallida no debe retirar la versión publicada anterior ni dejar
jugadores, perfiles, IDs externos o métricas parcialmente escritos. Este cambio se
limita al importador `import_sofascore_player_stats_csv` y a su límite transaccional.
No se conecta a producción, no modifica el esquema y no descarga Sofascore.

## Comportamiento

- El registro de lote `running` se crea antes de la transacción de datos. Un fallo
  ordinario revierte todos los cambios del candidato y registra el lote `failed`
  con `metrics_inserted=0`, `metrics_attempted` y `rolled_back=true`. Los demás
  contadores del lote fallido describen intentos, no cambios persistidos.
- Jugadores, enlaces y métricas se escriben en una única transacción. Las funciones
  de repositorio usadas por el importador aceptan `commit=False`; sus otros
  consumidores conservan el comportamiento anterior por defecto.
- Se interrumpe al primer error de fila. Un CSV vacío o una fila sin métricas se
  rechazan: no se publican como una sustitución válida. El proceso sale con error.
- Solo después de insertar el candidato completo se retiran las métricas de los
  lotes anteriores del mismo proveedor, país, división, competición y temporada.
  El cambio de estados y la publicación se confirman juntos.
- Un advisory lock transaccional serializa las publicaciones del mismo ámbito.
  Otros lectores ven la versión anterior hasta el commit. Las importaciones
  concurrentes de ámbitos distintos siguen sujetas a restricciones de identidad:
  una colisión puede fallar y deberá reintentarse; no se oculta con un rollback
  interno que permitiría continuar con un lote parcial.
- Los datos reales Sofascore sin lote no se borran por coincidencia de texto:
  bloquean el reemplazo y requieren reconciliación explícita. Los demo se conservan.
- `import_dataframe` exige una conexión sin transacción activa para no confirmar
  trabajo ajeno al crear el registro del lote.

## Pruebas reproducibles

La suite de integración aplica `db/init.sql` y todas las migraciones existentes a
un esquema temporal por test en PostgreSQL real. Solo acepta una URL explícita a
localhost y una base llamada `scouting_test`; nunca toma `DB_*` como destino.

```bash
pip install -r requirements-dev.txt
# Configurar PYTHONPATH=src y SCOUTING_TEST_DATABASE_URL en el shell.
# Ejemplo de URL para una base desechable propia:
# postgresql://scouting_test:<password>@127.0.0.1:5432/scouting_test
python -m pytest tests/test_atomic_sofascore_import.py -q
python -m pytest -q
```

Sin `SCOUTING_TEST_DATABASE_URL`, las pruebas PostgreSQL se omiten explícitamente.
El workflow de CI crea su propio servicio PostgreSQL 16 con datos sintéticos y
ejecuta la suite completa sin secretos del club.

Escenarios: fallo después de insertar más de 500 métricas; rollback de perfiles,
jugadores y enlaces; error SQL real; fallos antes y después de marcar completed
pero antes del commit; lectura externa durante la promoción; CSV vacío; fila sin
métricas; reemplazo repetido sin duplicar el conjunto; aislamiento de competición,
país y demo; publishers concurrentes con espera de lock comprobada; datos legacy
sin lote que requieren intervención.

## Qué revisar con Ángel antes de integrar

1. Aprobar la política de rechazar el CSV entero por una fila inválida/sin métricas.
2. Confirmar que el ámbito textual identifica correctamente la competición.
3. Ejecutar las pruebas PostgreSQL e inspeccionar los resultados de fallo inyectado.
4. Revisar si el entorno desplegado contiene métricas reales sin lote o lotes
   parciales antiguos: este cambio no sanea retrospectivamente esos datos.
5. Comprobar en un entorno de prueba el CSV real autorizado y el contrato del
   runner, que debe tratar la salida no-cero del importador como fallo.

## Fuera de esta entrega

No se corrigen rankings, percentiles, homónimos, cobertura, estados masivos de
eventos, checkpoint ni el dry-run del runner. Tampoco se garantiza que otros
escritores respeten este lock. La atomicidad se prueba para este importador, no
para toda la cadena de descarga/publicación de la plataforma.

Los reemplazos exitosos siguen eliminando las métricas de la versión anterior:
no se añade un archivo histórico ni rollback posterior a una publicación válida.
Una terminación abrupta revierte la transacción de PostgreSQL, pero puede dejar
el registro de lote en `running`; su reconciliación queda para otro cambio.
No se ha aplicado este código a producción ni se han saneado lotes existentes.

## Resultado local de esta entrega

116 pruebas pasan y 5 se omiten por sus condiciones de entorno. Las 11 pruebas
de atomicidad se ejecutaron con PostgreSQL 16.15 local, esquema y migraciones
originales y datos exclusivamente sintéticos. Los binarios portables proceden de
[EDB](https://www.enterprisedb.com/download-postgresql-binaries). No se usaron
credenciales, datos ni servicios del club para esta validación.
