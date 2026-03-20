# Imagem oficial do Python
FROM python:3.12-slim

# Evita arquivos .pyc e permite logs em tempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Instala dependências do sistema (Necessário para o psycopg2 e mysqlclient)
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    pkg-config \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências do Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia o projeto
COPY . /app/

# Coleta os arquivos estáticos (CSS do admin)
RUN python manage.py collectstatic --noinput

# COMANDO INTELIGENTE:
# Usa 'sh -c' para permitir que a variável $PORT do Railway seja lida corretamente.
CMD sh -c "python manage.py migrate && gunicorn core.wsgi:application --bind 0.0.0.0:${PORT:-8000}"