import httpx
import os
from classes.models import Message

class DeliveryProcessor:
    """Classe para envio de mensagens para diferentes CRMs.
    
    Fluxo de entrega:
    1. Recebe uma Message padronizada
    2. Identifica a plataforma (wts, kommo, rd_station)
    3. Envia para o CRM específico usando suas APIs
    4. Retorna True/False indicando sucesso/falha
    
    CRMs suportados:
    - WTS (WhatsApp): Usa WTS API com token de autenticação
    - Kommo (AmoCRM): Implementação básica (placeholder)
    - RD Station: Implementação básica (placeholder)
    
    Configuração:
    - WTS_API_TOKEN: Token de autenticação para WTS API
    - URLs e configurações específicas por CRM
    """
    def __init__(self):
        # Não precisa mais de conversation, pois cada mensagem já tem suas informações
        pass
        
    def send_message(self, message: Message):
        """Envia a mensagem para o CRM baseado na plataforma da mensagem."""
        crm_type = message.crm_source
        
        if crm_type == "wts":
            return self._send_wts_message(message)
        elif crm_type == "kommo":
            return self._send_kommo_message(message)
        elif crm_type == "rd_station":
            return self._send_rd_message(message)
        else:
            print(f"⚠️ CRM não suportado: {crm_type}")
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
