# Imagem oficial do Python
FROM python:3.12-slim

# Impede que o Python gere arquivos .pyc e permite logs em tempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Instala dependências do sistema necessárias para MySQL e PostgreSQL
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    pkg-config \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências do Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia o projeto para dentro do container
COPY . /app/

# O Railway injeta a porta automaticamente, mas deixamos a 8000 como padrão
EXPOSE 8000

# Comando para produção usando Gunicorn (já presente no seu requirements.txt)
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]