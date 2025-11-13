-- ============================================
-- Voilà Voice Dashboard + Pipecat Agent
-- Supabase (PostgreSQL) Schema
-- Fixed for UUID compatibility
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. USERS & AUTHENTICATION
-- ============================================

CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'operator',
    region VARCHAR(100) DEFAULT 'master',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_region ON users(region);

CREATE TABLE IF NOT EXISTS user_sessions (
    session_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);

-- ============================================
-- 2. VOICE AGENTS
-- ============================================

CREATE TABLE IF NOT EXISTS tb_voice_agent (
    id_voice_agent SERIAL PRIMARY KEY,
    regione VARCHAR(100),
    assistant_id VARCHAR(50),
    public BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    agent_type VARCHAR(50) DEFAULT 'pipecat'
);

CREATE INDEX IF NOT EXISTS idx_voice_agent_region ON tb_voice_agent(regione);
CREATE INDEX IF NOT EXISTS idx_voice_agent_active ON tb_voice_agent(is_active);

-- ============================================
-- 3. CALL STATISTICS
-- ============================================

CREATE TABLE IF NOT EXISTS tb_stat (
    id_stat SERIAL PRIMARY KEY,
    call_id UUID DEFAULT uuid_generate_v4(),
    interaction_id UUID,
    phone_number VARCHAR(100),
    assistant_id VARCHAR(50),
    started_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    action VARCHAR(50),
    sentiment VARCHAR(20),
    esito_chiamata VARCHAR(50),
    motivazione VARCHAR(100),
    patient_intent TEXT,
    transcript TEXT,
    summary TEXT,
    cost DECIMAL(10, 4),
    llm_token INTEGER DEFAULT 0,
    service VARCHAR(45) DEFAULT 'pipecat',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stat_call_id ON tb_stat(call_id);
CREATE INDEX IF NOT EXISTS idx_stat_assistant_id ON tb_stat(assistant_id);
CREATE INDEX IF NOT EXISTS idx_stat_started_at ON tb_stat(started_at);
CREATE INDEX IF NOT EXISTS idx_stat_phone ON tb_stat(phone_number);
CREATE INDEX IF NOT EXISTS idx_stat_sentiment ON tb_stat(sentiment);

-- ============================================
-- 4. KNOWLEDGE BASE
-- ============================================

CREATE TABLE IF NOT EXISTS qa_entries (
    qa_id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    region VARCHAR(100) NOT NULL DEFAULT 'Piemonte',
    pinecone_id VARCHAR(255) UNIQUE,
    id_domanda VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_qa_region ON qa_entries(region);
CREATE INDEX IF NOT EXISTS idx_qa_created ON qa_entries(created_at);

-- ============================================
-- 5. PRICING & SPORT DATA
-- ============================================

CREATE TABLE IF NOT EXISTS region_exam_pricing (
    id SERIAL PRIMARY KEY,
    region VARCHAR(100) NOT NULL,
    exam_code VARCHAR(10) NOT NULL,
    price DECIMAL(8, 2) NOT NULL,
    price_over DECIMAL(8, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_region_exam UNIQUE (region, exam_code)
);

CREATE TABLE IF NOT EXISTS sport_requisiti (
    id SERIAL PRIMARY KEY,
    sport VARCHAR(100) NOT NULL,
    visita VARCHAR(10) NOT NULL,
    agonismo_m VARCHAR(20) NOT NULL,
    agonismo_f VARCHAR(20) NOT NULL,
    validita VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sport_preparazione (
    id SERIAL PRIMARY KEY,
    sport_requisiti_id INTEGER NOT NULL,
    preparazione VARCHAR(200) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 6. PIPECAT SESSION TRACKING
-- ============================================

CREATE TABLE IF NOT EXISTS pipecat_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    caller_phone VARCHAR(100),
    start_node VARCHAR(50),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    nodes_visited TEXT[],
    functions_called TEXT[],
    final_node VARCHAR(50),
    transfer_requested BOOLEAN DEFAULT false,
    transfer_reason TEXT,
    user_interruptions INTEGER DEFAULT 0,
    llm_calls INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    assistant_id VARCHAR(50),
    region VARCHAR(100),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_pipecat_sessions_phone ON pipecat_sessions(caller_phone);
CREATE INDEX IF NOT EXISTS idx_pipecat_sessions_started ON pipecat_sessions(started_at);

CREATE TABLE IF NOT EXISTS pipecat_function_calls (
    id SERIAL PRIMARY KEY,
    session_id UUID,
    function_name VARCHAR(100) NOT NULL,
    parameters JSONB,
    result JSONB,
    called_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    duration_ms INTEGER,
    status VARCHAR(20),
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_function_calls_session ON pipecat_function_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_function_calls_name ON pipecat_function_calls(function_name);

-- ============================================
-- 7. SYNC & CONFIG
-- ============================================

CREATE TABLE IF NOT EXISTS knowledge_base_sync_log (
    id SERIAL PRIMARY KEY,
    qa_id INTEGER,
    action VARCHAR(20),
    region VARCHAR(100),
    synced_to_pinecone BOOLEAN DEFAULT false,
    synced_to_pipecat BOOLEAN DEFAULT false,
    pinecone_sync_at TIMESTAMP WITH TIME ZONE,
    pipecat_sync_at TIMESTAMP WITH TIME ZONE,
    sync_errors TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tb_prompt (
    id_prompt SERIAL PRIMARY KEY,
    prompt_name VARCHAR(100) NOT NULL,
    prompt TEXT NOT NULL,
    details TEXT,
    region VARCHAR(100),
    agent_type VARCHAR(50) DEFAULT 'pipecat',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 8. TRIGGERS
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_timestamp BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_qa_timestamp BEFORE UPDATE ON qa_entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stat_timestamp BEFORE UPDATE ON tb_stat
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_timestamp BEFORE UPDATE ON tb_voice_agent
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_prompt_timestamp BEFORE UPDATE ON tb_prompt
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 9. SEED DATA
-- ============================================

INSERT INTO users (email, name, password_hash, role, region)
VALUES ('admin@voila.com', 'System Administrator', 
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5yvQGvF4a7cOy',
        'admin', 'master')
ON CONFLICT (email) DO NOTHING;

INSERT INTO tb_voice_agent (regione, assistant_id, agent_type, is_active)
VALUES 
    ('Piemonte', 'pipecat-piemonte-001', 'pipecat', true),
    ('Lombardia', 'pipecat-lombardia-001', 'pipecat', false),
    ('Veneto', 'pipecat-veneto-001', 'pipecat', false)
ON CONFLICT DO NOTHING;

-- ============================================
-- 10. VERSION
-- ============================================

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_version (version, description)
VALUES (1, 'Supabase schema - Fixed UUID casting errors')
ON CONFLICT (version) DO NOTHING;
