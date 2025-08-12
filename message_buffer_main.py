import functions_framework
from flask import request, jsonify
import os
from dotenv import load_dotenv
load_dotenv()
from models import Publication, Message, Conversation

from supabase import SupabaseManager

from datetime import datetime
import json


@functions_framework.http
def message_buffer(request):
    """Cloud Function que processa tasks agendadas e publica no Pub/Sub"""
    
    # Retorna sucesso para requisições OPTIONS
    if request.method == 'OPTIONS':
        return ('', 204, { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'POST', 'Access-Control-Allow-Headers': 'Content-Type'})
    
    # Retorna erro para métodos diferentes de POST
    if request.method != 'POST':
        return jsonify({"error": f"Método {request.method} não é suportado"}), 405
    
    try:        
        # Obter dados da task
        task_data = request.get_json()
        if not task_data:
            return jsonify({"error": "Dados da task não fornecidos"}), 400
        
        identification = task_data.get("identification")
        
        if not identification:
            return jsonify({"error": "identification é obrigatório"}), 400
        
        print(f"🔄 Processando task para identificação: {identification}")
        
        # Conectar ao Supabase
        supabase = SupabaseManager(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))
        
        # Processar conversa para publicação
        try:
            # Usar método encapsulado da SupabaseManager
            conversation, buffer_messages, conversation_history = supabase.process_conversation_for_publication(identification)
            
            # Criar publication com nova estrutura
            publication = Publication(
                conversation=conversation, 
                buffer_messages=buffer_messages,
                conversation_history=conversation_history
            )
            
            # Publicar no Pub/Sub
            return publish_message(publication)
            
        except ValueError as e:
            print(f"❌ Erro de validação: {e}")
            return jsonify({"error": str(e)}), 404
        except Exception as e:
            print(f"❌ Erro ao processar conversa: {e}")
            return jsonify({"error": f"Erro ao processar conversa: {str(e)}"}), 500
            
    except Exception as e:
        print(f"❌ Erro geral no message buffer: {e}")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

def publish_message(publication: Publication):
    """Envia publication com mensagem e contexto para o Pub/Sub"""
    
    try:
        from google.cloud import pubsub_v1
        from google.oauth2 import service_account
        
        # Configurar credenciais
        try:
            # Primeiro tenta usar credenciais padrão (funciona nas cloud functions)
            credentials = None
            print("✅ Usando credenciais padrão do Google Cloud")
        except Exception:
            # Se falhar, tenta usar arquivo local (funciona localmente)
            service_account_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'service-account.json')
            if os.path.exists(service_account_path):
                credentials = service_account.Credentials.from_service_account_file(service_account_path)
                print(f"✅ Usando credenciais do arquivo: {service_account_path}")
            else:
                print("⚠️ Nenhuma credencial encontrada")
                credentials = None
        
        publisher = pubsub_v1.PublisherClient(credentials=credentials)
        topic_path = publisher.topic_path(os.getenv('GOOGLE_PROJECT_ID'), os.getenv('PUBSUB_TOPIC_TO_PROCESS'))
        
        # Preparar dados da publication
        publication_data = {
            "conversation": publication.conversation.model_dump(),
            "buffer_messages": [msg.model_dump() for msg in publication.buffer_messages] if publication.buffer_messages else [],
            "conversation_history": [msg.model_dump() for msg in publication.conversation_history] if publication.conversation_history else [],
            "timestamp": datetime.now().isoformat(),
            "publication_id": f"task_pub_{int(datetime.now().timestamp())}"
        }
        
        # Publicar no Pub/Sub
        publisher.publish(topic_path, json.dumps(publication_data).encode())
        print(f"✅ Publication enviada para Pub/Sub: {publication_data['publication_id']}")

        # Retornar resposta de sucesso
        return jsonify({
            "status": "success",
            "message": "Task processada e publicação enviada com sucesso",
            "publication_id": publication_data['publication_id'],
            "conversation_id": publication.conversation.id,
            "buffer_messages_count": len(publication.buffer_messages) if publication.buffer_messages else 0,
            "conversation_history_count": len(publication.conversation_history) if publication.conversation_history else 0
        }), 200
        
    except Exception as e:
        print(f"❌ Erro ao enviar publication para Pub/Sub: {str(e)}")
        return jsonify({
            "error": f"Erro ao publicar mensagem: {str(e)}"
        }), 500 