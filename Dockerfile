FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONPATH=/app/src
ENV CHROME_BINARY=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
# Compatibilidad con nombres antiguos
ENV CHROME_BIN=/usr/bin/chromium

# A) Paquetes del sistema: Chromium + ChromeDriver (Debian Bookworm)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        chromium \
        chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Cliente Docker + plugin Compose v2 (lanzar sofascore-worker desde Administración)
RUN apt-get update \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" \
       > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

# B) Copiar dependencias Python (ruta explícita)
COPY requirements.txt /app/requirements.txt

# C) Fallar el build si Selenium no está declarado en el requirements de app
RUN grep -n "selenium" /app/requirements.txt

# D) Instalar dependencias con el Python de la imagen
RUN python -m pip install --no-cache-dir -r /app/requirements.txt

# E) Validar Chromium, ChromeDriver y Selenium
RUN chromium --version \
    && chromedriver --version \
    && python -c "import selenium; print('Selenium', selenium.__version__)"

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0"]
