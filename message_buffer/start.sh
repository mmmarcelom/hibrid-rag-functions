#!/bin/bash

# Script de startup para Cloud Run
set -e

echo "🚀 Iniciando Message Buffer..."

# Verificar se as variáveis de ambiente estão definidas
if [ -z "$FUNCTION_TARGET" ]; then
    echo "❌ FUNCTION_TARGET não definido"
    exit 1
fi

if [ -z "$PORT" ]; then
    echo "❌ PORT não definido"
    exit 1
fi

echo "✅ Variáveis de ambiente OK"
echo "📋 FUNCTION_TARGET: $FUNCTION_TARGET"
echo "🔌 PORT: $PORT"

# Iniciar a função
echo "🚀 Iniciando functions-framework..."
exec functions-framework --target=${FUNCTION_TARGET} --port=${PORT} --host=0.0.0.0 