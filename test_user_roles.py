"""
Tests for user role functionality.
"""
import unittest

from src.storage.models import User, UserRole

class TestUserRoles(unittest.TestCase):
    """Test case for user role functionality."""
    
    def setUp(self):
        """Set up a test user for each test."""
        self.user = User()
        self.user.telegram_id = 12345
        # Initialize with default role to avoid warnings
        self.user.role = UserRole.PARTNER.value
    
    def test_default_role(self):
        """Test that the default role is PARTNER."""
        # By default, the role should be PARTNER
        self.assertEqual(self.user.get_role(), UserRole.PARTNER)
        self.assertFalse(self.user.is_admin())
        self.assertFalse(self.user.is_targetologist())
        self.assertTrue(self.user.is_partner())
    
    def test_set_role(self):
        """Test setting user roles."""
        # Test setting and getting admin role
        self.user.set_role(UserRole.ADMIN)
        self.assertEqual(self.user.role, UserRole.ADMIN.value)
        self.assertEqual(self.user.get_role(), UserRole.ADMIN)
        self.assertTrue(self.user.is_admin())
        self.assertFalse(self.user.is_targetologist())
        self.assertFalse(self.user.is_partner())
        
        # Test setting and getting targetologist role
        self.user.set_role(UserRole.TARGETOLOGIST)
        self.assertEqual(self.user.role, UserRole.TARGETOLOGIST.value)
        self.assertEqual(self.user.get_role(), UserRole.TARGETOLOGIST)
        self.assertFalse(self.user.is_admin())
        self.assertTrue(self.user.is_targetologist())
        self.assertFalse(self.user.is_partner())
        
        # Test setting and getting partner role
        self.user.set_role(UserRole.PARTNER)
        self.assertEqual(self.user.role, UserRole.PARTNER.value)
        self.assertEqual(self.user.get_role(), UserRole.PARTNER)
        self.assertFalse(self.user.is_admin())
        self.assertFalse(self.user.is_targetologist())
        self.assertTrue(self.user.is_partner())
    
    def test_invalid_role(self):
        """Test handling of invalid roles."""
        # Set an invalid role directly
        self.user.role = 'invalid_role'
        
        # get_role should return the default PARTNER role
        self.assertEqual(self.user.get_role(), UserRole.PARTNER)
        self.assertFalse(self.user.is_admin())
        self.assertFalse(self.user.is_targetologist())
        self.assertTrue(self.user.is_partner())

if __name__ == "__main__":
    unittest.main() 