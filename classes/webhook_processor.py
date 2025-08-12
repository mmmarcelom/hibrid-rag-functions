import uuid
from typing import Dict, Any
from datetime import datetime, timezone
from classes.models import Message

class WebhookProcessor:
    """Classe para processar webhooks de diferentes CRMs.
    
    Fluxo de processamento:
    1. Identifica o tipo de CRM baseado no path, headers ou dados
    2. Converte o webhook para o formato padronizado Message
    3. Valida e processa os dados específicos de cada CRM
    4. Retorna uma Message pronta para ser salva no Supabase
    
    CRMs suportados:
    - WTS (WhatsApp): Identificado por 'wts', 'whatsapp' no path ou 'x-wts-signature' no header
    - Kommo (AmoCRM): Identificado por 'kommo', 'amocrm' no path ou 'x-kommo-signature' no header  
    - RD Station: Identificado por 'rd', 'rdstation', 'conversas' no path ou 'x-rd-signature' no header
    """
    def __init__(self, request, tenant_id: str = None):
        self.request = request
        self.method = request.method
        self.tenant_id = tenant_id or "00000000-0000-0000-0000-000000000000"
        self.error = None
        
        try:
            self.crm_type = self._identify_crm_type()
            self.message = self._parse_webhook()
        except Exception as e:
            self.error = str(e)

    def _identify_crm_type(self) -> str:
        """Identifica o tipo de CRM baseado no path ou headers."""
        try:
            # Verificar path da URL
            path = self.request.path.strip('/').lower()
            
            if 'wts' in path or 'whatsapp' in path:
                return "wts"
            elif 'kommo' in path or 'amocrm' in path:
                return "kommo"
            elif 'rd' in path or 'rdstation' in path or 'conversas' in path:
                return "rd_station"
            
            # Verificar headers específicos
            headers = self.request.headers
            if 'x-wts-signature' in headers:
                return "wts"
            elif 'x-kommo-signature' in headers:
                return "kommo"
            elif 'x-rd-signature' in headers:
                return "rd_station"
            
            # Verificar dados do webhook para identificar
            request_json = self.request.get_json(silent=True)
            if request_json:
                # WTS tem campos específicos
                if 'sessionId' in request_json and 'lastContactMessage' in request_json:
                    return "wts"
                # Kommo tem campos específicos
                elif 'lead_id' in request_json or 'pipeline_id' in request_json:
                    return "kommo"
                # RD tem campos específicos
                elif 'contact_id' in request_json or 'funnel_id' in request_json:
                    return "rd_station"

            raise ValueError("CRM não suportado")

        except Exception as e:
            raise Exception(f"Erro na identificação do CRM: {str(e)}")

    def _parse_webhook(self) -> Message:
        """Converte o webhook para a mensagem padronizada."""

        try:
            # Converte o webhook para JSON
            request_json = self.request.get_json(silent=True)

            # Processar webhook baseado no tipo de CRM
            if self.crm_type == "wts":
                return self._process_wts_webhook(request_json)
            elif self.crm_type == "kommo":
                return self._process_kommo_webhook(request_json)
            elif self.crm_type == "rd_station":
                return self._process_rd_webhook(request_json)
            else:
                raise ValueError(f"Tipo de CRM '{self.crm_type}' não é suportado")

        except Exception as e:
            raise Exception(f"Erro na validação do {self.crm_type}: {str(e)}")

    def _process_wts_webhook(self, data: Dict[str, Any]) -> Message:
        """Processa webhook do WTS (WhatsApp)."""
        
        if data['lastMessage'] is None:
            raise ValueError("Nenhuma mensagem encontrada no webhook WTS")
        
        if data['lastMessage']['type'] != 'TEXT' or data['lastMessage']['text'] == '':
            raise ValueError("Mensagem WTS deve ser do tipo TEXT e não pode estar vazia")
        
        return Message(
            id=str(uuid.uuid4()),  # Gerar UUID único
            tenant_id=self.tenant_id,
            conversation_id="",
            platform="whatsapp",
            sender=data['contact']['phonenumber'].replace("+55|", "").replace("+55", ""),
            sender_name=data['contact']['name'],
            receiver=data['channel']['key'],
            content=data['lastMessage']['text'],
            message_type=data['lastMessage']['type'].lower(),
            direction="incoming",
            timestamp=datetime.fromisoformat(data['lastMessage']['createdAt'].replace('Z', '+00:00')),
            metadata={
                "session_id": data['sessionId'],
                "channel_id": data['channel']['id'],
                "contact_name": data['contact']['name'],
                "message_type": data['lastMessage']['type'],
                "crm": "wts",
                "original_message_id": data['lastMessage']['id'],
                "processed_at": datetime.now(timezone.utc).isoformat()
            },
            crm_source="wts"
        )

    def _process_kommo_webhook(self, data: Dict[str, Any]) -> Message:
        """Processa webhook do Kommo CRM."""
        # Garantir que content não seja None
        content = data.get('content', '')
        if content is None:
            content = ''
        
        return Message(
            id=str(uuid.uuid4()),  # Gerar UUID único
            tenant_id=self.tenant_id,
            conversation_id=data.get('conversation_id', ''),
            platform="whatsapp",  # Kommo usa WhatsApp como plataforma
            sender=data.get('sender', ''),
            sender_name=data.get('sender_name', ''),
            receiver=data.get('receiver', ''),
            content=content,
            message_type=data.get('message_type', 'text'),
            direction="incoming",
            timestamp=datetime.now(timezone.utc) if not data.get('timestamp') else datetime.fromisoformat(data.get('timestamp').replace('Z', '+00:00')),
            metadata={
                "crm": "kommo",
                "lead_id": data.get('lead_id'),
                "pipeline_id": data.get('pipeline_id'),
                "status_id": data.get('status_id'),
                "original_message_id": data.get('message_id'),
                "processed_at": datetime.now(timezone.utc).isoformat()
            },
            crm_source="kommo"
        )
    
    def _process_rd_webhook(self, data: Dict[str, Any]) -> Message:
        """Processa webhook do RD Conversas."""
        # Garantir que content não seja None
        content = data.get('content', '')
        if content is None:
            content = ''
        
        return Message(
            id=str(uuid.uuid4()),  # Gerar UUID único
            tenant_id=self.tenant_id,
            conversation_id=data.get('conversation_id', ''),
            platform="whatsapp",  # RD Station usa WhatsApp como plataforma
            sender=data.get('sender', ''),
            sender_name=data.get('sender_name', ''),
            receiver=data.get('receiver', ''),
            content=content,
            message_type=data.get('message_type', 'text'),
            direction="incoming",
            timestamp=datetime.now(timezone.utc) if not data.get('timestamp') else datetime.fromisoformat(data.get('timestamp').replace('Z', '+00:00')),
            metadata={
                "crm": "rd_station",
                "contact_id": data.get('contact_id'),
                "funnel_id": data.get('funnel_id'),
                "stage_id": data.get('stage_id'),
                "original_message_id": data.get('id'),
                "processed_at": datetime.now(timezone.utc).isoformat()
            },
            crm_source="rd_station"
        )
