"""
Test for the role column migration.
"""
import os
import sqlite3
import unittest
from tempfile import NamedTemporaryFile

from src.storage.migrations import add_role_column_to_users
from src.storage.models import UserRole

class TestRoleMigration(unittest.TestCase):
    """Test case for the role column migration."""
    
    def setUp(self):
        """Set up a temporary database for testing."""
        self.db_file = NamedTemporaryFile(delete=False)
        self.db_path = self.db_file.name
        self.db_file.close()
        
        # Create a temporary database with a users table
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table without the role column
        cursor.execute("""
        CREATE TABLE users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            fb_access_token TEXT,
            fb_refresh_token TEXT,
            token_expires_at TIMESTAMP,
            language TEXT NOT NULL DEFAULT 'ru',
            last_command TEXT,
            last_context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.commit()
        conn.close()
    
    def tearDown(self):
        """Clean up temporary files."""
        os.unlink(self.db_path)
    
    def test_add_role_column(self):
        """Test adding the role column to the users table."""
        # Run the migration
        success = add_role_column_to_users(self.db_path)
        
        # Verify the migration succeeded
        self.assertTrue(success, "Migration should succeed")
        
        # Verify the column was added with the correct default value
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if the column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        self.assertIn("role", columns, "The role column should exist")
        
        # Get the default value
        for column in cursor.execute("PRAGMA table_info(users)").fetchall():
            if column[1] == "role":
                default_value = column[4]
                break
        
        self.assertEqual(default_value, f"'{UserRole.PARTNER.value}'", 
                         f"Default value should be '{UserRole.PARTNER.value}'")
        
        # Test that running the migration again works correctly (idempotent)
        success = add_role_column_to_users(self.db_path)
        self.assertTrue(success, "Running the migration again should succeed")
        
        conn.close()

if __name__ == "__main__":
    unittest.main() 