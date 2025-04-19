"""
Tests for access control utilities.
"""
import unittest
from unittest.mock import patch, MagicMock

from src.utils.access_control import check_user_role
from src.storage.models import UserRole

class TestAccessControl(unittest.TestCase):
    """Test case for access control functionality."""
    
    @patch('src.utils.access_control.get_session')
    def test_check_user_role_admin(self, mock_get_session):
        """Test checking user role for admin."""
        # Setup mock
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        
        # Setup user mock
        mock_user = MagicMock()
        mock_user.get_role.return_value = UserRole.ADMIN
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Test admin access
        self.assertTrue(check_user_role(123, UserRole.ADMIN))
        
        # Test targetologist access (admin can access)
        self.assertTrue(check_user_role(123, UserRole.TARGETOLOGIST))
        
        # Test partner access (admin can access)
        self.assertTrue(check_user_role(123, UserRole.PARTNER))
    
    @patch('src.utils.access_control.get_session')
    def test_check_user_role_targetologist(self, mock_get_session):
        """Test checking user role for targetologist."""
        # Setup mock
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        
        # Setup user mock
        mock_user = MagicMock()
        mock_user.get_role.return_value = UserRole.TARGETOLOGIST
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Test admin access (targetologist cannot access)
        self.assertFalse(check_user_role(123, UserRole.ADMIN))
        
        # Test targetologist access
        self.assertTrue(check_user_role(123, UserRole.TARGETOLOGIST))
        
        # Test partner access (targetologist can access)
        self.assertTrue(check_user_role(123, UserRole.PARTNER))
    
    @patch('src.utils.access_control.get_session')
    def test_check_user_role_partner(self, mock_get_session):
        """Test checking user role for partner."""
        # Setup mock
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        
        # Setup user mock
        mock_user = MagicMock()
        mock_user.get_role.return_value = UserRole.PARTNER
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Test admin access (partner cannot access)
        self.assertFalse(check_user_role(123, UserRole.ADMIN))
        
        # Test targetologist access (partner cannot access)
        self.assertFalse(check_user_role(123, UserRole.TARGETOLOGIST))
        
        # Test partner access
        self.assertTrue(check_user_role(123, UserRole.PARTNER))
    
    @patch('src.utils.access_control.get_session')
    def test_check_user_role_user_not_found(self, mock_get_session):
        """Test checking user role when user is not found."""
        # Setup mock
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        
        # User not found
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # All access should be denied
        self.assertFalse(check_user_role(123, UserRole.ADMIN))
        self.assertFalse(check_user_role(123, UserRole.TARGETOLOGIST))
        self.assertFalse(check_user_role(123, UserRole.PARTNER))
    
    @patch('src.utils.access_control.get_session')
    def test_check_user_role_exception(self, mock_get_session):
        """Test checking user role when an exception occurs."""
        # Setup mock to raise exception
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_session.query.side_effect = Exception("Database error")
        
        # All access should be denied on exception
        self.assertFalse(check_user_role(123, UserRole.ADMIN))
        self.assertFalse(check_user_role(123, UserRole.TARGETOLOGIST))
        self.assertFalse(check_user_role(123, UserRole.PARTNER))

if __name__ == "__main__":
    unittest.main() 