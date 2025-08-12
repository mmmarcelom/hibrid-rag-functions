# 🤖 Hibrid RAG Functions - Sistema Multi-Tenant

Sistema de processamento de mensagens com RAG (Retrieval-Augmented Generation) para múltiplos clientes, construído com Google Cloud Functions, Supabase e integração com CRMs.

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CRMs (WTS,    │    │  Message        │    │  Message        │
│   Kommo, RD)    │───▶│  Buffer         │───▶│  Processor      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Supabase      │    │  Pub/Sub        │
                       │   (Multi-Tenant)│    │  (Processing)   │
                       └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │  Message        │
                                               │  Delivery       │
                                               └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │   CRMs (WTS,    │
                                               │   Kommo, RD)    │
                                               └─────────────────┘
```

## 🚀 Deploy no Cloud Run

### Pré-requisitos

1. **Google Cloud Project** configurado
2. **Cloud Build** habilitado
3. **Cloud Run** habilitado
4. **Service Account** com permissões adequadas
5. **Supabase** configurado com estrutura multi-tenant

### 1. Configurar Conectar Repositório

1. Acesse o [Google Cloud Console](https://console.cloud.google.com)
2. Vá para **Cloud Build** → **Triggers**
3. Clique em **"Conectar repositório"**
4. Conecte seu repositório GitHub
5. Configure o trigger para usar o arquivo `cloudbuild.yaml`

### 2. Configurar Variáveis de Ambiente

No Cloud Build Trigger, configure as substituições:

```yaml
_SUPABASE_URL: https://your-project.supabase.co
_SUPABASE_ANON_KEY: your-supabase-anon-key
_CLOUD_TASKS_QUEUE_ID: message-processing-queue
_CLOUD_TASKS_LOCATION: southamerica-east1
_MESSAGE_PROCESSOR_URL: https://message-processor-xxxxx-sae1.a.run.app
_PUBSUB_TOPIC_TO_PROCESS: para-processamento
```

### 3. Configurar Service Account

Crie um Service Account com as seguintes permissões:

```bash
# Criar Service Account
gcloud iam service-accounts create hibrid-rag-sa \
    --display-name="Hibrid RAG Service Account"

# Conceder permissões
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:hibrid-rag-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudtasks.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:hibrid-rag-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/pubsub.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:hibrid-rag-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.admin"

# Configurar Cloud Build para usar o Service Account
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$PROJECT_ID@cloudbuild.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"
```

### 4. Configurar Cloud Run

Configure o Cloud Run para usar o Service Account:

```bash
# Configurar Cloud Run para usar o Service Account
gcloud run services update message-buffer \
    --service-account=hibrid-rag-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --region=southamerica-east1

gcloud run services update message-processor \
    --service-account=hibrid-rag-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --region=southamerica-east1

gcloud run services update message-delivery \
    --service-account=hibrid-rag-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --region=southamerica-east1
```

### 5. Deploy Automático

Após configurar o trigger, cada push para a branch principal irá:

1. **Build** das 3 imagens Docker
2. **Deploy** automático no Cloud Run
3. **Configuração** das variáveis de ambiente
4. **Atualização** das URLs de comunicação

## 📋 Estrutura do Projeto

### 🏗️ Arquitetura Multi-Tenant

O projeto segue uma arquitetura multi-tenant onde cada cliente (tenant) tem:

- **Dados isolados** no Supabase com Row Level Security (RLS)
- **Configurações específicas** por tenant
- **Tópicos Pub/Sub específicos** por cliente
- **Cloud Tasks isoladas** por tenant

### 📡 Tópicos Pub/Sub por Cliente

O sistema usa tópicos específicos por cliente seguindo o formato:

```
{nome_cliente}-processamento  # Para processamento de mensagens
{nome_cliente}-envio          # Para envio de mensagens
```

#### 📋 Exemplos:

| Cliente | Processamento | Envio |
|---------|---------------|-------|
| hubnordeste | `hubnordeste-processamento` | `hubnordeste-envio` |
| cliente2 | `cliente2-processamento` | `cliente2-envio` |
| default | `default-processamento` | `default-envio` |

#### ⚠️ Tópicos Obrigatórios:

Os tópicos padrão são **OBRIGATÓRIOS** e devem ser criados primeiro:

```bash
# Tópicos padrão (obrigatórios)
gcloud pubsub topics create default-processamento --project=SEU_PROJETO_ID
gcloud pubsub topics create default-envio --project=SEU_PROJETO_ID

