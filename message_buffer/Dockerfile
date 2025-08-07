# Message Buffer - Cloud Function
FROM python:3.11-slim

# Definir variáveis de ambiente
ENV FUNCTION_TARGET=message_buffer
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
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

# Verificar se arquivos importantes existem
RUN ls -la /app && \
    test -f main.py && \
    test -f models.py && \
    test -f supabase_manager.py

# Expor porta
EXPOSE 8080

# Comando para executar a função (sem health check para debug inicial)
CMD exec python -m functions_framework --target=$FUNCTION_TARGET --port=$PORT --host=0.0.0.0 --debug