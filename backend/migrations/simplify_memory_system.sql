-- Migration: Simplify Memory System
-- Date: 2026-02-03
-- Description: Simplify memory system from 5 tables to 5 text fields in users table

-- ============================================
-- Add 5 memory fields to users table
-- ============================================
ALTER TABLE users ADD COLUMN memory_preferences TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN memory_facts TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN memory_episodes TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN memory_tasks TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN memory_relations TEXT DEFAULT '';

-- ============================================
-- Migration Complete
-- ============================================
-- This migration simplifies the memory system by:
-- - Adding 5 TEXT fields to users table for storing memory content
-- - Each field stores one type of memory as natural language text
-- - Replaces the complex 5-table structure with simple text storage
