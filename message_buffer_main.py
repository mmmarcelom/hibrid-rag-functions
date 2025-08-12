import functions_framework
from flask import request, jsonify
import os
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

from classes.models import Message
from classes.webhook_processor import WebhookProcessor
from classes.supabase_manager import SupabaseManager
from classes.cloud_tasks_manager import CloudTasksManager

def get_tenant_info_from_request(request) -> tuple[str, str]:
    """Extrai e valida o tenant_id e retorna o slug do tenant."""
    # Verificar se tenant_id está presente
    tenant_id = request.args.get('tenant_id')
    if not tenant_id:
        raise ValueError("tenant_id é obrigatório na URL")
    
    # Verificar se é um UUID válido
    try:
        uuid.UUID(str(tenant_id))
    except ValueError:
        raise ValueError(f"tenant_id deve ser um UUID válido: {tenant_id}")
    
    # Buscar slug do tenant no banco
    try:
        supabase = SupabaseManager(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))
        slug = supabase.get_tenant_name(tenant_id)
        return tenant_id, slug
    except Exception as e:
        raise ValueError(f"Erro ao buscar informações do tenant: {str(e)}")

# ----------------------------------------------------------------------------------------
#                                  MAIN FUNCTION
# ----------------------------------------------------------------------------------------

@functions_framework.http
def message_buffer(request):
    """Função que recebe webhooks dos CRMs e processa as mensagens."""
    # Extrair e validar tenant_id e obter slug da URL
    try:
        tenant_id, slug = get_tenant_info_from_request(request)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    # TODO: Reativar validação quando RLS estiver configurado corretamente
    # # Verificar se tenant existe no banco
    # supabase = SupabaseManager(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))
    # try:
    #     if not supabase.tenant_exists(tenant_id):
    #         return jsonify({"error": f"tenant_id não encontrado no banco de dados: {tenant_id}"}), 400
    # except Exception as e:
    #     return jsonify({"error": f"Erro ao verificar tenant_id no banco: {str(e)}"}), 500
    
    # Processar webhook
    webhook = WebhookProcessor(request, tenant_id)
    
    if webhook.error:
        return jsonify({"error": webhook.error}), 400
    
    if not webhook.message:
        return jsonify({"error": "Nenhuma mensagem válida encontrada no webhook"}), 400
    
    print(f"📨 Mensagem recebida: {webhook.message.id} | Tenant: {tenant_id}")
    
    # Salvar mensagem no Supabase (usando a mesma instância)
    try:
        # TODO: Se RLS estiver ativo, usar SUPABASE_SERVICE_ROLE_KEY em vez de SUPABASE_ANON_KEY
        supabase = SupabaseManager(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))
        supabase.save_message(webhook.message)
    except Exception as e:
        print(f"❌ Erro ao salvar mensagem: {e}")
        return jsonify({"error": f"Erro ao salvar mensagem: {str(e)}"}), 500
    
    # Cancelar task anterior e agendar nova task
    try:
        cloud_tasks = CloudTasksManager()
        cloud_tasks.cancel_existing_task(webhook.message.id, tenant_id, slug, webhook.message.platform)
        task_name = cloud_tasks.schedule_task(webhook.message.id, tenant_id, slug, webhook.message.platform)
        print(f"✅ Task agendada: {task_name}")
    except Exception as e:
        print(f"❌ Erro ao agendar processamento: {e}")
        return jsonify({"error": f"Erro ao agendar processamento: {str(e)}"}), 500
    
    return jsonify({
        "status": "success",
        "message": "Mensagem recebida e processada com sucesso",
        "tenant_id": tenant_id,
        "message_id": webhook.message.id
    }), 200