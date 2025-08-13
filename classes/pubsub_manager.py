import os
import json
from datetime import datetime, timezone
from google.cloud import pubsub_v1
from google.oauth2 import service_account
from classes.models import Publication

class PubSubManager:
    def __init__(self):
        """Inicializa o cliente do Pub/Sub."""
        try:
            if os.path.exists('service-account.json'):
                print("🔧 Usando credenciais de desenvolvimento (service-account.json)")
                credentials = service_account.Credentials.from_service_account_file(
                    'service-account.json',
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                self.publisher = pubsub_v1.PublisherClient(credentials=credentials)
            else:
                print("🔧 Usando credenciais de produção (Cloud Run)")
                self.publisher = pubsub_v1.PublisherClient()
        except Exception as e:
            print(f"❌ Erro ao inicializar Pub/Sub client: {str(e)}")
            raise e
        
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT não configurado")

    def _get_client_name_from_tenant(self, tenant_id: str) -> str:
        """Obtém o nome do cliente a partir do tenant_id."""
        try:
            from classes.supabase_manager import SupabaseManager
            supabase = SupabaseManager(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))
            return supabase.get_tenant_name(tenant_id)
        except Exception as e:
            print(f"⚠️ Erro ao obter nome do cliente: {e}, usando 'default'")
            return "default"

    def publish_publication(self, publication: Publication, topic_name: str = None):
        """Publica uma publication no Pub/Sub."""
        try:
            # Usar topic específico do tenant se não especificado
            if not topic_name:
                # Obter nome do cliente a partir do tenant_id
                client_name = self._get_client_name_from_tenant(publication.tenant_id)
                topic_name = f"{client_name}-processamento"
                
                # Verificar se o topic específico existe, senão usar padrão
                try:
                    topic_path = self.publisher.topic_path(self.project_id, topic_name)
                    # Tentar obter informações do topic para verificar se existe
                    self.publisher.get_topic(request={"name": topic_path})
                    print(f"✅ Usando topic específico do cliente: {topic_name}")
                except Exception:
                    # Topic específico não existe, usar padrão
                    topic_name = "default-processamento"
                    print(f"⚠️ Topic específico não encontrado, usando padrão: {topic_name}")
            
            topic_path = self.publisher.topic_path(self.project_id, topic_name)
            
            # Preparar dados da publication
            publication_data = {
                "tenant_id": publication.tenant_id,
                "conversation": publication.conversation.model_dump(mode='json'),
                "buffer_messages": [msg.model_dump(mode='json') for msg in publication.buffer_messages] if publication.buffer_messages else [],
                "conversation_history": [msg.model_dump(mode='json') for msg in publication.conversation_history] if publication.conversation_history else [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "publication_id": f"pub_{int(datetime.now().timestamp())}"
            }
            
            # Publicar no Pub/Sub
            future = self.publisher.publish(topic_path, json.dumps(publication_data).encode())
            message_id = future.result()  # Aguarda confirmação
            
            print(f"✅ Publication enviada: {publication_data['publication_id']} | Message ID: {message_id} | Topic: {topic_name}")
            return {
                "publication_id": publication_data['publication_id'],
                "message_id": message_id,
                "topic": topic_name
            }
            
        except Exception as e:
            print(f"❌ Erro ao publicar no Pub/Sub: {e}")
            raise e

    def publish_delivery_message(self, message_data: dict, tenant_id: str, topic_name: str = None):
        """Publica uma mensagem de envio no Pub/Sub."""
        try:
            # Usar topic específico do tenant se não especificado
            if not topic_name:
                # Obter nome do cliente a partir do tenant_id
                client_name = self._get_client_name_from_tenant(tenant_id)
                topic_name = f"{client_name}-envio"
                
                # Verificar se o topic específico existe, senão usar padrão
                try:
                    topic_path = self.publisher.topic_path(self.project_id, topic_name)
                    # Tentar obter informações do topic para verificar se existe
                    self.publisher.get_topic(request={"name": topic_path})
                    print(f"✅ Usando topic de envio específico do cliente: {topic_name}")
                except Exception:
                    # Topic específico não existe, usar padrão
                    topic_name = "default-envio"
                    print(f"⚠️ Topic de envio específico não encontrado, usando padrão: {topic_name}")
            
            topic_path = self.publisher.topic_path(self.project_id, topic_name)
            
            # Preparar dados da mensagem de envio
            delivery_data = {
                "tenant_id": tenant_id,
                "message": message_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "delivery_id": f"del_{int(datetime.now().timestamp())}"
            }
            
            # Publicar no Pub/Sub
            future = self.publisher.publish(topic_path, json.dumps(delivery_data).encode())
            message_id = future.result()  # Aguarda confirmação
            
            print(f"✅ Mensagem de envio publicada: {delivery_data['delivery_id']} | Message ID: {message_id} | Topic: {topic_name}")
            return {
                "delivery_id": delivery_data['delivery_id'],
                "message_id": message_id,
                "topic": topic_name
            }
            
        except Exception as e:
            print(f"❌ Erro ao publicar mensagem de envio no Pub/Sub: {e}")
            raise e
    
    def publish_message(self, message_data: dict, topic_name: str = None):
        """Publica dados arbitrários no Pub/Sub."""
        try:
            # Usar topic padrão se não especificado
            if not topic_name:
                topic_name = os.getenv('PUBSUB_TOPIC_TO_PROCESS', 'message-processing')
            
            topic_path = self.publisher.topic_path(self.project_id, topic_name)
            
            # Publicar no Pub/Sub
            future = self.publisher.publish(topic_path, json.dumps(message_data).encode())
            message_id = future.result()  # Aguarda confirmação
            
            print(f"✅ Mensagem publicada | Message ID: {message_id}")
            return message_id
            
        except Exception as e:
            print(f"❌ Erro ao publicar mensagem no Pub/Sub: {e}")
            raise e
