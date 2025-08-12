-- =====================================================
-- CONFIGURAÇÃO MULTI-TENANT DO SUPABASE
-- =====================================================

-- Habilitar extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- TABELAS DE TENANTS
-- =====================================================

-- Tabela principal de tenants (empresas/clientes)
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL, -- Identificador único para URLs
    api_key VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended', 'pending')),
    plan_type VARCHAR(50) DEFAULT 'basic' CHECK (plan_type IN ('basic', 'pro', 'enterprise')),
    max_conversations INTEGER DEFAULT 1000,
    max_messages_per_month INTEGER DEFAULT 10000,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID, -- ID do usuário que criou o tenant
    notes TEXT -- Notas administrativas
);

-- Tabela de configurações por tenant
CREATE TABLE IF NOT EXISTS tenant_configs (
    tenant_id UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Configurações de RAG
    rag_collection_name VARCHAR(255) DEFAULT 'knowledge',
    rag_model_name VARCHAR(100) DEFAULT 'all-MiniLM-L6-v2',
    rag_similarity_threshold DECIMAL(3,2) DEFAULT 0.7,
    rag_max_results INTEGER DEFAULT 5,
    
    -- Configurações de Pub/Sub
    pubsub_topic_processing VARCHAR(255),
    pubsub_topic_delivery VARCHAR(255),
    pubsub_subscription_processing VARCHAR(255),
    pubsub_subscription_delivery VARCHAR(255),
    
    -- Configurações de CRMs
    crm_config JSONB DEFAULT '{}',
    
    -- Configurações de Rate Limiting
    rate_limits JSONB DEFAULT '{
        "requests_per_minute": 60,
        "requests_per_hour": 1000,
        "requests_per_day": 10000,
        "max_concurrent_requests": 10
    }',
    
    -- Configurações de Notificações
    notification_config JSONB DEFAULT '{
        "email_alerts": false,
        "webhook_alerts": false,
        "webhook_url": null
    }',
    
    -- Configurações de IA
    ai_config JSONB DEFAULT '{
        "model": "llama3.2",
        "temperature": 0.7,
        "max_tokens": 500,
        "system_prompt": "Você é um assistente útil e amigável."
    }',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabela de chaves de API por tenant
CREATE TABLE IF NOT EXISTS tenant_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL, -- Nome descritivo da chave
    api_key VARCHAR(255) UNIQUE NOT NULL,
    permissions JSONB DEFAULT '{
        "read": true,
        "write": true,
        "admin": false
    }',
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'revoked')),
    expires_at TIMESTAMPTZ, -- NULL = nunca expira
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID -- ID do usuário que criou a chave
);

-- Tabela de configurações de CRMs por tenant
CREATE TABLE IF NOT EXISTS tenant_crm_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    crm_type VARCHAR(50) NOT NULL CHECK (crm_type IN ('wts', 'kommo', 'rd_conversas', 'whatsapp_business')),
    crm_name VARCHAR(255) NOT NULL, -- Nome descritivo da integração
    
    -- Configurações de autenticação
    api_token VARCHAR(500), -- Token de API (criptografado)
    api_url VARCHAR(500), -- URL base da API
    webhook_url VARCHAR(500), -- URL do webhook
    
    -- Configurações específicas do CRM
    config JSONB DEFAULT '{}',
    
    -- Status da integração
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'error')),
    last_sync_at TIMESTAMPTZ,
    error_message TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Garantir que cada tenant tenha apenas uma configuração por tipo de CRM
    UNIQUE(tenant_id, crm_type)
);

-- =====================================================
-- TABELAS PRINCIPAIS (ATUALIZADAS COM TENANT_ID)
-- =====================================================

-- Criar tabela de conversas (atualizada)
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    identification VARCHAR(100) NOT NULL, -- Identificação do usuário: @doinstagram | telefone tratado (5582912341234) | nome do usuário no facebook
    platform TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,
    ia_active BOOLEAN DEFAULT TRUE
);

-- Tabela para mensagens recebidas dos webhooks (atualizada)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    conversation_id UUID,
    platform TEXT NOT NULL,
    sender TEXT NOT NULL,
    receiver TEXT NOT NULL,
    sender_name VARCHAR(255), -- Nome do remetente da mensagem
    content TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('incoming', 'outgoing')),
    message_type TEXT NOT NULL CHECK (message_type IN ('text', 'audio', 'video', 'image', 'document')),
    timestamp TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    crm_source TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT fk_conversation
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- =====================================================
-- ÍNDICES PARA PERFORMANCE
-- =====================================================

-- Índices para tenants
CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(slug);
CREATE INDEX IF NOT EXISTS idx_tenants_api_key ON tenants(api_key);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);
CREATE INDEX IF NOT EXISTS idx_tenants_plan_type ON tenants(plan_type);
CREATE INDEX IF NOT EXISTS idx_tenants_created_at ON tenants(created_at);

-- Índices para tenant_configs
CREATE INDEX IF NOT EXISTS idx_tenant_configs_rag_collection ON tenant_configs(rag_collection_name);
CREATE INDEX IF NOT EXISTS idx_tenant_configs_pubsub_topics ON tenant_configs(pubsub_topic_processing, pubsub_topic_delivery);

