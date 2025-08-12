import functions_framework
from flask import request, jsonify
import os
import json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from classes.models import Publication, Message, Conversation
from classes.supabase_manager import SupabaseManager
from classes.pubsub_manager import PubSubManager

@functions_framework.http
def message_processor(request):
    """Função que processa mensagens e publica no Pub/Sub."""
    
    # Retorna erro para métodos diferentes de POST
    if request.method != 'POST':
        return jsonify({"error": f"Método {request.method} não é suportado"}), 405
    
    try:        
        # Obter dados da task
        task_data = request.get_json()
        if not task_data:
            return jsonify({"error": "Dados da task não fornecidos"}), 400
        
        message_id = task_data.get("message_id")
        tenant_id = task_data.get("tenant_id")
        
        if not message_id:
            return jsonify({"error": "message_id é obrigatório"}), 400
        
        if not tenant_id:
            return jsonify({"error": "tenant_id é obrigatório"}), 400
        
        print(f"🔄 Processando task para message_id: {message_id} (tenant: {tenant_id})")
        
        # Conectar ao Supabase com tenant_id
        supabase = SupabaseManager(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'), tenant_id)
        
        # Obter configurações específicas do tenant
        tenant_config = supabase.get_tenant_config(tenant_id)
        
        # Processar conversa para publicação
        try:
            # Usar método encapsulado da SupabaseManager
            conversation, buffer_messages, conversation_history = supabase.process_conversation_for_publication(message_id, tenant_id)
            
            # Criar publication com nova estrutura
            publication = Publication(
                tenant_id=tenant_id,
                conversation=conversation, 
                buffer_messages=buffer_messages,
                conversation_history=conversation_history
            )
            
            # Publicar no Pub/Sub usando configurações do tenant
            pubsub = PubSubManager()
            
            # Usar topic específico do tenant se disponível
            topic_name = None
            if tenant_config and tenant_config.get('pubsub_topic_processing'):
                topic_name = tenant_config['pubsub_topic_processing']
                print(f"📡 Usando topic específico do tenant: {topic_name}")
            
            result = pubsub.publish_publication(publication, topic_name)
            
            # Retornar resposta de sucesso
            return jsonify({
                "status": "success",
                "message": "Task processada e publicação enviada com sucesso",
                "publication_id": result["publication_id"],
                "message_id": result["message_id"],
                "topic": result["topic"],
                "tenant_id": publication.tenant_id,
                "conversation_id": publication.conversation.id,
                "buffer_messages_count": len(publication.buffer_messages) if publication.buffer_messages else 0,
                "conversation_history_count": len(publication.conversation_history) if publication.conversation_history else 0
            }), 200
            
        except ValueError as e:
            print(f"❌ Erro de validação: {e}")
            return jsonify({"error": str(e)}), 404
        except Exception as e:
            print(f"❌ Erro ao processar conversa: {e}")
            return jsonify({"error": f"Erro ao processar conversa: {str(e)}"}), 500
            
    except Exception as e:
        print(f"❌ Erro geral no message processor: {e}")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500 