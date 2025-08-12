-- Script para criar o tenant hubnordeste
-- Execute este script no Supabase SQL Editor APÓS executar recreate_tables_with_rls.sql

-- =====================================================
-- CRIAR TENANT HUBNORDESTE
-- =====================================================

-- Inserir tenant hubnordeste
INSERT INTO tenants (id, name, slug, api_key, status, plan_type, notes)
VALUES (
    '31d34af8-5324-4579-9661-4eb132a2de55',
    'Hub Nordeste',
    'hubnordeste',
    generate_api_key(),
    'active',
    'enterprise',
    'Tenant para Hub Nordeste - cliente principal'
) ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    status = EXCLUDED.status,
    plan_type = EXCLUDED.plan_type,
    notes = EXCLUDED.notes,
    updated_at = NOW();

-- Inserir configurações do tenant hubnordeste
INSERT INTO tenant_configs (tenant_id, rag_collection_name, pubsub_topic_processing, pubsub_topic_delivery, rate_limit_per_minute, max_conversation_history)
VALUES (
    '31d34af8-5324-4579-9661-4eb132a2de55',
    'knowledge_hubnordeste',
    'para-processamento-hubnordeste',
    'para-envio-hubnordeste',
    120, -- 120 mensagens por minuto
    100  -- 100 mensagens no histórico
) ON CONFLICT (tenant_id) DO UPDATE SET
    rag_collection_name = EXCLUDED.rag_collection_name,
    pubsub_topic_processing = EXCLUDED.pubsub_topic_processing,
    pubsub_topic_delivery = EXCLUDED.pubsub_topic_delivery,
    rate_limit_per_minute = EXCLUDED.rate_limit_per_minute,
    max_conversation_history = EXCLUDED.max_conversation_history,
    updated_at = NOW();

-- Inserir chave de API para hubnordeste
INSERT INTO tenant_api_keys (tenant_id, key_name, api_key, permissions, is_active)
VALUES (
    '31d34af8-5324-4579-9661-4eb132a2de55',
    'API Key Principal',
    generate_api_key(),
    '{"read": true, "write": true, "admin": true}'::jsonb,
    true
) ON CONFLICT DO NOTHING;

-- =====================================================
-- CONFIGURAÇÕES DE CRM PARA HUBNORDESTE
-- =====================================================

-- Configuração WTS (WhatsApp)
INSERT INTO tenant_crm_configs (tenant_id, crm_type, config, is_active)
VALUES (
    '31d34af8-5324-4579-9661-4eb132a2de55',
    'wts',
    '{
        "webhook_url": "https://message-receiver-xxxxx-uc.a.run.app/31d34af8-5324-4579-9661-4eb132a2de55",
        "api_key": "wts_api_key_hubnordeste",
        "channel_id": "127",
        "instance_id": "hubnordeste_instance",
        "settings": {
            "auto_reply": true,
            "business_hours": {
                "enabled": true,
                "start": "08:00",
                "end": "18:00",
                "timezone": "America/Sao_Paulo"
            }
        }
    }'::jsonb,
    true
) ON CONFLICT (tenant_id, crm_type) DO UPDATE SET
    config = EXCLUDED.config,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- Configuração Kommo (AmoCRM) - exemplo
INSERT INTO tenant_crm_configs (tenant_id, crm_type, config, is_active)
VALUES (
    '31d34af8-5324-4579-9661-4eb132a2de55',
    'kommo',
    '{
        "webhook_url": "https://message-receiver-xxxxx-uc.a.run.app/31d34af8-5324-4579-9661-4eb132a2de55",
        "api_key": "kommo_api_key_hubnordeste",
        "domain": "hubnordeste.amocrm.ru",
        "pipeline_id": "12345",
        "settings": {
            "auto_create_lead": true,
            "lead_source": "WhatsApp"
        }
    }'::jsonb,
    false -- Desabilitado por enquanto
) ON CONFLICT (tenant_id, crm_type) DO UPDATE SET
    config = EXCLUDED.config,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- Configuração RD Station Conversas - exemplo
INSERT INTO tenant_crm_configs (tenant_id, crm_type, config, is_active)
VALUES (
    '31d34af8-5324-4579-9661-4eb132a2de55',
    'rd_station',
    '{
        "webhook_url": "https://message-receiver-xxxxx-uc.a.run.app/31d34af8-5324-4579-9661-4eb132a2de55",
        "api_key": "rd_api_key_hubnordeste",
        "account_id": "hubnordeste_account",
        "settings": {
            "auto_tag": true,
            "tag_name": "WhatsApp"
        }
    }'::jsonb,
    false -- Desabilitado por enquanto
) ON CONFLICT (tenant_id, crm_type) DO UPDATE SET
    config = EXCLUDED.config,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- =====================================================
-- VERIFICAÇÃO DOS DADOS INSERIDOS
-- =====================================================

-- Verificar tenant criado
SELECT 
    id,
    name,
    slug,
    status,
    plan_type,
    created_at
FROM tenants 
WHERE slug = 'hubnordeste';

-- Verificar configurações
SELECT 
    tc.tenant_id,
    t.name as tenant_name,
    tc.rag_collection_name,
    tc.pubsub_topic_processing,
    tc.pubsub_topic_delivery,
    tc.rate_limit_per_minute,
    tc.max_conversation_history
FROM tenant_configs tc
JOIN tenants t ON tc.tenant_id = t.id
WHERE t.slug = 'hubnordeste';

-- Verificar chaves de API
SELECT 
    tak.tenant_id,
    t.name as tenant_name,
    tak.key_name,
    tak.api_key,
    tak.is_active,
    tak.created_at
FROM tenant_api_keys tak
JOIN tenants t ON tak.tenant_id = t.id
WHERE t.slug = 'hubnordeste';

-- Verificar configurações de CRM
SELECT 
    tcrm.tenant_id,
    t.name as tenant_name,
    tcrm.crm_type,
    tcrm.config,
    tcrm.is_active,
    tcrm.created_at
FROM tenant_crm_configs tcrm
JOIN tenants t ON tcrm.tenant_id = t.id
WHERE t.slug = 'hubnordeste'
ORDER BY tcrm.crm_type;

-- Resumo final
SELECT 
    'Tenant Hub Nordeste' as info,
    t.name,
    t.slug,
    t.status,
    t.plan_type,
    tc.rag_collection_name,
    tc.pubsub_topic_processing,
    tc.pubsub_topic_delivery
FROM tenants t
LEFT JOIN tenant_configs tc ON t.id = tc.tenant_id
WHERE t.slug = 'hubnordeste';
