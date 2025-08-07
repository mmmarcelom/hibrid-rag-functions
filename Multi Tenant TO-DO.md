# 🏢 Checklist de Migração para Multi-Tenant

## 📋 Visão Geral

Este documento contém o checklist completo para migrar o sistema de single-tenant para multi-tenant, garantindo isolamento completo de dados, configurações e infraestrutura por empresa/cliente.

---

## 🗄️ 1. Dados e Persistência

### 1.1 Estrutura de Banco de Dados

#### ✅ Tabela de Tenants
```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### ✅ Adicionar tenant_id nas tabelas existentes
```sql
-- Adicionar coluna tenant_id
ALTER TABLE messages ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE conversations ADD COLUMN tenant_id UUID REFERENCES tenants(id);

-- Criar índices para performance
CREATE INDEX idx_messages_tenant_id ON messages(tenant_id);
CREATE INDEX idx_conversations_tenant_id ON conversations(tenant_id);
```

#### ✅ Tabela de Configurações por Tenant
```sql
CREATE TABLE tenant_configs (
    tenant_id UUID REFERENCES tenants(id) PRIMARY KEY,
    rag_collection_name VARCHAR(255),
    pubsub_topic_name VARCHAR(255),
    pubsub_subscription_name VARCHAR(255),
    crm_config JSONB,
    rate_limits JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 1.2 Row Level Security (RLS)

#### ✅ Habilitar RLS
```sql
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_configs ENABLE ROW LEVEL SECURITY;
```

#### ✅ Criar Políticas de Segurança
```sql
-- Política para messages
CREATE POLICY "Users can only access their tenant data" ON messages
    FOR ALL USING (tenant_id = auth.jwt() ->> 'tenant_id');

-- Política para conversations
CREATE POLICY "Users can only access their tenant data" ON conversations
    FOR ALL USING (tenant_id = auth.jwt() ->> 'tenant_id');

-- Política para tenant_configs
CREATE POLICY "Users can only access their tenant config" ON tenant_configs
    FOR ALL USING (tenant_id = auth.jwt() ->> 'tenant_id');
```

### 1.3 Script de Migração de Dados

#### ✅ Migração de Dados Existentes
```python
def migrate_to_multi_tenant(default_tenant_id: str):
    """
    Script para migrar dados single-tenant para multi-tenant
    """
    # 1. Criar tenant padrão
    # 2. Atualizar todas as mensagens existentes
    # 3. Atualizar todas as conversas existentes
    # 4. Migrar base de conhecimento
    # 5. Criar configurações padrão
    pass
```

---

## 🧠 2. Base de Conhecimento

### 2.1 Isolamento de Coleções

#### ✅ Coleções Separadas por Tenant
```python
class MultiTenantRAGSystem:
    def __init__(self):
        self.tenant_collections = {}
    
    def get_collection_name(self, tenant_id: str) -> str:
        return f"knowledge_{tenant_id}"
    
    def retrieve_context(self, query: str, tenant_id: str, history: List[Message]):
        collection_name = self.get_collection_name(tenant_id)
        # Buscar apenas na coleção do tenant
        # ...
```

### 2.2 Migração de Embeddings

#### ✅ Script de Migração de Embeddings
```python
def migrate_embeddings_to_tenant_collections():
    """
    Migrar embeddings existentes para coleções separadas por tenant
    """
    # 1. Identificar todos os tenants
    # 2. Criar coleções separadas
    # 3. Migrar embeddings existentes
    # 4. Validar migração
    pass
```

### 2.3 Backup e Restore por Tenant

#### ✅ Estratégia de Backup
- [ ] Backup separado para cada tenant
- [ ] Restore granular por tenant
- [ ] Validação de integridade por tenant

---

## 📨 3. Pub/Sub e Entrega de Mensagens

### 3.1 Tópicos Separados por Tenant

#### ✅ Estrutura de Tópicos
```
para-envio-tenant-{tenant_id}
para-processamento-tenant-{tenant_id}
```

#### ✅ Criação Dinâmica de Tópicos
```python
class TenantPubSubManager:
    def __init__(self):
        self.tenant_topics = {}
    
    def get_topic_name(self, tenant_id: str, purpose: str) -> str:
        return f"{purpose}-tenant-{tenant_id}"
    
    def create_tenant_topics(self, tenant_id: str):
        # Criar tópicos específicos do tenant
        pass
```

### 3.2 Subscriptions Separadas

#### ✅ Subscriptions por Tenant
```python
def create_tenant_subscriptions(tenant_id: str):
    """
    Criar subscriptions específicas para cada tenant
    """
    # 1. Subscription para processamento
    # 2. Subscription para entrega
    # 3. Configurar filtros se necessário
    pass
```

### 3.3 Roteamento de Mensagens

#### ✅ Sistema de Roteamento
```python
class TenantRouter:
    def __init__(self):
        self.tenant_configs = {}
    
    def get_tenant_config(self, tenant_id: str):
        # Buscar configuração do tenant no Supabase
        pass
    
    def route_message(self, message: Message):
        tenant_id = message.tenant_id
        config = self.get_tenant_config(tenant_id)
        
        # Publicar no tópico específico do tenant
        topic_name = config['pubsub_topic_name']
        # ...
```

---

## 🔐 4. Segurança e Autenticação

### 4.1 Autenticação por Tenant

#### ✅ Middleware de Detecção de Tenant
```python
def tenant_middleware(request):
    """
    Middleware para detectar tenant via:
    - Header X-Tenant-ID
    - Subdomain
    - API Key
    - JWT Token
    """
    # Implementar lógica de detecção
    pass
```

### 4.2 Autorização Baseada em Tenant

#### ✅ Validação de Acesso
```python
def validate_tenant_access(tenant_id: str, user_id: str) -> bool:
    """
    Validar se o usuário tem acesso ao tenant
    """
    # Verificar permissões
    pass
```

### 4.3 Logs de Auditoria

#### ✅ Logs Estruturados por Tenant
```python
class TenantLogger:
    def __init__(self):
        self.tenant_logs = {}
    
    def log_activity(self, tenant_id: str, activity: str, data: dict):
        # Logs separados por tenant
        # ...
```

---

## 📊 5. Monitoramento e Métricas

### 5.1 Métricas Separadas por Tenant

#### ✅ Métricas por Tenant
- [ ] Número de mensagens processadas
- [ ] Tempo de resposta
- [ ] Taxa de erro
- [ ] Uso de recursos

### 5.2 Alertas por Tenant

#### ✅ Sistema de Alertas
- [ ] Alertas de erro por tenant
- [ ] Alertas de performance por tenant
- [ ] Alertas de uso de recursos por tenant

### 5.3 Dashboards por Tenant

#### ✅ Dashboards Separados
- [ ] Dashboard de atividade por tenant
- [ ] Dashboard de performance por tenant
- [ ] Dashboard de uso de recursos por tenant

---

## ⚙️ 6. Configuração e Infraestrutura

### 6.1 Configuração Dinâmica

#### ✅ Configurações por Tenant
```python
class TenantConfigManager:
    def __init__(self):
        self.configs = {}
    
    def get_tenant_config(self, tenant_id: str) -> dict:
        # Buscar configuração do tenant
        pass
    
    def update_tenant_config(self, tenant_id: str, config: dict):
        # Atualizar configuração do tenant
        pass
```

### 6.2 Rate Limiting por Tenant

#### ✅ Sistema de Rate Limiting
```python
class TenantRateLimiter:
    def __init__(self):
        self.tenant_limits = {}
    
    def check_rate_limit(self, tenant_id: str) -> bool:
        # Verificar limites específicos por tenant
        # ...
```

### 6.3 Infraestrutura como Código

#### ✅ Terraform/CloudFormation
```yaml
# Criar recursos por tenant:
# - Pub/Sub topics/subscriptions
# - Cloud Functions
# - IAM roles
# - Monitoring
```

---

## 🚀 7. Operacional

### 7.1 Backup e Recuperação

#### ✅ Estratégia de Backup
- [ ] Backup separado para cada tenant
- [ ] Recuperação granular por tenant
- [ ] Teste de recuperação regular

### 7.2 Disaster Recovery

#### ✅ Plano de DR
- [ ] DR por tenant
- [ ] Tempo de recuperação definido por tenant
- [ ] Teste de DR regular

### 7.3 Onboarding de Novos Tenants

#### ✅ Processo de Onboarding
- [ ] Criação automática de recursos
- [ ] Configuração inicial
- [ ] Validação de setup
- [ ] Documentação para o tenant

### 7.4 Offboarding de Tenants

#### ✅ Processo de Offboarding
- [ ] Backup final dos dados
- [ ] Remoção de recursos
- [ ] Limpeza de dados
- [ ] Confirmação de remoção

---

## 📋 8. Checklist de Implementação

### Fase 1: Isolamento de Dados
- [ ] Criar tabela `tenants`
- [ ] Adicionar `tenant_id` em `messages` e `conversations`
- [ ] Criar tabela `tenant_configs`
- [ ] Implementar RLS
- [ ] Script de migração de dados existentes
- [ ] Testes de isolamento

### Fase 2: Base de Conhecimento
- [ ] Implementar coleções separadas por tenant
- [ ] Migrar embeddings existentes
- [ ] Implementar filtro de busca por tenant
- [ ] Testes de isolamento da base de conhecimento

### Fase 3: Pub/Sub e Entrega
- [ ] Implementar tópicos separados por tenant
- [ ] Implementar subscriptions separadas
- [ ] Implementar roteamento de mensagens
- [ ] Testes de entrega por tenant

### Fase 4: Segurança e Monitoramento
- [ ] Implementar autenticação por tenant
- [ ] Implementar autorização baseada em tenant
- [ ] Implementar logs de auditoria
- [ ] Implementar métricas por tenant
- [ ] Implementar alertas por tenant

### Fase 5: Otimização e Escalabilidade
- [ ] Implementar rate limiting por tenant
- [ ] Otimizar performance por tenant
- [ ] Implementar cache por tenant
- [ ] Testes de carga por tenant

---

## 🔧 9. Scripts e Ferramentas

### 9.1 Scripts de Migração
- [ ] `migrate_to_multi_tenant.py`
- [ ] `create_tenant_resources.py`
- [ ] `validate_tenant_isolation.py`

### 9.2 Ferramentas de Administração
- [ ] Dashboard de administração de tenants
- [ ] Ferramentas de monitoramento por tenant
- [ ] Ferramentas de backup/restore por tenant

### 9.3 Documentação
- [ ] Documentação técnica da arquitetura multi-tenant
- [ ] Guia de onboarding para novos tenants
- [ ] Guia de troubleshooting por tenant

---

## 📞 10. Contatos e Responsabilidades

### 10.1 Equipe Responsável
- **Arquitetura**: [Nome]
- **Desenvolvimento**: [Nome]
- **Infraestrutura**: [Nome]
- **Segurança**: [Nome]
- **QA**: [Nome]

### 10.2 Cronograma
- **Fase 1**: [Data]
- **Fase 2**: [Data]
- **Fase 3**: [Data]
- **Fase 4**: [Data]
- **Fase 5**: [Data]

---

## ✅ Status do Projeto

- **Status Geral**: 🔄 Em Planejamento
- **Última Atualização**: [Data]
- **Próxima Revisão**: [Data]

---

*Este documento deve ser atualizado conforme o progresso do projeto.* 