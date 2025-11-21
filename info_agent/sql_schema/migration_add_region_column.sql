-- ============================================
-- Migration: Add Region Column & Required Tables
-- Purpose: Simplify region filtering and add authentication
-- Date: 2025-01-20
-- ============================================

-- ============================================
-- 1. ADD REGION COLUMN TO tb_stat
-- ============================================

-- Add region column
ALTER TABLE tb_stat
ADD COLUMN IF NOT EXISTS region VARCHAR(100);

-- Create index for fast filtering
CREATE INDEX IF NOT EXISTS idx_stat_region ON tb_stat(region);

-- Backfill existing data (extract region from assistant_id)
UPDATE tb_stat
SET region = CASE
    WHEN assistant_id ILIKE '%lombardia%' OR assistant_id ILIKE '%lombardy%' THEN 'Lombardia'
    WHEN assistant_id ILIKE '%piemonte%' OR assistant_id ILIKE '%piedmont%' THEN 'Piemonte'
    WHEN assistant_id ILIKE '%veneto%' THEN 'Veneto'
    ELSE 'Unknown'
END
WHERE region IS NULL;

-- ============================================
-- 2. USERS & AUTHENTICATION TABLES
-- ============================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'operator',
    region VARCHAR(100),  -- User's assigned region for filtering (NULL = all regions for admin)
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User sessions table (for JWT)
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE,  -- UNIQUE: one session per user (for ON CONFLICT)
    token_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add unique constraint if table already exists without it
ALTER TABLE user_sessions
ADD CONSTRAINT IF NOT EXISTS user_sessions_user_id_unique UNIQUE (user_id);

-- Indexes for users
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_region ON users(region);

-- If users table already exists without region column, add it
ALTER TABLE users ADD COLUMN IF NOT EXISTS region VARCHAR(100);

-- Indexes for sessions
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);

-- ============================================
-- 3. Q/A MANAGEMENT TABLE
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
-- 4. SEED DATA
-- ============================================

-- Create default admin user (password: admin123)
-- region = NULL means admin can see all regions
INSERT INTO users (email, name, password_hash, role, region)
VALUES (
    'admin@voila.com',
    'System Administrator',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5yvQGvF4a7cOy',
    'admin',
    NULL
) ON CONFLICT (email) DO NOTHING;

-- ============================================
-- 5. VERIFICATION QUERIES
-- ============================================

-- Check region column exists and is populated
-- SELECT region, COUNT(*) as call_count FROM tb_stat GROUP BY region;

-- Check users table
-- SELECT email, name, role FROM users;

-- Check qa_entries table exists
-- SELECT COUNT(*) FROM qa_entries;

-- ============================================
-- NOTES:
-- ============================================
-- 1. This migration is ADDITIVE - it does not modify existing data
-- 2. tb_stat existing records will be backfilled with region based on assistant_id
-- 3. All CREATE statements use IF NOT EXISTS for idempotency
-- 4. Run this script in your Supabase SQL editor
-- ============================================
