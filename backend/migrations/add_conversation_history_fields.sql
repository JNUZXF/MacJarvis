-- Migration: Add conversation history fields to messages table
-- Date: 2026-01-28
-- Description: Add tool_call_results and metadata fields to support detailed conversation history

-- SQLite does not support ALTER TABLE ADD COLUMN for JSON columns in all versions
-- We need to handle this migration carefully

-- For SQLite, we'll use ALTER TABLE ADD COLUMN which should work for newer versions
-- If the columns already exist, these statements will fail (which is expected)

-- Add tool_call_results column
ALTER TABLE messages ADD COLUMN tool_call_results JSON DEFAULT NULL;

-- Add metadata column
ALTER TABLE messages ADD COLUMN metadata JSON DEFAULT NULL;

-- Commit the changes
-- Note: SQLite auto-commits in non-transactional mode
