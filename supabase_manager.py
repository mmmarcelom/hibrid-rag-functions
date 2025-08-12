import uuid
from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal, List
from datetime import datetime, timezone
from supabase import create_client, Client
from models import Message, Conversation

class SupabaseManager:
    def __init__(self, url: str, key: str, tenant_id: str = None):
        self.url = url
        self.key = key
        self.tenant_id = tenant_id or "00000000-0000-0000-0000-000000000000"  # Tenant padrão
        self._client = None
        self._initialize()
    
    def _initialize(self): 
        """Inicializa conexão com Supabase"""
        if self._client is not None:
            return True
            
        try:
            self._client = create_client(self.url, self.key)
            # Testar conexão
            self._client.table("conversations").select("id").limit(1).execute()
            print("✅ Conexão com Supabase estabelecida com sucesso")
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar com Supabase: {e}")
            raise ConnectionError(f"Não foi possível conectar ao Supabase: {e}")
    
    @property
    def supabase(self) -> Client:
        """Retorna o cliente Supabase"""
        if self._client is None:
            raise ConnectionError("Supabase não foi inicializado. Chame initialize() primeiro.")
        return self._client

    def message_to_json(self, message: Message):
        return {
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
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    def save_message(self, message: Message):
        try:            
            message_data = self.message_to_json(message)
            result = self.supabase.table("messages").insert(message_data).execute()
            print(f"✅ Mensagem salva: {result.data[0]['id']}")
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
    
    def process_conversation_for_publication(self, identification: str, tenant_id: str) -> tuple[Conversation, List[Message], List[Message]]:
        """
        Processa uma conversa para publicação no Pub/Sub.
        Retorna a conversa, mensagens do buffer e histórico completo.
        """
        try:
            # 1. Buscar mensagens não processadas (buffer)
            buffer_messages = self.get_unprocessed_messages(identification, tenant_id)
            
            if not buffer_messages:
                raise ValueError("Nenhuma mensagem não processada encontrada")
            
            # 2. Buscar ou criar conversa
            conversation = self.get_or_create_conversation_by_identification(identification, tenant_id)
            
            # 3. Buscar histórico ANTES de atualizar conversation_id
            conversation_history = self.get_conversation_history(conversation.id, tenant_id)
            
            # 4. Atualizar conversation_id das mensagens do buffer
            message_ids = [msg.id for msg in buffer_messages]
            self.update_messages_conversation_id(message_ids, conversation.id, tenant_id)
            
            # Filtrar apenas as últimas 10 mensagens para evitar tokens excessivos
            # Como agora está em ordem cronológica, pegamos os últimos 10
            recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
            
            print(f"✅ Dados processados para publicação:")
            print(f"   - Tenant: {tenant_id}")
            print(f"   - Conversa: {conversation.id}")
            print(f"   - Mensagens do buffer: {len(buffer_messages)}")
            print(f"   - Histórico completo: {len(conversation_history)} mensagens")
            print(f"   - Histórico recente: {len(recent_history)} mensagens")
            
            return conversation, buffer_messages, recent_history
            
        except Exception as e:
            print(f"❌ Erro ao processar conversa para publicação: {e}")
            raise ConnectionError(f"Erro ao processar conversa para publicação no Supabase: {e}")
    
    def get_or_create_conversation_by_identification(self, identification: str, tenant_id: str) -> Conversation:
        """Busca ou cria uma conversa baseada na identificação."""
        try:
            result = self.supabase.table("conversations").select("*").eq("identification", identification).eq("tenant_id", tenant_id).order("created_at", desc=True).limit(1).execute()
            
            if result.data:
                # Conversa existente
                conversation_data = result.data[0]
                conversation = Conversation(
                    id=conversation_data["id"],
                    tenant_id=conversation_data["tenant_id"],
                    identification=conversation_data["identification"],
                    platform=conversation_data["platform"],
                    created_at=conversation_data["created_at"],
                    updated_at=conversation_data["updated_at"],
                    ia_active=conversation_data.get("ia_active", True)
                )
                print(f"✅ Conversa existente encontrada: {conversation.id}")
                return conversation
            else:
                # Buscar mensagens não processadas para determinar a plataforma
                buffer_messages = self.get_unprocessed_messages(identification, tenant_id)
                platform = "wts"  # padrão
                
                if buffer_messages:
                    # Usar a plataforma da primeira mensagem, mas converter "whatsapp" para "wts"
                    raw_platform = buffer_messages[0].platform
                    if raw_platform == "whatsapp":
                        platform = "wts"
                    else:
                        platform = raw_platform
                
                # Criar nova conversa
                conversation_data = {
                    "tenant_id": tenant_id,
                    "identification": identification,
                    "platform": platform,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                result = self.supabase.table("conversations").insert(conversation_data).execute()
                conversation_data = result.data[0]
                conversation = Conversation(
                    id=conversation_data["id"],
                    tenant_id=conversation_data["tenant_id"],
                    identification=conversation_data["identification"],
                    platform=conversation_data["platform"],
                    created_at=conversation_data["created_at"],
                    updated_at=conversation_data["updated_at"],
                    ia_active=conversation_data.get("ia_active", True)
                )
                print(f"✅ Nova conversa criada: {conversation.id}")
                return conversation
                
        except Exception as e:
            print(f"❌ Erro ao buscar ou criar conversa: {e}")
            raise ConnectionError(f"Erro ao buscar ou criar conversa no Supabase: {e}") 