-- Índices para tenant_api_keys
CREATE INDEX IF NOT EXISTS idx_tenant_api_keys_tenant_id ON tenant_api_keys(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_api_keys_api_key ON tenant_api_keys(api_key);
CREATE INDEX IF NOT EXISTS idx_tenant_api_keys_status ON tenant_api_keys(status);
CREATE INDEX IF NOT EXISTS idx_tenant_api_keys_expires_at ON tenant_api_keys(expires_at);

-- Índices para tenant_crm_configs
CREATE INDEX IF NOT EXISTS idx_tenant_crm_configs_tenant_id ON tenant_crm_configs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_crm_configs_crm_type ON tenant_crm_configs(crm_type);
CREATE INDEX IF NOT EXISTS idx_tenant_crm_configs_status ON tenant_crm_configs(status);

-- Índices para conversations (atualizados)
CREATE INDEX IF NOT EXISTS idx_conversations_tenant_id ON conversations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_conversations_identification ON conversations(identification);
CREATE INDEX IF NOT EXISTS idx_conversations_platform ON conversations(platform);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_last_message_at ON conversations(last_message_at);
CREATE INDEX IF NOT EXISTS idx_conversations_ia_active ON conversations(ia_active);

-- Índices para messages (atualizados)
CREATE INDEX IF NOT EXISTS idx_messages_tenant_id ON messages(tenant_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_platform ON messages(platform);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender);
CREATE INDEX IF NOT EXISTS idx_messages_sender_name ON messages(sender_name);
CREATE INDEX IF NOT EXISTS idx_messages_direction ON messages(direction);
CREATE INDEX IF NOT EXISTS idx_messages_message_type ON messages(message_type);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_crm_source ON messages(crm_source);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

-- Índices compostos para queries comuns
CREATE INDEX IF NOT EXISTS idx_conversations_tenant_identification ON conversations(tenant_id, identification);
CREATE INDEX IF NOT EXISTS idx_conversations_tenant_platform ON conversations(tenant_id, platform);
CREATE INDEX IF NOT EXISTS idx_messages_tenant_conversation_timestamp ON messages(tenant_id, conversation_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_messages_tenant_platform_crm ON messages(tenant_id, platform, crm_source);
CREATE INDEX IF NOT EXISTS idx_messages_tenant_direction_type ON messages(tenant_id, direction, message_type);

-- =====================================================
-- ROW LEVEL SECURITY (RLS) - MULTI-TENANT
-- =====================================================

-- Habilitar RLS nas tabelas
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_crm_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Políticas para tenants (apenas admins podem ver todos)
CREATE POLICY "Tenants são visíveis apenas para admins" ON tenants
    FOR ALL USING (auth.jwt() ->> 'role' = 'admin');

-- Políticas para tenant_configs
CREATE POLICY "Tenant configs são visíveis para o próprio tenant" ON tenant_configs
    FOR ALL USING (tenant_id = auth.jwt() ->> 'tenant_id');

-- Políticas para tenant_api_keys
CREATE POLICY "API keys são visíveis para o próprio tenant" ON tenant_api_keys
    FOR ALL USING (tenant_id = auth.jwt() ->> 'tenant_id');

-- Políticas para tenant_crm_configs
CREATE POLICY "CRM configs são visíveis para o próprio tenant" ON tenant_crm_configs
    FOR ALL USING (tenant_id = auth.jwt() ->> 'tenant_id');

-- Políticas para conversations
CREATE POLICY "Conversations são visíveis para o próprio tenant" ON conversations
    FOR ALL USING (tenant_id = auth.jwt() ->> 'tenant_id');

-- Políticas para messages
CREATE POLICY "Messages são visíveis para o próprio tenant" ON messages
    FOR ALL USING (tenant_id = auth.jwt() ->> 'tenant_id');

-- =====================================================
-- FUNÇÕES E TRIGGERS
-- =====================================================

-- Função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para atualizar updated_at
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tenant_configs_updated_at BEFORE UPDATE ON tenant_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tenant_crm_configs_updated_at BEFORE UPDATE ON tenant_crm_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_messages_updated_at BEFORE UPDATE ON messages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Função para gerar API keys únicas
CREATE OR REPLACE FUNCTION generate_api_key()
RETURNS TEXT AS $$
BEGIN
    RETURN 'sk_' || encode(gen_random_bytes(32), 'base64');
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- DADOS INICIAIS
-- =====================================================

-- Inserir tenant padrão para migração
INSERT INTO tenants (id, name, slug, api_key, status, plan_type, notes)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'Tenant Padrão',
    'default',
    generate_api_key(),
    'active',
    'enterprise',
    'Tenant padrão criado automaticamente para migração de dados existentes'
) ON CONFLICT (slug) DO NOTHING;

-- Inserir configuração padrão
INSERT INTO tenant_configs (tenant_id, rag_collection_name, pubsub_topic_processing, pubsub_topic_delivery)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'knowledge_default',
    'para-processamento-default',
    'para-envio-default'
) ON CONFLICT (tenant_id) DO NOTHING;

-- =====================================================
-- COMENTÁRIOS DAS TABELAS
-- =====================================================

COMMENT ON TABLE tenants IS 'Tabela principal de tenants (empresas/clientes)';
COMMENT ON TABLE tenant_configs IS 'Configurações específicas por tenant';
COMMENT ON TABLE tenant_api_keys IS 'Chaves de API por tenant';
COMMENT ON TABLE tenant_crm_configs IS 'Configurações de CRMs por tenant';
COMMENT ON TABLE conversations IS 'Tabela de conversas entre usuários e IA (multi-tenant)';
COMMENT ON TABLE messages IS 'Tabela de mensagens recebidas e enviadas (multi-tenant)';

-- =====================================================
-- FIM DA CONFIGURAÇÃO MULTI-TENANT
-- =====================================================
