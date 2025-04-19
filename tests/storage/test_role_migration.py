#!/usr/bin/env python
"""
Test script for role-based access control migrations.
Uses an in-memory SQLite database to test migrations without affecting production data.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

# Add project root to path if needed
sys.path.append(str(Path(__file__).parent.parent.parent))

# Create a temporary environment with in-memory database
os.environ["ENVIRONMENT"] = "test"
TestBase = declarative_base()


class TestRoleMigration(unittest.TestCase):
    """Test case for role-based access control migrations."""
    
    def setUp(self):
        """Set up in-memory database for testing."""
        # Create a temporary database file
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        
        # Create session
        self.Session = sessionmaker(bind=self.engine)
        
        # Create users table for testing
        with self.engine.begin() as connection:
            connection.execute(text("""
                CREATE TABLE users (
                    telegram_id INTEGER PRIMARY KEY,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    fb_access_token TEXT,
                    fb_refresh_token TEXT,
                    token_expires_at DATETIME,
                    language VARCHAR(10) DEFAULT 'ru' NOT NULL,
                    last_command VARCHAR(255),
                    last_context TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Insert test users
            connection.execute(text("""
                INSERT INTO users (telegram_id, username, first_name, language)
                VALUES 
                    (100, 'test_admin', 'Admin', 'ru'),
                    (101, 'test_targetolog', 'Target', 'ru'),
                    (102, 'test_partner', 'Partner', 'ru')
            """))
        
        # Override engine in migration module
        from src.storage.migrations import role_access_migration
        role_access_migration.engine = self.engine
    
    def tearDown(self):
        """Clean up after tests."""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_add_role_column(self):
        """Test adding role column to users table."""
        # Import the migration function
        from src.storage.migrations.role_access_migration import add_role_column
        
        # Run migration
        self.assertTrue(add_role_column())
        
        # Check if column was added
        inspector = inspect(self.engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        self.assertIn('role', columns)
        
        # Check if default value was set correctly
        with self.engine.connect() as connection:
            result = connection.execute(text("SELECT telegram_id, role FROM users")).fetchall()
            self.assertEqual(len(result), 3)
            
            # Check all users have default partner role
            for row in result:
                self.assertEqual(row[1], 'partner')
    
    def test_create_access_control_table(self):
        """Test creating access_control table."""
        # Import the migration function
        from src.storage.migrations.role_access_migration import create_access_control_table
        
        # Run migration
        self.assertTrue(create_access_control_table())
        
        # Check if table was created
        inspector = inspect(self.engine)
        self.assertIn('access_control', inspector.get_table_names())
        
        # Check table structure
        columns = {col['name'] for col in inspector.get_columns('access_control')}
        expected_columns = {'id', 'partner_id', 'admin_id', 'campaign_id', 
                          'granted_at', 'expires_at', 'is_active'}
        self.assertEqual(columns, expected_columns)
    
    def test_create_access_request_table(self):
        """Test creating access_request table."""
        # Import the migration function
        from src.storage.migrations.role_access_migration import create_access_request_table
        
        # Run migration
        self.assertTrue(create_access_request_table())
        
        # Check if table was created
        inspector = inspect(self.engine)
        self.assertIn('access_request', inspector.get_table_names())
        
        # Check table structure
        columns = {col['name'] for col in inspector.get_columns('access_request')}
        expected_columns = {'id', 'partner_id', 'requested_at', 'status', 
                          'processed_by', 'processed_at'}
        self.assertEqual(columns, expected_columns)
    
    def test_run_migrations(self):
        """Test running all migrations together."""
        # Import the migration function
        from src.storage.migrations.role_access_migration import run_migrations
        
        # Run migrations
        self.assertTrue(run_migrations())
        
        # Check all tables and columns
        inspector = inspect(self.engine)
        
        # Check role column
        columns = [col['name'] for col in inspector.get_columns('users')]
        self.assertIn('role', columns)
        
        # Check access_control table
        self.assertIn('access_control', inspector.get_table_names())
        
        # Check access_request table
        self.assertIn('access_request', inspector.get_table_names())
        
        # Test changing a user role to admin
        with self.engine.begin() as connection:
            connection.execute(text("""
                UPDATE users SET role = 'admin' WHERE telegram_id = 100
            """))
            
            result = connection.execute(text("""
                SELECT role FROM users WHERE telegram_id = 100
            """)).fetchone()
            
            self.assertIsNotNone(result)
            self.assertEqual(result[0], 'admin')


if __name__ == "__main__":
    unittest.main() 