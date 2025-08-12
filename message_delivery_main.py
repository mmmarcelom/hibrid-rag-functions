import functions_framework
from flask import request, jsonify
import os
import json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from classes.models import Message, Conversation, Publication
from classes.delivery_processor import DeliveryProcessor
from classes.supabase_manager import SupabaseManager

@functions_framework.http
def message_delivery(request):
    """Função que recebe mensagens processadas do Pub/Sub e envia para os CRMs."""
    
    # Retorna erro para métodos diferentes de POST
    if request.method != 'POST':
        return jsonify({"error": f"Método {request.method} não é suportado"}), 405
    
    try:
        # Obter dados da publicação
        publication_data = request.get_json()
        if not publication_data:
            return jsonify({"error": "Dados da publicação não fornecidos"}), 400
        
        tenant_id = publication_data.get("tenant_id")
        if not tenant_id:
            return jsonify({"error": "tenant_id é obrigatório"}), 400
        
        print(f"📤 Processando entrega para tenant: {tenant_id}")
        
        # Conectar ao Supabase com tenant_id
        supabase = SupabaseManager(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'), tenant_id)
        
        # Processar publicação
        try:
            # Reconstruir objetos a partir dos dados
            conversation_data = publication_data.get("conversation", {})
            conversation = Conversation(**conversation_data)
            
            buffer_messages_data = publication_data.get("buffer_messages", [])
            buffer_messages = [Message(**msg_data) for msg_data in buffer_messages_data]
            
            conversation_history_data = publication_data.get("conversation_history", [])
            conversation_history = [Message(**msg_data) for msg_data in conversation_history_data]
            
            publication = Publication(
                tenant_id=tenant_id,
                conversation=conversation,
                buffer_messages=buffer_messages,
                conversation_history=conversation_history
            )
            
            # Processar entrega
            return process_delivery(publication, supabase)
            
        except Exception as e:
            print(f"❌ Erro ao processar publicação: {e}")
            return jsonify({"error": f"Erro ao processar publicação: {str(e)}"}), 500
            
    except Exception as e:
        print(f"❌ Erro geral no message delivery: {e}")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

def process_delivery(publication: Publication, supabase: SupabaseManager):
    """Processa a entrega das mensagens para os CRMs."""
    
    try:
        # Inicializar processador de entrega
        delivery_processor = DeliveryProcessor()
        
        # Processar cada mensagem do buffer
        successful_deliveries = 0
        failed_deliveries = 0
        
        for message in publication.buffer_messages:
            try:
                print(f"📤 Enviando mensagem: {message.content[:50]}...")
                
                # Enviar mensagem para o CRM
                success = delivery_processor.send_message(message)
                
                if success:
                    successful_deliveries += 1
                    print(f"✅ Mensagem enviada com sucesso")
                else:
                    failed_deliveries += 1
                    print(f"❌ Falha ao enviar mensagem")
                    
            except Exception as e:
                failed_deliveries += 1
                print(f"❌ Erro ao processar mensagem: {e}")
        
        # Salvar mensagens de resposta no Supabase (se houver)
        # Aqui você pode implementar a lógica para salvar as respostas da IA
        
        # Retornar resultado
        return jsonify({
            "status": "success",
            "message": "Entrega processada com sucesso",
            "tenant_id": publication.tenant_id,
            "conversation_id": publication.conversation.id,
            "total_messages": len(publication.buffer_messages),
            "successful_deliveries": successful_deliveries,
            "failed_deliveries": failed_deliveries,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ Erro ao processar entrega: {str(e)}")
        return jsonify({
            "error": f"Erro ao processar entrega: {str(e)}"
        }), 500