import functions_framework
from flask import request, jsonify
import os
import json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
from models import Publication, Message, Conversation

from supabase import SupabaseManager
from message_processor import WebhookProcessor

from google.cloud import tasks_v2

def get_tenant_id_from_request(request) -> str:
    """Extrai o tenant_id da requisição via header, query param ou subdomain"""
    
    # 1. Tentar via header X-Tenant-ID
    tenant_id = request.headers.get('X-Tenant-ID')
    if tenant_id:
        print(f"✅ Tenant ID encontrado via header: {tenant_id}")
        return tenant_id
    
    # 2. Tentar via query parameter
    tenant_id = request.args.get('tenant_id')
    if tenant_id:
        print(f"✅ Tenant ID encontrado via query param: {tenant_id}")
        return tenant_id
    
    # 3. Tentar via subdomain (ex: tenant1.seudominio.com)
    host = request.headers.get('Host', '')
    if '.' in host:
        subdomain = host.split('.')[0]
        if subdomain not in ['www', 'api', 'app']:
            print(f"✅ Tenant ID encontrado via subdomain: {subdomain}")
            return subdomain
    
    # 4. Usar tenant padrão
    default_tenant = "00000000-0000-0000-0000-000000000000"
    print(f"⚠️ Usando tenant padrão: {default_tenant}")
    return default_tenant

@functions_framework.http
def message_receiver(request):
    """Função router que recebe webhooks de diferentes CRMs e padroniza as mensagens."""
    
    # Detectar tenant_id
    tenant_id = get_tenant_id_from_request(request)
    
    webhook = WebhookProcessor(request)
    
    # Retorna sucesso para requisições OPTIONS
    if webhook.method == 'OPTIONS':
        return ('', 204, { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'POST', 'Access-Control-Allow-Headers': 'Content-Type' })
    
    # Retorna erro para métodos diferentes de POST
    if webhook.method != 'POST': 
        return jsonify({"error": f"Método {request.method} não é suportado"}), 405
    
    # Retorna erro se houver problema na validação
    if webhook.error is not None:
        return jsonify({"error": "Erro na validação da request", "details": str(webhook.error)}), 400

    if webhook.message is None:
        return jsonify({"error": "Nenhum conteúdo para processar"}), 200

    # Converte o webhook para a mensagem padronizada
    incomming_message = webhook.message
    
    # Adicionar tenant_id à mensagem
    incomming_message.tenant_id = tenant_id
    
    print(f"📨 Mensagem recebida para tenant {tenant_id}: {incomming_message}")

    # Carrega o Supabase com tenant_id
    supabase = SupabaseManager(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'), tenant_id)
    
    # Salva a mensagem sem conversation_id (será definido pelo message_buffer)
    supabase.save_message(incomming_message)

    # Agendar task para processamento com buffer de 6 segundos
    # Usuário será criado/buscado no message_buffer
    return schedule_processing_task(incomming_message.sender, tenant_id)

def schedule_processing_task(identification: str, tenant_id: str):
    """Agenda uma task para processamento com buffer de 6 segundos"""
    
    try:
        # No Cloud Functions, usar as credenciais padrão do ambiente
        client = tasks_v2.CloudTasksClient()
        print("✅ Usando credenciais padrão do Google Cloud")
        
    except Exception as e:
        print(f"❌ Erro ao inicializar Cloud Tasks client: {str(e)}")
        return jsonify({"error": f"Erro de credenciais: {str(e)}"}), 500
        
    try:
        # Configurar queue e projeto
        project_id = os.getenv('GOOGLE_PROJECT_ID')
        queue_id = os.getenv('CLOUD_TASKS_QUEUE_ID', 'message-processing-queue')
        location_id = os.getenv('CLOUD_TASKS_LOCATION', 'us-central1')
        
        # Construir caminho da queue
        queue_path = client.queue_path(project_id, location_id, queue_id)
        
        # Cancelar task existente para este usuário (se houver)
        cancel_existing_task(client, queue_path, identification, tenant_id)
        
        # Criar payload da task
        task_payload = { 
            "identification": identification,
            "tenant_id": tenant_id
        }
        
        # Configurar task
        task = {
            'http_request': {
                'http_method': tasks_v2.HttpMethod.POST,
                'url': os.getenv('MESSAGE_BUFFER_URL'),  # URL do message buffer
                'headers': { 'Content-Type': 'application/json' },
                'body': json.dumps(task_payload).encode()
            },
            'schedule_time': { 'seconds': int(datetime.now().timestamp()) + 6  }
        }
        
        # Criar task
        response = client.create_task(request={"parent": queue_path, "task": task})
        
        print(f"✅ Task agendada para identificação {identification} (tenant: {tenant_id}): {response.name}")
        
        # Retornar resposta de sucesso
        response_data = { 
            "status": "success",
            "message": "Webhook processado e task agendada com sucesso",
            "task_id": response.name,
            "identification": identification,
            "tenant_id": tenant_id,
            "scheduled_time": datetime.now().isoformat()
        }
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"❌ Erro ao agendar task: {str(e)}")
        return jsonify({"error": f"Erro ao agendar task: {str(e)}"}), 500

def cancel_existing_task(client, queue_path: str, identification: str, tenant_id: str):
    """Cancela task existente para a identificação"""
    
    try:
        # Listar tasks na queue
        request = tasks_v2.ListTasksRequest(parent=queue_path)
        page_result = client.list_tasks(request=request)
        
        for task in page_result:
            # Verificar se a task é para a mesma identificação e tenant
            if task.http_request.body:
                try:
                    task_data = json.loads(task.http_request.body.decode())
                    if (task_data.get("identification") == identification and 
                        task_data.get("tenant_id") == tenant_id):
                        # Cancelar task existente
                        client.delete_task(name=task.name)
                        print(f"🔄 Task cancelada para identificação {identification} (tenant: {tenant_id}): {task.name}")
                        break
                except:
                    continue
                    
    except Exception as e:
        print(f"⚠️ Erro ao cancelar task existente: {e}")
        # Não falhar se não conseguir cancelar