#!/usr/bin/env python3
"""
Migration script to add new tables and update user table for permissions relationship.

This script performs the following actions:
1. Creates a join table 'accounts_to_users' for many-to-many relation between users and accounts.
2. Creates a 'permissions' table for storing RBAC privileges. In each row of the table, a single permission is stored corresponding to a role. Multiple records may have the same role.
3. Alters the 'users' table to add a new column 'role' (a string) to store the user's role,
   which will be used to fetch from the permissions table all permissions associated with that role.
   
Note: ALTER TABLE commands may vary based on the database engine.
"""

from sqlalchemy import text
from src.storage.database import engine
from src.utils.logger import get_logger

logger = get_logger(__name__)

def run_migration():
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. Create join table accounts_to_users
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS accounts_to_users (
                    user_id INTEGER NOT NULL,
                    account_id INTEGER NOT NULL,
                    PRIMARY KEY (user_id, account_id),
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
                );
            """))
            logger.info("Table 'accounts_to_users' created successfully.")
            
            # 2. Create permissions table, allowing multiple rows per role
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role VARCHAR(255) NOT NULL,
                    permission TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """))
            logger.info("Table 'permissions' created successfully.")
            
            # 3. Alter users table to add role column (string)
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN role VARCHAR(255);
            """))
            logger.info("Column 'role' added to 'users' table.")
            
            # 4. No foreign key constraint is added since permissions.role is not unique.
            
            trans.commit()
            logger.info("Migration executed successfully.")
        except Exception as e:
            trans.rollback()
            logger.error(f"Migration failed: {e}")
            raise

if __name__ == "__main__":
    run_migration() 