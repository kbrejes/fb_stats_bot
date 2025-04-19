"""
Tests for access tables migrations.
"""
import os
import sqlite3
import unittest
from tempfile import NamedTemporaryFile

from src.storage.migrations import (
    create_access_request_table,
    create_access_control_table
)

class TestAccessTablesMigration(unittest.TestCase):
    """Test case for access tables migrations."""
    
    def setUp(self):
        """Set up a temporary database for testing."""
        self.db_file = NamedTemporaryFile(delete=False)
        self.db_path = self.db_file.name
        self.db_file.close()
        
        # Create a temporary database with users table
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table for foreign key references
        cursor.execute("""
        CREATE TABLE users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            role VARCHAR(20) NOT NULL DEFAULT 'partner'
        )
        """)
        
        conn.commit()
        conn.close()
    
    def tearDown(self):
        """Clean up temporary files."""
        os.unlink(self.db_path)
    
    def test_create_access_request_table(self):
        """Test creating the access_requests table."""
        # Run the migration
        success = create_access_request_table(self.db_path)
        
        # Verify the migration succeeded
        self.assertTrue(success, "Migration should succeed")
        
        # Verify the table was created
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='access_requests'")
        table_exists = cursor.fetchone() is not None
        self.assertTrue(table_exists, "The access_requests table should exist")
        
        # Check the table schema
        cursor.execute("PRAGMA table_info(access_requests)")
        columns = {column[1]: column for column in cursor.fetchall()}
        
        self.assertIn("id", columns, "The table should have an id column")
        self.assertIn("partner_id", columns, "The table should have a partner_id column")
        self.assertIn("status", columns, "The table should have a status column")
        self.assertIn("requested_at", columns, "The table should have a requested_at column")
        self.assertIn("processed_at", columns, "The table should have a processed_at column")
        self.assertIn("processed_by", columns, "The table should have a processed_by column")
        
        # Test idempotence
        success = create_access_request_table(self.db_path)
        self.assertTrue(success, "Running the migration again should succeed")
        
        conn.close()
    
    def test_create_access_control_table(self):
        """Test creating the access_controls table."""
        # Run the migration
        success = create_access_control_table(self.db_path)
        
        # Verify the migration succeeded
        self.assertTrue(success, "Migration should succeed")
        
        # Verify the table was created
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='access_controls'")
        table_exists = cursor.fetchone() is not None
        self.assertTrue(table_exists, "The access_controls table should exist")
        
        # Check the table schema
        cursor.execute("PRAGMA table_info(access_controls)")
        columns = {column[1]: column for column in cursor.fetchall()}
        
        self.assertIn("id", columns, "The table should have an id column")
        self.assertIn("partner_id", columns, "The table should have a partner_id column")
        self.assertIn("admin_id", columns, "The table should have an admin_id column")
        self.assertIn("campaign_id", columns, "The table should have a campaign_id column")
        self.assertIn("granted_at", columns, "The table should have a granted_at column")
        self.assertIn("expires_at", columns, "The table should have an expires_at column")
        self.assertIn("is_active", columns, "The table should have an is_active column")
        
        # Test idempotence
        success = create_access_control_table(self.db_path)
        self.assertTrue(success, "Running the migration again should succeed")
        
        conn.close()

if __name__ == "__main__":
    unittest.main() 