-- Migration: Add Memory System Tables
-- Date: 2026-01-29
-- Description: Add comprehensive memory system with 5 memory types

-- ============================================
-- 1. Preference Memory Table
-- ============================================
CREATE TABLE IF NOT EXISTS preference_memory (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    category VARCHAR(100) NOT NULL,
    preference_key VARCHAR(200) NOT NULL,
    preference_value TEXT NOT NULL,
    confidence INTEGER NOT NULL DEFAULT 5,
    source VARCHAR(100),
    extra_metadata JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_confirmed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pref_user_id ON preference_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_pref_category ON preference_memory(category);
CREATE INDEX IF NOT EXISTS idx_pref_user_category ON preference_memory(user_id, category);
CREATE INDEX IF NOT EXISTS idx_pref_key ON preference_memory(user_id, preference_key);

-- ============================================
-- 2. Fact Memory Table
-- ============================================
CREATE TABLE IF NOT EXISTS fact_memory (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    fact_type VARCHAR(100) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    fact_value TEXT NOT NULL,
    confidence INTEGER NOT NULL DEFAULT 5,
    source VARCHAR(100),
    metadata JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_fact_user_id ON fact_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_fact_type ON fact_memory(fact_type);
CREATE INDEX IF NOT EXISTS idx_fact_user_type ON fact_memory(user_id, fact_type);
CREATE INDEX IF NOT EXISTS idx_fact_subject ON fact_memory(user_id, subject);

-- ============================================
-- 3. Task Memory Table
-- ============================================
CREATE TABLE IF NOT EXISTS task_memory (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    session_id VARCHAR(36),
    task_type VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    progress INTEGER NOT NULL DEFAULT 0,
    priority VARCHAR(20) DEFAULT 'medium',
    context JSON,
    extra_metadata JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    due_date TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_task_user_id ON task_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_task_status ON task_memory(status);
CREATE INDEX IF NOT EXISTS idx_task_user_status ON task_memory(user_id, status);
CREATE INDEX IF NOT EXISTS idx_task_session_id ON task_memory(session_id);
CREATE INDEX IF NOT EXISTS idx_task_updated ON task_memory(updated_at);

-- ============================================
-- 4. Relation Memory Table
-- ============================================
CREATE TABLE IF NOT EXISTS relation_memory (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    subject_entity VARCHAR(200) NOT NULL,
    subject_type VARCHAR(100) NOT NULL,
    relation_type VARCHAR(100) NOT NULL,
    object_entity VARCHAR(200) NOT NULL,
    object_type VARCHAR(100) NOT NULL,
    confidence INTEGER NOT NULL DEFAULT 5,
    bidirectional INTEGER NOT NULL DEFAULT 0,
    extra_metadata JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rel_user_id ON relation_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_rel_subject ON relation_memory(user_id, subject_entity);
CREATE INDEX IF NOT EXISTS idx_rel_object ON relation_memory(user_id, object_entity);
CREATE INDEX IF NOT EXISTS idx_rel_type ON relation_memory(relation_type);
CREATE INDEX IF NOT EXISTS idx_rel_entities ON relation_memory(subject_entity, object_entity);

-- ============================================
-- Migration Complete
-- ============================================
-- This migration adds comprehensive memory system with:
-- - Preference Memory: User preferences and settings
-- - Fact Memory: Objective information about the user
-- - Task Memory: Ongoing tasks and work state
-- - Relation Memory: Relationships between entities
--
-- All tables include proper indexing for efficient queries
-- and foreign key constraints for data integrity.