# Tópicos específicos por cliente (opcionais)
gcloud pubsub topics create hubnordeste-processamento --project=SEU_PROJETO_ID
gcloud pubsub topics create hubnordeste-envio --project=SEU_PROJETO_ID
```

#### 🔄 Fallback:

Se um tópico específico do cliente não existir, o sistema usa automaticamente:
- `default-processamento` para processamento
- `default-envio` para envio

### 🚀 Cloud Tasks Queues por Cliente e Plataforma

Cada cliente usa **um CRM** (wts, kommo, rd_station), mas pode usar **múltiplas plataformas** (whatsapp, instagram, messenger). As queues são nomeadas como:

```
{slug_cliente}-{platform}
```

#### 📋 Exemplos:

| Cliente | CRM | Plataformas | Queues |
|---------|-----|-------------|--------|
| hubnordeste | wts | whatsapp, instagram | `hubnordeste-whatsapp`, `hubnordeste-instagram` |
| cliente2 | kommo | whatsapp, messenger | `cliente2-whatsapp`, `cliente2-messenger` |
| default | - | whatsapp | `default-whatsapp` |

#### 🔧 Comandos para criar queues:

```bash
# Hub Nordeste (usando WTS CRM)
gcloud tasks queues create hubnordeste-whatsapp --location=southamerica-east1 --project=hibrid-rag
gcloud tasks queues create hubnordeste-instagram --location=southamerica-east1 --project=hibrid-rag
gcloud tasks queues create hubnordeste-messenger --location=southamerica-east1 --project=hibrid-rag

# Default (fallback)
gcloud tasks queues create default-whatsapp --location=southamerica-east1 --project=hibrid-rag
gcloud tasks queues create default-instagram --location=southamerica-east1 --project=hibrid-rag
gcloud tasks queues create default-messenger --location=southamerica-east1 --project=hibrid-rag
```

#### 🎯 Lógica de funcionamento:

1. **CRM único por cliente**: Cada cliente usa apenas um CRM (wts, kommo, rd_station)
2. **Múltiplas plataformas**: O mesmo cliente pode ter conversas em whatsapp, instagram, messenger
3. **Queues por plataforma**: Cada plataforma tem sua própria queue para isolamento
4. **Processamento unificado**: Todas as mensagens do cliente vão para o mesmo tópico Pub/Sub

### 📁 Estrutura de Arquivos

```
hibrid-rag-functions/
├── 📄 message_buffer_main.py        # Recebe webhooks dos CRMs
├── 📄 message_processor_main.py     # Processa mensagens e publica no Pub/Sub
├── 📄 message_delivery_main.py      # Envia mensagens para os CRMs
├── 📄 models.py                     # Modelos Pydantic (multi-tenant)
├── 📄 supabase.py                   # Gerenciador do Supabase (multi-tenant)
├── 📄 message_processor.py          # Processamento de webhooks e entrega
├── 📄 requirements.txt              # Dependências Python
├── 📄 env.example                   # Exemplo de variáveis de ambiente
├── 📄 .gitignore                    # Arquivos ignorados pelo Git
├── 📄 .gcloudignore                 # Arquivos ignorados pelo Cloud Build
├── 📄 cloudbuild.yaml               # Configuração do Cloud Build
├── 📄 README.md                     # Documentação principal
├── 📁 message_buffer_Dockerfile     # Dockerfile para message-buffer
├── 📁 message_processor_Dockerfile  # Dockerfile para message-processor
├── 📁 message_delivery_Dockerfile   # Dockerfile para message-delivery
├── 📁 setup/                        # Scripts de setup do banco de dados
└── 📁 scripts/                      # Scripts e documentação auxiliar
    ├── 📄 setup_region.sh           # Configuração de região (Linux/Mac)
    ├── 📄 setup_region.bat          # Configuração de região (Windows)
    ├── 📄 region_config.md          # Documentação da configuração regional
    ├── 📄 Multi Tenant TO-DO.md     # Roadmap multi-tenant
    ├── 📄 manage_tenants.py         # Gerenciador de tenants
    ├── 📄 create_hubnordeste.py     # Criação específica do tenant Hub Nordeste
    ├── 📄 create_hubnordeste_tenant.sql # SQL para criar tenant
    ├── 📄 exemplo_webhook_hubnordeste.py # Exemplo de webhook
    ├── 📄 HUBNORDESTE_TENANT_README.md # Documentação do tenant
    ├── 📄 test_multi_tenant.py      # Testes da implementação multi-tenant
    └── 📄 MULTI_TENANT_MIGRATION_SUMMARY.md # Resumo da migração
