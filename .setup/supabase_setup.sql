-- =====================================================
-- CONFIGURAÇÃO INICIAL DO SUPABASE
-- =====================================================

-- Habilitar extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- TABELAS PRINCIPAIS
-- =====================================================

-- Criar tabela de conversas
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identification VARCHAR(100) NOT NULL, -- Identificação do usuário: @doinstagram | telefone tratado (5582912341234) | nome do usuário no facebook
    platform TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,
    ia_active BOOLEAN DEFAULT TRUE
);

-- Tabela para mensagens recebidas dos webhooks
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

-- Índices para conversations
CREATE INDEX IF NOT EXISTS idx_conversations_identification ON conversations(identification);
CREATE INDEX IF NOT EXISTS idx_conversations_platform ON conversations(platform);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_last_message_at ON conversations(last_message_at);
CREATE INDEX IF NOT EXISTS idx_conversations_ia_active ON conversations(ia_active);

-- Índices para messages
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
CREATE INDEX IF NOT EXISTS idx_messages_conversation_timestamp ON messages(conversation_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_messages_platform_crm ON messages(platform, crm_source);
CREATE INDEX IF NOT EXISTS idx_messages_direction_type ON messages(direction, message_type);

-- =====================================================
-- ROW LEVEL SECURITY (RLS)
-- =====================================================

-- Habilitar RLS nas tabelas
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Políticas para conversations
CREATE POLICY "Conversations são visíveis para todos" ON conversations
    FOR ALL USING (true);

CREATE POLICY "Conversations podem ser criadas por todos" ON conversations
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Conversations podem ser atualizadas por todos" ON conversations
    FOR UPDATE USING (true);

-- Políticas para messages
CREATE POLICY "Messages são visíveis para todos" ON messages
    FOR ALL USING (true);

CREATE POLICY "Messages podem ser criadas por todos" ON messages
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Messages podem ser atualizadas por todos" ON messages
    FOR UPDATE USING (true);

-- =====================================================
-- COMENTÁRIOS DAS TABELAS
-- =====================================================

COMMENT ON TABLE conversations IS 'Tabela de conversas entre usuários e IA';
COMMENT ON TABLE messages IS 'Tabela de mensagens recebidas e enviadas';

COMMENT ON COLUMN conversations.identification IS 'Identificação única do usuário (telefone, @instagram, etc)';
COMMENT ON COLUMN conversations.platform IS 'Plataforma da conversa (whatsapp, instagram, facebook, etc)';
COMMENT ON COLUMN conversations.ia_active IS 'Se a IA está ativa para esta conversa';

COMMENT ON COLUMN messages.sender_name IS 'Nome do remetente da mensagem';
COMMENT ON COLUMN messages.direction IS 'Direção da mensagem: incoming (recebida) ou outgoing (enviada)';
COMMENT ON COLUMN messages.message_type IS 'Tipo da mensagem: text, audio, video, image, document';
COMMENT ON COLUMN messages.crm_source IS 'Fonte do CRM: wts, kommo, rd_conversas, etc';

-- =====================================================
-- FIM DA CONFIGURAÇÃO
-- =====================================================