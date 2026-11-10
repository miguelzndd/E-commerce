FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY comum ./comum
COPY catalogo ./catalogo
COPY pedidos ./pedidos
COPY pagamentos ./pagamentos
COPY usuarios ./usuarios
COPY gateway ./gateway
COPY web ./web

RUN mkdir -p dados

# O comando de cada serviço é definido no docker-compose.yml
