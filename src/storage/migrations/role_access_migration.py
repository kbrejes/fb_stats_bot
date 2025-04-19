"""
Migration script to add role-based access control to the database.
"""
import logging
from enum import Enum, auto
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, func, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine import Engine
from sqlalchemy.schema import Table
from sqlalchemy.sql import text

from src.storage.database import engine, Base
from src.utils.logger import get_logger

logger = get_logger(__name__)

class UserRole(Enum):
    """Enum for user roles in the system."""
    ADMIN = "admin"
    TARGETOLOGIST = "targetologist"
    PARTNER = "partner"

def add_role_column():
    """Add role column to users table."""
    connection = engine.connect()
    transaction = connection.begin()
    try:
        # Check if the role column already exists
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        if 'role' not in columns:
            logger.info("Adding 'role' column to 'users' table...")
            connection.execute(text(
                "ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'partner'"
            ))
            logger.info("Column 'role' added successfully.")
        else:
            logger.info("Column 'role' already exists in 'users' table.")
        
        transaction.commit()
        return True
    except Exception as e:
        transaction.rollback()
        logger.error(f"Error adding 'role' column: {str(e)}")
        return False
    finally:
        connection.close()

def create_access_control_table():
    """Create the access_control table for managing partner access to campaigns."""
    connection = engine.connect()
    transaction = connection.begin()
    try:
        # Check if the access_control table already exists
        inspector = inspect(engine)
        if 'access_control' not in inspector.get_table_names():
            logger.info("Creating 'access_control' table...")
            connection.execute(text("""
                CREATE TABLE access_control (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    partner_id INTEGER NOT NULL,
                    admin_id INTEGER NOT NULL,
                    campaign_id VARCHAR(255) NOT NULL,
                    granted_at DATETIME NOT NULL,
                    expires_at DATETIME NULL,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    FOREIGN KEY (partner_id) REFERENCES users(telegram_id),
                    FOREIGN KEY (admin_id) REFERENCES users(telegram_id)
                )
            """))
            logger.info("Table 'access_control' created successfully.")
        else:
            logger.info("Table 'access_control' already exists.")
        
        transaction.commit()
        return True
    except Exception as e:
        transaction.rollback()
        logger.error(f"Error creating 'access_control' table: {str(e)}")
        return False
    finally:
        connection.close()

def create_access_request_table():
    """Create the access_request table for tracking partner access requests."""
    connection = engine.connect()
    transaction = connection.begin()
    try:
        # Check if the access_request table already exists
        inspector = inspect(engine)
        if 'access_request' not in inspector.get_table_names():
            logger.info("Creating 'access_request' table...")
            connection.execute(text("""
                CREATE TABLE access_request (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    partner_id INTEGER NOT NULL,
                    requested_at DATETIME NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    processed_by INTEGER NULL,
                    processed_at DATETIME NULL,
                    FOREIGN KEY (partner_id) REFERENCES users(telegram_id),
                    FOREIGN KEY (processed_by) REFERENCES users(telegram_id)
                )
            """))
            logger.info("Table 'access_request' created successfully.")
        else:
            logger.info("Table 'access_request' already exists.")
        
        transaction.commit()
        return True
    except Exception as e:
        transaction.rollback()
        logger.error(f"Error creating 'access_request' table: {str(e)}")
        return False
    finally:
        connection.close()

def run_migrations():
    """Run all migrations for role-based access control."""
    logger.info("Starting role-based access control migrations...")
    
    # Step 1: Add role column to users table
    if not add_role_column():
        logger.error("Failed to add role column. Aborting migrations.")
        return False
    
    # Step 2: Create access_control table
    if not create_access_control_table():
        logger.error("Failed to create access_control table. Aborting migrations.")
        return False
    
    # Step 3: Create access_request table
    if not create_access_request_table():
        logger.error("Failed to create access_request table. Aborting migrations.")
        return False
    
    logger.info("Role-based access control migrations completed successfully.")
    return True

if __name__ == "__main__":
    if run_migrations():
        print("✅ Role-based access control migrations completed successfully.")
    else:
        print("❌ Role-based access control migrations failed. Check the logs for details.") 