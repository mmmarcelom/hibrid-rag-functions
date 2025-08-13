#!/usr/bin/env python3
"""
Script melhorado para testar o message_processor localmente
Inclui melhor tratamento de erros e debug
"""

import requests
import json
import sys
from datetime import datetime

def test_message_processor():
    """Testa o message_processor com dados do arquivo sampleWTStaskdata.json"""
    
    try:
        # Carregar dados de teste
        with open('sampleWTStaskdata.json', 'r') as file:
            data = json.load(file)
        
        print("📋 Dados carregados:")
        print(json.dumps(data, indent=2))
        print()
        
        # URL do message_processor local
        url = 'http://127.0.0.1:8081'
        
        print(f"🌐 Enviando para: {url}")
        print(f"📤 Payload: {json.dumps(data, indent=2)}")
        print("-" * 50)
        
        # Fazer requisição
        response = requests.post(url, json=data, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Headers: {dict(response.headers)}")
        print("-" * 50)
        
        if response.status_code == 200:
            print("✅ Sucesso!")
            result = response.json()
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # Salvar resultado em arquivo para análise
            with open('message_processor_result.json', 'w') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print("\n💾 Resultado salvo em: message_processor_result.json")
            
        else:
            print("❌ Erro!")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2, ensure_ascii=False))
            except:
                print(f"Texto da resposta: {response.text}")
                
    except FileNotFoundError:
        print("❌ Arquivo sampleWTStaskdata.json não encontrado!")
        print("💡 Execute primeiro o teste do message_buffer para gerar este arquivo")
        
    except requests.exceptions.ConnectionError:
        print("❌ Erro de conexão!")
        print("💡 Certifique-se de que o message_processor está rodando:")
        print("   functions-framework --target=message_processor --port=8081 --source=message_processor_main.py")
        
    except requests.exceptions.Timeout:
        print("❌ Timeout na requisição!")
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()

def test_with_custom_data(message_id, tenant_id):
    """Testa com dados customizados"""
    
    data = {
        "message_id": message_id,
        "tenant_id": tenant_id,
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"🧪 Teste customizado:")
    print(f"   Message ID: {message_id}")
    print(f"   Tenant ID: {tenant_id}")
    print()
    
    url = 'http://127.0.0.1:8081'
    
    try:
        response = requests.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            print("✅ Sucesso!")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(f"❌ Erro {response.status_code}:")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    print("🚀 Teste Melhorado do Message Processor")
    print("=" * 50)
    
    # Teste principal
    test_message_processor()
    
    print("\n" + "=" * 50)
    print("💡 Para teste customizado, use:")
    print("   test_with_custom_data('seu-message-id', 'seu-tenant-id')")
