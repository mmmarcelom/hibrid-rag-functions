import os
import json
from datetime import datetime, timezone
from google.cloud import tasks_v2
from google.oauth2 import service_account

class CloudTasksManager:
    def __init__(self):
        """Inicializa o cliente do Cloud Tasks."""
        try:
            # Verificar se estamos em desenvolvimento (arquivo service-account.json existe)
            if os.path.exists('service-account.json'):
                print("🔧 Usando credenciais de desenvolvimento (service-account.json)")
                credentials = service_account.Credentials.from_service_account_file(
                    'service-account.json',
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                self.client = tasks_v2.CloudTasksClient(credentials=credentials)
            else:
                print("🔧 Usando credenciais de produção (Cloud Run)")
                self.client = tasks_v2.CloudTasksClient()
        except Exception as e:
            print(f"❌ Erro ao inicializar Cloud Tasks client: {str(e)}")
            raise e
        
        # Configurações
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        if not self.project_id:
            print("⚠️ GOOGLE_CLOUD_PROJECT não configurado, tentando detectar automaticamente...")
            try:
                # Tentar detectar projeto automaticamente
                from google.auth import default
                credentials, project = default()
                self.project_id = project
            except Exception as e:
                print(f"❌ Não foi possível detectar projeto automaticamente: {e}")
                raise ValueError("GOOGLE_CLOUD_PROJECT não configurado e não foi possível detectar automaticamente")
        
        self.location = "southamerica-east1"
    
    def cancel_existing_task(self, message_id: str, tenant_id: str, slug: str, platform: str = None):
        """Cancela task existente para o mesmo message_id e tenant_id."""
        try:
            queue_id = f"{slug}-{platform}" if platform else f"{slug}-default"
            parent = self.client.queue_path(self.project_id, self.location, queue_id)
            
            # Listar tasks na queue
            request = tasks_v2.ListTasksRequest(parent=parent)
            page_result = self.client.list_tasks(request=request)
            
            for task in page_result:
                # Verificar se a task é para o mesmo message_id e tenant_id
                if task.http_request.body:
                    try:
                        task_data = json.loads(task.http_request.body.decode())
                        if (task_data.get("message_id") == message_id and 
                            task_data.get("tenant_id") == tenant_id):
                            # Cancelar task existente
                            self.client.delete_task(name=task.name)
                            break
                    except:
                        continue
                        
        except Exception as e:
            queue_id = f"{slug}-{platform}" if platform else f"{slug}-default"
            print(f"⚠️ Erro ao cancelar task existente na queue '{queue_id}': {e}")
            # Não falhar se não conseguir cancelar
    
    def schedule_task(self, message_id: str, tenant_id: str, slug: str, platform: str = None):
        """Agenda uma nova task para processar a mensagem."""
        try:
            queue_id = f"{slug}-{platform}" if platform else f"{slug}-default"
            parent = self.client.queue_path(self.project_id, self.location, queue_id)
            
            # Dados da tarefa
            task_data = {
                "message_id": message_id,
                "tenant_id": tenant_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Obter URL do Message Buffer
            message_processor_url = os.getenv('MESSAGE_PROCESSOR_URL')
            
            # Criar a tarefa
            task = {
                'http_request': {
                    'http_method': tasks_v2.HttpMethod.POST,
                    'url': message_processor_url,
                    'headers': {
                        'Content-Type': 'application/json',
                        'X-Tenant-ID': tenant_id
                    },
                    'body': json.dumps(task_data).encode()
                }
            }
            
            # Criar task no Cloud Tasks
            response = self.client.create_task(request={"parent": parent, "task": task})
            return response.name
            
        except Exception as e:
            queue_id = f"{slug}-{platform}" if platform else f"{slug}-default"
            print(f"❌ Erro ao criar tarefa na queue '{queue_id}': {e}")
            raise e
