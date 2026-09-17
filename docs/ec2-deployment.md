# Despliegue en EC2 sin afectar otras aplicaciones

Esta guía usa `docker-compose.ec2.yml`, pensado para servidores compartidos:

- no expone PostgreSQL en el host;
- usa un puerto de Streamlit configurable;
- evita `container_name` fijos;
- usa un volumen de base de datos propio;
- no monta `/var/run/docker.sock` en la app.

## 1. Preparar variables

En el EC2, dentro del repo clonado:

```bash
cp .env.ec2.example .env
nano .env
```

Cambia como mínimo:

- `DB_PASSWORD`: contraseña larga y única.
- `SCOUTING_APP_PORT`: puerto libre en el servidor, por ejemplo `18501`.

Antes de levantar la app, verifica que el puerto esté libre:

```bash
sudo ss -ltnp | grep ':18501' || true
```

Si aparece otro proceso, cambia `SCOUTING_APP_PORT` en `.env`.

## 2. Validar la configuración

```bash
docker compose -f docker-compose.ec2.yml config -q
python scripts/check_compose_db_credentials.py -f docker-compose.ec2.yml
```

Compose carga `.env` automáticamente; no hace falta `source .env`.
`DB_PASSWORD` se aplica al crear el volumen; cambiarla después no actualiza el rol
(en producción usa `ALTER ROLE`, no borres el volumen).

## 3. Levantar la aplicación

```bash
docker compose -f docker-compose.ec2.yml up -d --build
```

El servicio `db-init` aplica migraciones, carga competiciones e inserta datos demo
si la base aún no tiene métricas reales. No hace falta ejecutar scripts a mano.

El seed demo incluye:

- **Jason León** y **Marcelo Flores** (laterales izquierdos) con informes, atributos y métricas objetivas
- **Cohortes** de defensores laterales para percentiles y radares
- **Jugadores O'Higgins** con datos en temporadas 2024 y 2025 para comparación histórica

Tras el seed, validar en la UI: **Consultar jugador** → Jason León / Marcelo Flores; **Comparación** entre ambos; **Comparación por temporadas** → O'Higgins.

La app quedará disponible en:

```text
http://IP_DEL_EC2:18501
```

Usa el puerto que hayas definido en `SCOUTING_APP_PORT`.

## 4. Ver estado y logs

```bash
docker compose -f docker-compose.ec2.yml ps
docker compose -f docker-compose.ec2.yml logs -f app
```

## 5. Actualizar una versión ya desplegada

```bash
git pull
docker compose -f docker-compose.ec2.yml up -d --build
docker compose -f docker-compose.ec2.yml exec app python scripts/apply_migrations.py
```

No ejecutes `seed_demo_data.py` en una base con datos reales salvo que quieras insertar/actualizar datos demo.

## 6. Reverse proxy recomendado

Si ya tienes Nginx o Caddy en el EC2, apunta tu dominio/subdominio al puerto interno elegido.

Ejemplo Nginx:

```nginx
server {
    server_name scouting.tu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:18501;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Después puedes agregar HTTPS con Certbot si tu servidor ya lo usa.

## 7. Backup básico

```bash
docker compose -f docker-compose.ec2.yml exec postgres pg_dump -U "$DB_USER" "$DB_NAME" > ohiggins_scouting_backup.sql
```

Si tu shell no tiene cargadas las variables de `.env`, usa los valores reales:

```bash
docker compose -f docker-compose.ec2.yml exec postgres pg_dump -U ohiggins_scouting_user ohiggins_scouting_db > ohiggins_scouting_backup.sql
```

## 8. Worker Sofascore

El worker queda disponible solo bajo perfil y no se ejecuta por defecto:

```bash
docker compose -f docker-compose.ec2.yml --profile worker build sofascore-worker
docker compose -f docker-compose.ec2.yml --profile worker run --rm sofascore-worker python scripts/run_all_sofascore_pipeline.py --help
```

Mantén `DISABLE_SOFASCORE_UPDATE=1` en producción si no quieres permitir lanzarlo desde la interfaz.
