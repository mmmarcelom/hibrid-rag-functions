import uuid
import os
from typing import List, Optional
from datetime import datetime, timezone
from supabase import create_client, Client
from classes.models import Message, Conversation, Publication

class SupabaseManager:
    def __init__(self, url: str, key: str, tenant_id: str = None):
        self.url = url
        self.key = key
        self.tenant_id = tenant_id or "00000000-0000-0000-0000-000000000000"
        self._client = None
        self._initialize()

    def _initialize(self):
        """Inicializa o cliente Supabase."""
        try:
            self.supabase = create_client(self.url, self.key)
            # Definir contexto do tenant_id para RLS
            if self.tenant_id:
                self._set_tenant_context()
        except Exception as e:
            print(f"❌ Erro ao inicializar cliente Supabase: {e}")
            raise ConnectionError(f"Erro ao conectar ao Supabase: {e}")

    def _set_tenant_context(self):
        """Define o contexto do tenant_id na sessão do Supabase."""
        if not self.tenant_id:
            return
            
        try:
            # Tentar usar a função set_config se disponível
            self.supabase.rpc('set_config', {
                'name': 'app.tenant_id',
                'value': str(self.tenant_id)
            }).execute()
            print(f"✅ Contexto do tenant definido: {self.tenant_id}")
        except Exception as e:
            # Se a função não existir, apenas logar o aviso
            if 'set_config' in str(e) or 'PGRST202' in str(e):
                print(f"⚠️ Função set_config não disponível, continuando sem contexto de tenant")
            else:
                print(f"⚠️ Erro ao definir contexto do tenant: {e}")
            # Continuar mesmo sem definir o contexto


    def message_to_json(self, message: Message) -> dict:
        """Converte uma mensagem para o formato JSON do Supabase."""
        return {
            "id": message.id,
            "tenant_id": message.tenant_id,
            "conversation_id": message.conversation_id or None,
            "platform": message.platform,
            "sender": message.sender,
            "receiver": message.receiver,
            "sender_name": message.sender_name,
            "message_type": message.message_type,
            "content": message.content,
            "metadata": message.metadata or {},
            "direction": message.direction,
            "crm_source": message.crm_source,
            "timestamp": message.timestamp.isoformat() if message.timestamp else None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    def save_message(self, message: Message):
        try:            
            message_data = self.message_to_json(message)
            result = self.supabase.table("messages").insert(message_data).execute()
            return result.data[0]["id"]
        except Exception as e:
            print(f"❌ Erro ao salvar mensagem: {e}")
            raise ConnectionError(f"Erro ao salvar mensagem no Supabase: {e}")

    def get_or_create_conversation(self, message: Message) -> Conversation:
        try:
            result = self.supabase.table("conversations").select("*").eq("tenant_id", message.tenant_id).eq("identification", message.sender).order("created_at", desc=True).limit(1).execute()
            if result.data:
                conversation_data = result.data[0]
                conversation = Conversation(
                    id=conversation_data["id"],
                    tenant_id=conversation_data["tenant_id"],
                    identification=conversation_data["identification"],
                    platform=conversation_data["platform"],
                    crm_source=conversation_data["crm_source"],
                    created_at=conversation_data["created_at"],
                    updated_at=conversation_data["updated_at"],
                    ia_active=conversation_data.get("ia_active", True)
                )
                print(f"✅ Conversa existente encontrada: {conversation.id}")
                return conversation
            else:

                conversation_data = {
                    "tenant_id": message.tenant_id,
                    "identification": message.sender,
                    "platform": message.platform,
                    "crm_source": message.crm_source,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                result = self.supabase.table("conversations").insert(conversation_data).execute()
                new_conversation_data = result.data[0]
                conversation = Conversation(
                    id=new_conversation_data["id"],
                    tenant_id=new_conversation_data["tenant_id"],
                    identification=new_conversation_data["identification"],
                    platform=new_conversation_data["platform"],
                    crm_source=new_conversation_data["crm_source"],
                    created_at=new_conversation_data["created_at"],
                    updated_at=new_conversation_data["updated_at"],
                    ia_active=new_conversation_data.get("ia_active", True)
                )
                print(f"✅ Nova conversa criada: {conversation.id}")
                return conversation
        except Exception as e:
            print(f"❌ Erro ao gerenciar conversa: {e}")
            raise ConnectionError(f"Erro ao gerenciar conversa no Supabase: {e}")


    
    def get_conversation_history(self, conversation_id: str, tenant_id: str) -> List[Message]:
        """Obtém o histórico de mensagens de uma conversa em ordem cronológica."""
        try:
            result = self.supabase.table("messages").select("*").eq("conversation_id", conversation_id).eq("tenant_id", tenant_id).order("created_at", desc=False).execute()
            return [Message(**msg) for msg in result.data]
        except Exception as e:
            print(f"❌ Erro ao obter histórico de mensagens: {e}")
            raise ConnectionError(f"Erro ao obter histórico de mensagens no Supabase: {e}")
    
    def get_unprocessed_messages(self, identification: str, tenant_id: str) -> List[Message]:
        """Obtém mensagens não processadas (sem conversation_id) para um usuário."""
        try:
            result = (
                self.supabase.table("messages")
                .select("*")
                .eq("sender", identification)
                .eq("tenant_id", tenant_id)
                .is_("conversation_id", "null")
                .order("created_at", desc=True)
                .execute())
            return [Message(**msg) for msg in result.data]
        except Exception as e:
            print(f"❌ Erro ao obter mensagens não processadas: {e}")
            raise ConnectionError(f"Erro ao obter mensagens não processadas no Supabase: {e}")
    
    def update_messages_conversation_id(self, message_ids: List[str], conversation_id: str, tenant_id: str):
        """Atualiza o conversation_id de múltiplas mensagens."""
        try:
            result = self.supabase.table("messages").update({"conversation_id": conversation_id}).in_("id", message_ids).eq("tenant_id", tenant_id).execute()
            print(f"✅ {len(message_ids)} mensagens atualizadas com conversation_id: {conversation_id}")
            return result
        except Exception as e:
            print(f"❌ Erro ao atualizar conversation_id das mensagens: {e}")
            raise ConnectionError(f"Erro ao atualizar conversation_id das mensagens no Supabase: {e}")

    def process_conversation_for_publication(self, message_id: str, tenant_id: str):
        """Processa uma conversa para publicação no Pub/Sub."""
        try:
            # 1. Obter mensagem pelo message_id
            message_result = self.supabase.table("messages").select("*").eq("id", message_id).eq("tenant_id", tenant_id).execute()
            
            if not message_result.data:
                raise ValueError(f"Mensagem não encontrada: {message_id}")
            
            message_data = message_result.data[0]
            message = Message(**message_data)
            
            # 2. Obter ou criar conversa
            conversation = self.get_or_create_conversation(message)
            
            # 3. Obter mensagens não processadas
            buffer_messages = self.get_unprocessed_messages(message.sender, tenant_id)
            
            if not buffer_messages:
                raise ValueError(f"Nenhuma mensagem não processada encontrada para identificação: {message.sender}")
            
            # 4. Atualizar conversation_id das mensagens
            message_ids = [msg.id for msg in buffer_messages]
            self.update_messages_conversation_id(message_ids, conversation.id, tenant_id)
            
            # 5. Obter histórico da conversa
            conversation_history = self.get_conversation_history(conversation.id, tenant_id)
            
            # 6. Atualizar conversation_id nas mensagens do buffer
            for msg in buffer_messages:
                msg.conversation_id = conversation.id
            
            print(f"✅ Conversa processada: {conversation.id}, {len(buffer_messages)} mensagens no buffer, {len(conversation_history)} no histórico")
            
            return conversation, buffer_messages, conversation_history
            
        except Exception as e:
            print(f"❌ Erro ao processar conversa para publicação: {e}")
            raise ConnectionError(f"Erro ao processar conversa para publicação no Supabase: {e}")

    def get_tenant_config(self, tenant_id: str) -> dict:
        """Obtém as configurações específicas de um tenant."""
        try:
            result = self.supabase.table("tenant_configs").select("*").eq("tenant_id", tenant_id).execute()
            if result.data:
                config = result.data[0]
                print(f"✅ Configurações do tenant carregadas: {config['pubsub_topic_processing']}")
                return config
            else:
                print(f"⚠️ Configurações do tenant não encontradas: {tenant_id}")
                return None
        except Exception as e:
            print(f"❌ Erro ao obter configurações do tenant: {e}")
            return None

    def get_tenant_name(self, tenant_id: str) -> str:
        """Obtém o nome do cliente a partir do tenant_id."""
        try:
            result = self.supabase.table("tenants").select("slug").eq("id", tenant_id).execute()
            if result.data:
                slug = result.data[0]['slug']
                print(f"✅ Nome do cliente obtido: {slug}")
                return slug
            else:
                print(f"⚠️ Tenant não encontrado: {tenant_id}")
                return "default"
        except Exception as e:
            print(f"❌ Erro ao obter nome do tenant: {e}")
            return "default"

    def tenant_exists(self, tenant_id: str) -> bool:
        """Verifica se um tenant_id existe no banco de dados."""
        try:
            print(f"🔍 Verificando se tenant_id existe: {tenant_id}")
            print(f"🔑 URL do Supabase: {self.url}")
            print(f"🔑 Chave anônima configurada: {'Sim' if self.key else 'Não'}")
            
            # Teste 1: Consulta direta (pode ser bloqueada por RLS)
            try:
                result = self.supabase.table("tenants").select("id").eq("id", tenant_id).execute()
                print(f"📊 Resultado da consulta direta: {result.data}")
                if len(result.data) > 0:
                    print(f"✅ Tenant encontrado via consulta direta")
                    return True
            except Exception as e:
                print(f"⚠️ Erro na consulta direta (possível RLS): {e}")
            
            # Teste 2: Consulta com RPC (bypass RLS)
            try:
                result = self.supabase.rpc('get_tenant_by_id', {'tenant_id_param': tenant_id}).execute()
                print(f"📊 Resultado da consulta RPC: {result.data}")
                if len(result.data) > 0:
                    print(f"✅ Tenant encontrado via RPC")
                    return True
            except Exception as e:
                print(f"⚠️ Erro na consulta RPC: {e}")
            
            # Teste 3: Consulta com SQL direto
            try:
                result = self.supabase.table("tenants").select("*").execute()
                print(f"📋 Todos os tenants (se RLS permitir): {len(result.data)}")
                for tenant in result.data:
                    print(f"   - Tenant: {tenant['id']} | {tenant['name']}")
                    if tenant['id'] == tenant_id:
                        print(f"✅ Tenant encontrado na lista completa")
                        return True
            except Exception as e:
                print(f"⚠️ Erro ao listar todos os tenants: {e}")
            
            print(f"❌ Tenant não encontrado em nenhuma consulta")
            return False
            
        except Exception as e:
            print(f"❌ Erro ao verificar tenant_id no banco: {e}")
            raise ConnectionError(f"Erro ao verificar tenant_id no Supabase: {e}") 