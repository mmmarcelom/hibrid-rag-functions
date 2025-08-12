import uuid
import httpx
import os
from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal, List
from datetime import datetime, timezone
from supabase import create_client, Client
from models import Message

class WebhookProcessor:
    """Classe para processar webhooks de diferentes CRMs."""
    def __init__(self, request):
        self.request = request
        self.method = request.method
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
                return "rd_conversas"
            
            # Verificar headers específicos
            headers = self.request.headers
            if 'x-wts-signature' in headers:
                return "wts"
            elif 'x-kommo-signature' in headers:
                return "kommo"
            elif 'x-rd-signature' in headers:
                return "rd_conversas"
            
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
                    return "rd_conversas"

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
            elif self.crm_type == "rd_conversas":
                return self._process_rd_webhook(request_json)
            else:
                raise ValueError(f"Tipo de CRM '{self.crm_type}' não é suportado")

        except Exception as e:
            raise Exception(f"Erro na validação do {self.crm_type}: {str(e)}")

    def _process_wts_webhook(self, data: Dict[str, Any]) -> Message:
        """Processa webhook do WTS (WhatsApp)."""
        
        if data['lastMessage'] is None:
            return None
        
        if data['lastMessage']['type'] != 'TEXT' or data['lastMessage']['text'] == '':
            return None
        
        return Message(
            id=data['lastMessage']['id'],
            conversation_id="",
            platform="wts",
            sender=data['contact']['phonenumber'].replace("+55|", "").replace("+55", ""),
            sender_name=data['contact']['name'],
            receiver=data['channel']['key'],
            content=data['lastMessage']['text'],
            message_type=data['lastMessage']['type'].lower(),
            direction="incoming",
            timestamp=data['lastMessage']['createdAt'],
            metadata={
                "session_id": data['sessionId'],
                "channel_id": data['channel']['id'],
                "contact_name": data['contact']['name'],
                "message_type": data['lastMessage']['type'],
                "crm": "wts"
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
            id=data.get('message_id', str(datetime.now().timestamp())),
            conversation_id=data.get('conversation_id', ''),
            platform="kommo",
            sender=data.get('sender', ''),
            sender_name=data.get('sender_name', ''),
            receiver=data.get('receiver', ''),
            content=content,
            message_type=data.get('message_type', 'text'),
            direction="incoming",
            timestamp=data.get('timestamp', datetime.now().isoformat()),
            metadata={
                "crm": "kommo",
                "lead_id": data.get('lead_id'),
                "pipeline_id": data.get('pipeline_id'),
                "status_id": data.get('status_id')
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
            id=data.get('id', str(datetime.now().timestamp())),
            conversation_id=data.get('conversation_id', ''),
            platform="rd_conversas",
            sender=data.get('sender', ''),
            sender_name=data.get('sender_name', ''),
            receiver=data.get('receiver', ''),
            content=content,
            message_type=data.get('message_type', 'text'),
            direction="incoming",
            timestamp=data.get('timestamp', datetime.now().isoformat()),
            metadata={
                "crm": "rd_conversas",
                "contact_id": data.get('contact_id'),
                "funnel_id": data.get('funnel_id'),
                "stage_id": data.get('stage_id')
            },
            crm_source="rd_conversas"
        )


class DeliveryProcessor:
    """Classe para envio de mensagens para diferentes CRMs."""
    def __init__(self):
        # Não precisa mais de conversation, pois cada mensagem já tem suas informações
        pass
        
    def send_message(self, message: Message):
        """Envia a mensagem para o CRM baseado na plataforma da mensagem."""
        crm_type = message.platform
        
        if crm_type == "wts":
            return self._send_wts_message(message)
        elif crm_type == "kommo":
            return self._send_kommo_message(message)
        elif crm_type == "rd_conversas":
            return self._send_rd_message(message)
        else:
            print(f"⚠️ Plataforma não suportada: {crm_type}")
            return False

    def _send_wts_message(self, message: Message):
        """Envia a mensagem para o WTS."""
        try:
            # Obter token da API WTS
            api_token = os.getenv('WTS_API_TOKEN')
            if not api_token:
                raise ValueError("WTS_API_TOKEN é obrigatório. Configure a variável de ambiente WTS_API_TOKEN.")
            
            api_url = 'https://api.wts.chat'
            headers = {
                "accept": "application/json",
                "content-type": "application/*+json",
                "Authorization": f"Bearer {api_token}"
            }
            
            print(f"📤 Enviando mensagem via WTS API...")
            
            # Formatar números de telefone para o formato esperado pela WTS API
            to_number = message.receiver
            from_number = message.sender
            
            # Se o número não tem o formato +55, adicionar
            if not to_number.startswith("+55"):
                to_number = f"+55{to_number}"
            if not from_number.startswith("+55"):
                from_number = f"+55{from_number}"
            
            payload = { 
                "body": {"text": message.content}, 
                "to": to_number,
                "from": from_number
            }

            if message.metadata:
                payload["metadata"] = message.metadata

            # Usar httpx de forma síncrona para compatibilidade com Cloud Functions
            with httpx.Client(timeout=30.0) as client:
                url = f"{api_url}/chat/v1/message/send"
                response = client.post(url, json=payload, headers=headers)
                
            if response.status_code == 200:
                print(f"✅ WTS: mensagem enviada com sucesso")
                return True
            else:
                print(f"❌ WTS: erro ao enviar mensagem: {response.status_code} - {response.text}")
                print(f"📡 Response: {response.status_code}, Response text: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ WTS: erro ao enviar mensagem: {e}")
            import traceback
            print(f"📋 Traceback: {traceback.format_exc()}")
            return False
        
    def _send_kommo_message(self, message: Message):
        """Envia a mensagem para o Kommo."""
        print(f"Enviando mensagem para o Kommo: {message.content[:50]}...")

    def _send_rd_message(self, message: Message):
        """Envia a mensagem para o RD Conversas."""
        print(f"Enviando mensagem para o RD Conversas: {message.content[:50]}...")
