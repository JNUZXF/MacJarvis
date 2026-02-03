#!/usr/bin/env python3
"""
File: backend/scripts/run_migration.py
Purpose: Run database migration script
"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import get_settings


async def run_migration(migration_file: str):
    """Run a SQL migration file"""
    settings = get_settings()
    
    # Create engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )
    
    # Read migration SQL
    migration_path = backend_dir / migration_file
    print(f"Reading migration from: {migration_path}")
    
    with open(migration_path, 'r') as f:
        sql = f.read()
    
    async with engine.begin() as conn:
        # Execute each statement
        for statement in sql.split(';'):
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    await conn.execute(text(statement))
                    print(f'✓ Executed: {statement[:60]}...')
                except Exception as e:
                    error_msg = str(e).lower()
                    if 'already exists' in error_msg or 'duplicate column' in error_msg:
                        print(f'⚠ Skipped (already exists): {statement[:60]}...')
                    else:
                        print(f'✗ Error: {e}')
                        raise
        
        print('✓ Migration completed successfully')
    
    await engine.dispose()


if __name__ == "__main__":
    migration_file = sys.argv[1] if len(sys.argv) > 1 else "migrations/simplify_memory_system.sql"
    asyncio.run(run_migration(migration_file))
