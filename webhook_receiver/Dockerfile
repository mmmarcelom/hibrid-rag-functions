# Webhook Receiver - Cloud Function
FROM python:3.11-slim

# Definir variáveis de ambiente
ENV FUNCTION_TARGET=webhook_receiver
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório de trabalho
WORKDIR /app

# Copiar requirements primeiro (para cache)
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código da função
COPY . .

# Verificar se main.py existe
RUN test -f main.py || (echo "main.py não encontrado!" && exit 1)

# Expor porta
EXPOSE 8080

# Comando para executar a função
CMD exec python -m functions_framework --target=$FUNCTION_TARGET --port=$PORT --host=0.0.0.0