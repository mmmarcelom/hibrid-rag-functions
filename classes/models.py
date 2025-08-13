import uuid
from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal, List
from datetime import datetime, timezone
from supabase import create_client, Client

class Message(BaseModel):
    """Mensagem padronizada para todos os webhooks e sistemas."""
    id: str
    tenant_id: str  # OBRIGATÓRIO - ID do tenant
    conversation_id: Optional[str] = None  # Será definido pelo message_processor
    platform: Literal['whatsapp', 'instagram', 'messenger']
    sender: str
    sender_name: Optional[str] = None
    receiver: str
    content: str
    direction: Literal['incoming', 'outgoing']
    message_type: Literal['text', 'audio', 'video', 'image', 'document']
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    crm_source: Literal['wts', 'kommo', 'rd_station']
    
    class Config:
        extra = "ignore"
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class Conversation(BaseModel):
    """Estrutura para conversas no Supabase."""
    id: str
    tenant_id: str  # OBRIGATÓRIO - ID do tenant
    identification: str
    platform: Literal['whatsapp', 'instagram', 'messenger']
    crm_source: Literal['wts', 'kommo', 'rd_station']
    created_at: str
    updated_at: str
    ia_active: Optional[bool] = True
    
    class Config:
        extra = "ignore"

class Publication(BaseModel):
    """Estrutura para publicação no Pub/Sub com mensagem e contexto."""
    tenant_id: str  # OBRIGATÓRIO - ID do tenant
    conversation: Conversation
    buffer_messages: Optional[List[Message]] = None  # Mensagens recebidas agrupadas pelo buffer
    conversation_history: Optional[List[Message]] = None  # Histórico completo da conversa (inclui respostas anteriores)
    
    class Config:
        extra = "ignore"
