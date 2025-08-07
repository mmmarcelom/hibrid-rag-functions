import functions_framework
from flask import request, jsonify
from dotenv import load_dotenv
from google.cloud import pubsub_v1
from datetime import datetime
from models import Message

class DeliveryProcessor():
    """Classe base para envio de mensagens."""
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
        import httpx
        import os
        
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
            import httpx
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