# despliegue/Dockerfile · una sola imagen para el servicio web y las tres tareas (Render; o Docker en Hetzner). C5.
# Se construye desde la carpeta que arma despliegue/preparar_contexto.sh (app/ + herramientas/), que es la raíz del repo.
# Reproduce las rutas del Mac (HOME=/srv/ro, ~/Downloads/…, ~/RO_HERRAMIENTAS) para que los lectores funcionen
# sin tocarlos; config.py permite moverlas con variables si algún día hace falta.
FROM python:3.11-slim-bookworm

ARG CON_NAVEGADOR=1
ENV HOME=/srv/ro \
    TZ=Europe/Madrid \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/navegadores \
    RO_APP=/srv/ro/Downloads/APP_RO_ROLES_Y_PERMISOS_2026-10-02/30_APP_PROTOTIPO

# pg_dump tiene que ser de la versión de la base o MÁS NUEVA: el «postgresql-client» de bookworm es el 15 y se niega a
# volcar una 16 o 17 («server version mismatch»), así que la copia de cada hora fallaría. La base es Supabase (Postgres
# 17 en los proyectos nuevos; mira la versión en Supabase › Settings › Infrastructure): el cliente 17 vuelca 15, 16 y 17.
# Se toma del repositorio oficial.
RUN apt-get update \
 && apt-get install -y --no-install-recommends tzdata ca-certificates openssl rsync curl gnupg \
 && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/pgdg.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/pgdg.gpg] http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
      > /etc/apt/sources.list.d/pgdg.list \
 && apt-get update && apt-get install -y --no-install-recommends postgresql-client-17 \
 && rm -rf /var/lib/apt/lists/*

COPY app/despliegue/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
 && if [ "$CON_NAVEGADOR" = "1" ]; then python -m playwright install --with-deps chromium; fi

RUN useradd --create-home --home-dir /srv/ro --shell /usr/sbin/nologin ro
COPY --chown=ro:ro herramientas/ /srv/ro/RO_HERRAMIENTAS/
COPY --chown=ro:ro app/ /srv/ro/Downloads/APP_RO_ROLES_Y_PERMISOS_2026-10-02/30_APP_PROTOTIPO/
RUN chmod +x /srv/ro/Downloads/APP_RO_ROLES_Y_PERMISOS_2026-10-02/30_APP_PROTOTIPO/despliegue/entrada.sh

USER ro
WORKDIR /srv/ro/Downloads/APP_RO_ROLES_Y_PERMISOS_2026-10-02/30_APP_PROTOTIPO
# Render da el puerto en $PORT; servir.py lo lee en modo servidor (RO_MODO=servidor).
EXPOSE 10000
HEALTHCHECK --interval=60s --timeout=5s CMD python3 -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','10000')+'/vivo',timeout=4)" || exit 1
ENTRYPOINT ["despliegue/entrada.sh"]
CMD ["web"]
