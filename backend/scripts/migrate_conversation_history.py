#!/usr/bin/env python3
"""
Migration script to add conversation history fields to the messages table.

This script adds:
- tool_call_results: JSON field to store tool execution results
- metadata: JSON field to store additional metadata (timestamps, etc.)

Usage:
    python scripts/migrate_conversation_history.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.infrastructure.database.connection import get_engine
from app.config import get_settings
import structlog

logger = structlog.get_logger(__name__)


async def check_column_exists(engine, table_name: str, column_name: str) -> bool:
    """
    Check if a column exists in a table.

    Args:
        engine: Database engine
        table_name: Table name
        column_name: Column name

    Returns:
        True if column exists, False otherwise
    """
    async with engine.begin() as conn:
        # For SQLite, we can use PRAGMA table_info
        result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
        columns = result.fetchall()

        for col in columns:
            if col[1] == column_name:  # col[1] is the column name
                return True

        return False


async def add_column_if_not_exists(
    engine,
    table_name: str,
    column_name: str,
    column_type: str
) -> bool:
    """
    Add a column to a table if it doesn't exist.

    Args:
        engine: Database engine
        table_name: Table name
        column_name: Column name
        column_type: Column type definition

    Returns:
        True if column was added, False if it already existed
    """
    exists = await check_column_exists(engine, table_name, column_name)

    if exists:
        logger.info(
            "column_already_exists",
            table=table_name,
            column=column_name
        )
        return False

    async with engine.begin() as conn:
        await conn.execute(
            text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        )
        logger.info(
            "column_added",
            table=table_name,
            column=column_name,
            type=column_type
        )

    return True


async def migrate():
    """Run the migration."""
    logger.info("migration_started", migration="add_conversation_history_fields")

    settings = get_settings()
    engine = get_engine(settings)

    try:
        # Add tool_call_results column
        added_results = await add_column_if_not_exists(
            engine,
            "messages",
            "tool_call_results",
            "JSON DEFAULT NULL"
        )

        # Add metadata column
        added_metadata = await add_column_if_not_exists(
            engine,
            "messages",
            "metadata",
            "JSON DEFAULT NULL"
        )

        if added_results or added_metadata:
            logger.info(
                "migration_completed",
                migration="add_conversation_history_fields",
                added_tool_call_results=added_results,
                added_metadata=added_metadata
            )
        else:
            logger.info(
                "migration_skipped",
                migration="add_conversation_history_fields",
                reason="columns_already_exist"
            )

        return True

    except Exception as e:
        logger.error(
            "migration_failed",
            migration="add_conversation_history_fields",
            error=str(e),
            error_type=type(e).__name__
        )
        return False

    finally:
        await engine.dispose()


async def verify_migration():
    """Verify the migration was successful."""
    logger.info("verification_started")

    settings = get_settings()
    engine = get_engine(settings)

    try:
        has_results = await check_column_exists(engine, "messages", "tool_call_results")
        has_metadata = await check_column_exists(engine, "messages", "metadata")

        if has_results and has_metadata:
            logger.info(
                "verification_passed",
                tool_call_results_exists=has_results,
                metadata_exists=has_metadata
            )
            return True
        else:
            logger.error(
                "verification_failed",
                tool_call_results_exists=has_results,
                metadata_exists=has_metadata
            )
            return False

    finally:
        await engine.dispose()


async def main():
    """Main entry point."""
    print("=" * 60)
    print("Conversation History Migration")
    print("=" * 60)
    print()

    # Run migration
    success = await migrate()

    if not success:
        print("\n❌ Migration failed!")
        sys.exit(1)

    # Verify migration
    print()
    verified = await verify_migration()

    if verified:
        print("\n✅ Migration completed successfully!")
        print()
        print("The following columns have been added to the 'messages' table:")
        print("  - tool_call_results (JSON): Stores tool execution results")
        print("  - metadata (JSON): Stores additional metadata like timestamps")
        print()
    else:
        print("\n❌ Migration verification failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
