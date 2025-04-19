"""
Database migrations for the application.
"""
import logging
import sqlite3
from pathlib import Path
from typing import Optional

from config.settings import DB_PATH
from src.storage.models import UserRole

logger = logging.getLogger(__name__)

def add_role_column_to_users(db_path: Optional[str] = None) -> bool:
    """
    Adds a role column to the users table if it doesn't exist.
    
    Args:
        db_path: Path to the database file. If None, uses the default DB_PATH from settings.
        
    Returns:
        True if migration was successful, False otherwise.
    """
    path = db_path or DB_PATH
    if not Path(path).exists():
        logger.error(f"Database file not found: {path}")
        return False
        
    conn = None
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "role" not in columns:
            logger.info("Adding 'role' column to 'users' table")
            cursor.execute(f"ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT '{UserRole.PARTNER.value}'")
            conn.commit()
            logger.info("Migration successful: Added 'role' column to 'users' table")
            return True
        else:
            logger.info("Column 'role' already exists in 'users' table")
            return True
            
    except sqlite3.Error as e:
        logger.error(f"SQLite error during migration: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def run_all_migrations(db_path: Optional[str] = None) -> bool:
    """
    Runs all migrations in the correct order.
    
    Args:
        db_path: Path to the database file. If None, uses the default DB_PATH from settings.
        
    Returns:
        True if all migrations were successful, False otherwise.
    """
    # Run migrations in order
    migrations = [
        add_role_column_to_users,
    ]
    
    path = db_path or DB_PATH
    success = True
    
    for migration in migrations:
        logger.info(f"Running migration: {migration.__name__}")
        if not migration(path):
            logger.error(f"Migration failed: {migration.__name__}")
            success = False
            break
    
    if success:
        logger.info("All migrations completed successfully")
    else:
        logger.error("Some migrations failed")
        
    return success

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    # Run all migrations
    run_all_migrations() 