```

## 🔧 Configuração Multi-Tenant

### 1. Setup do Banco de Dados

Execute no Supabase SQL Editor:

```sql
-- Criar estrutura multi-tenant
\i .setup/supabase_multi_tenant_clean.sql

-- Criar tenant específico (exemplo)
INSERT INTO tenants (name, slug, api_key, status, plan_type)
VALUES ('Hub Nordeste', 'hubnordeste', 'sk_xxx', 'active', 'enterprise');
```

### 2. Detecção de Tenant

O sistema detecta automaticamente o tenant via:

- **Header**: `X-Tenant-ID: tenant-uuid`
- **Query**: `?tenant_id=tenant-uuid`
- **Subdomain**: `tenant1.seudominio.com`
- **Padrão**: `00000000-0000-0000-0000-000000000000`

### 3. Exemplo de Uso

```bash
# Webhook para Hub Nordeste
curl -X POST https://message-buffer-xxxxx-sae1.a.run.app \
  -H "X-Tenant-ID: hubnordeste-uuid" \
  -H "Content-Type: application/json" \
  -d '{"webhook": "data"}'
```

## 🔐 Segurança

### Credenciais

- **Service Account**: Gerenciado automaticamente pelo Cloud Run
- **Supabase**: Chaves configuradas via variáveis de ambiente
- **CRMs**: Tokens configurados por tenant no banco

### Isolamento Multi-Tenant

- **Row Level Security (RLS)** no Supabase
- **Tópicos Pub/Sub** separados por tenant
- **Configurações** isoladas por tenant
- **Rate Limiting** por tenant

## 📊 Monitoramento

### Logs Estruturados

```python
import logging

logging.info("Mensagem processada", extra={
    "tenant_id": "hubnordeste-uuid",
    "tenant_name": "Hub Nordeste",
    "message_id": "msg_123",
    "platform": "wts"
})
```

### Métricas por Tenant

```sql
-- Estatísticas de uso
SELECT * FROM get_tenant_stats('hubnordeste-uuid');

-- Conversas ativas
SELECT COUNT(*) FROM conversations 
WHERE tenant_id = 'hubnordeste-uuid' 
  AND last_message_at > NOW() - INTERVAL '7 days';
```

## 🚨 Troubleshooting

### Problemas Comuns

1. **Credenciais**: Verificar se o Service Account tem permissões adequadas
2. **Variáveis de Ambiente**: Confirmar se estão configuradas no Cloud Run
3. **URLs**: Verificar se as URLs de comunicação estão corretas
4. **Tenant ID**: Confirmar se o tenant existe no banco

### Logs

```bash
# Ver logs do Cloud Run
gcloud logging read "resource.type=cloud_run_revision" --limit=50

# Filtrar por tenant
gcloud logging read "resource.type=cloud_run_revision AND jsonPayload.tenant_id=hubnordeste-uuid"
```

## 🔄 Desenvolvimento Local

### 1. Configurar Ambiente

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp env.example .env
# Editar .env com suas configurações
```

### 2. Executar Localmente

```bash
# Message Buffer
functions-framework --target=message_buffer --port=8080

# Message Processor
functions-framework --target=message_processor --port=8081

# Message Delivery
functions-framework --target=message_delivery --port=8082
```

### 3. Testar

```bash
# Testar webhook
curl -X POST http://localhost:8080 \
  -H "X-Tenant-ID: test-tenant" \
  -H "Content-Type: application/json" \
  -d '{"webhook": "test"}'
```

## 🛠️ Scripts Úteis

### Configuração de Região

```bash
# Linux/Mac
chmod +x scripts/setup_region.sh
./scripts/setup_region.sh

# Windows
scripts\setup_region.bat
```

### Gerenciamento de Tenants

```bash
# Executar gerenciador interativo
python scripts/manage_tenants.py

# Criar tenant específico
python scripts/create_hubnordeste.py
```

### Testes

```bash
# Executar testes multi-tenant
python scripts/test_multi_tenant.py
```

## 📈 Próximos Passos

- [ ] Implementar RAG Server
- [ ] Adicionar mais integrações de CRM
- [ ] Implementar monitoramento avançado
- [ ] Adicionar testes automatizados
- [ ] Implementar backup automático

## 📞 Suporte

Para suporte técnico ou dúvidas:

1. Verifique os logs no Cloud Console
2. Consulte a documentação em `scripts/Multi Tenant TO-DO.md`
3. Teste localmente antes de fazer deploy
4. Verifique as configurações do Service Account

---

**🎉 Sistema multi-tenant configurado e pronto para produção!**