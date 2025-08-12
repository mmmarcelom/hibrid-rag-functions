import functions_framework
import os
from dotenv import load_dotenv
load_dotenv()
from models import Message

from supabase import SupabaseManager
from message_processor import DeliveryProcessor

import time
import random
import json

@functions_framework.cloud_event
def message_delivery(cloud_event):
    """Cloud Function ativada por gatilho do Pub/Sub para enviar mensagens aos CRMs"""
    
    try:
        # Carregar variáveis de ambiente
        load_dotenv()
        
        # Conectar ao Supabase
        supabase = SupabaseManager(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))
        print("✅ Conectado ao Supabase")
        
        # Decodificar dados da mensagem do Pub/Sub
        message_data = cloud_event.data.get("message", {})
        if not message_data:
            print("⚠️ Nenhuma mensagem encontrada no evento")
            return
        
        # Decodificar dados da mensagem
        import base64
        if "data" in message_data:
            decoded_data = base64.b64decode(message_data["data"]).decode("utf-8")
            data = json.loads(decoded_data)
        else:
            print("⚠️ Dados da mensagem não encontrados")
            return
        
        print(f"📥 Mensagem recebida do Pub/Sub: {message_data.get('messageId', 'N/A')}")
        
        # Compatibilidade: detectar formato antigo vs novo
        if isinstance(data, list):
            # Formato novo: data é uma lista direta
            messages_data = data
            print(f"📋 Dados da mensagem: {len(messages_data)} mensagens (formato novo)")
        elif isinstance(data, dict) and 'messages' in data:
            # Formato antigo: data é um objeto com chave 'messages'
            messages_data = data.get('messages', [])
            print(f"📋 Dados da mensagem: {len(messages_data)} mensagens (formato antigo)")
        else:
            # Fallback: assumir que data é uma lista
            messages_data = data if isinstance(data, list) else []
            print(f"📋 Dados da mensagem: {len(messages_data)} mensagens (fallback)")
        
        # Processar lista de mensagens
        messageList = [Message(**msg) for msg in messages_data]
        
        if not messageList:
            print("⚠️ Nenhuma mensagem encontrada na publicação")
            return
        
        print(f"🔄 Processando {len(messageList)} mensagens")
        
        # Criar delivery processor
        delivery_processor = DeliveryProcessor()
        
        # Processar cada mensagem com intervalo aleatório
        for index, msg in enumerate(messageList):
            messageInfo = f"🔄 Processando mensagem {index + 1} de {len(messageList)}"
            print(messageInfo)

            try:
                # Salvar mensagem no Supabase
                supabase.save_message(msg)
                print(f"✅ Mensagem {index + 1} salva no Supabase")
            except Exception as e:
                print(f"❌ Erro ao salvar mensagem: {e}")
                # Em caso de erro, a função será executada novamente automaticamente
                raise e
            
            try:
                # Enviar mensagem para o CRM
                delivery_processor.send_message(msg)
                print(f"✅ Mensagem {index + 1} enviada para o CRM")
            except Exception as e:
                print(f"❌ Erro ao enviar mensagem: {e}")
                # Em caso de erro, a função será executada novamente automaticamente
                raise e

            # Aguardar tempo aleatório entre 1 e 3 segundos (exceto na última mensagem)
            if index < len(messageList) - 1:
                sleep_time = random.uniform(1.0, 3.0)
                print(f"⏳ Aguardando {sleep_time:.1f} segundos antes da próxima mensagem...")
                time.sleep(sleep_time)
        
        print(f"✅ Processamento concluído: {len(messageList)} mensagens enviadas")
        
    except Exception as e:
        print(f"❌ Erro geral no message_delivery: {e}")
        # Re-raise para que o Cloud Functions faça retry automático
        raise e