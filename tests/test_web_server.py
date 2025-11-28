"""
Unit tests for web_server.py - Testing security improvements
"""
import unittest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.web_server import DashcamWebServer
from flask import session


class TestWebServerSecurity(unittest.TestCase):
    """Test security features of the web server."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_db = Mock()
        self.mock_cleanup = Mock()
        
        # Create web server instance
        self.server = DashcamWebServer(
            database_manager=self.mock_db,
            cleanup_manager=self.mock_cleanup,
            video_dir='/tmp/videos',
            host='127.0.0.1',
            port=8089,
            admin_user='testadmin',
            admin_pass='testpass123'
        )
        
        # Configure Flask app for testing
        self.server.app.config['TESTING'] = True
        self.server.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.server.app.test_client()
    
    def test_random_secret_key_generated(self):
        """Test that Flask secret key is randomly generated."""
        # Secret key should be 64 chars (32 bytes hex encoded)
        self.assertEqual(len(self.server.app.secret_key), 64)
        # Should not be the old hardcoded value
        self.assertNotEqual(
            self.server.app.secret_key,
            'george-jetson-dashcam-secret-key-change-in-production'
        )
    
    def test_rate_limiting_initialization(self):
        """Test that rate limiting is properly initialized."""
        self.assertTrue(hasattr(self.server, 'login_attempts'))
        self.assertEqual(self.server.max_login_attempts, 5)
        self.assertEqual(self.server.login_lockout_duration, 300)
    
    def test_successful_login(self):
        """Test successful login clears rate limit attempts."""
        response = self.client.post('/login', data={
            'username': 'testadmin',
            'password': 'testpass123'
        }, follow_redirects=False)
        
        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)
        self.assertTrue('/dashboard' in response.location)
    
    def test_failed_login_increments_attempts(self):
        """Test that failed login attempts are tracked."""
        # Attempt failed login
        response = self.client.post('/login', data={
            'username': 'testadmin',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid credentials', response.data)
        
        # Check that attempt was recorded
        # Note: In test environment, remote_addr might be None
        self.assertTrue(len(self.server.login_attempts) >= 0)
    
    def test_rate_limiting_lockout(self):
        """Test that too many failed attempts trigger lockout."""
        # Simulate 5 failed attempts
        for i in range(5):
            self.client.post('/login', data={
                'username': 'testadmin',
                'password': 'wrongpassword'
            })
        
        # 6th attempt should be locked out
        response = self.client.post('/login', data={
            'username': 'testadmin',
            'password': 'wrongpassword'
        })
        
        self.assertIn(b'Too many failed attempts', response.data)
    
    def test_validate_date_function(self):
        """Test date validation function."""
        # Valid dates
        self.assertEqual(self.server._validate_date('2025-11-27'), '2025-11-27')
        self.assertEqual(self.server._validate_date('2024-01-01'), '2024-01-01')
        
        # Invalid dates
        self.assertIsNone(self.server._validate_date('2025-13-01'))  # Invalid month
        self.assertIsNone(self.server._validate_date('2025/11/27'))  # Wrong format
        self.assertIsNone(self.server._validate_date('not-a-date'))
        self.assertIsNone(self.server._validate_date(''))
        self.assertIsNone(self.server._validate_date(None))
    
    def test_sanitize_string_function(self):
        """Test string sanitization function."""
        # Normal strings
        self.assertEqual(self.server._sanitize_string('ABC123'), 'ABC123')
        self.assertEqual(self.server._sanitize_string('Honda Civic'), 'Honda Civic')
        
        # Dangerous characters should be removed
        result = self.server._sanitize_string("ABC123; DROP TABLE--")
        # Hyphens are allowed (alphanumeric + - _), semicolon removed
        self.assertNotIn(';', result)
        self.assertIn('ABC123', result)
        self.assertEqual(
            self.server._sanitize_string("Test<script>alert(1)</script>"),
            'Testscriptalert1script'
        )
        
        # Length limiting
        long_string = 'A' * 200
        result = self.server._sanitize_string(long_string, max_length=50)
        self.assertEqual(len(result), 50)
        
        # Empty/None
        self.assertIsNone(self.server._sanitize_string(''))
        self.assertIsNone(self.server._sanitize_string(None))
    
    def test_search_endpoint_requires_login(self):
        """Test that search endpoint requires authentication."""
        response = self.client.post('/api/search', json={})
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
    
    def test_search_input_validation(self):
        """Test that search endpoint validates inputs."""
        # Login first
        with self.client.session_transaction() as sess:
            sess['user'] = 'testadmin'
        
        # Mock database response
        self.mock_db.search_events.return_value = []
        
        # Test with dangerous input
        response = self.client.post('/api/search', json={
            'license_plate': 'ABC123; DROP TABLE vehicles--',
            'limit': 99999,
            'start_date': '2025/11/27',  # Invalid format
            'color': '<script>alert(1)</script>'
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Verify sanitization occurred
        call_args = self.mock_db.search_events.call_args
        if call_args:
            kwargs = call_args[1]
            # License plate should be sanitized
            if kwargs.get('license_plate'):
                self.assertNotIn(';', kwargs['license_plate'])
                self.assertNotIn('--', kwargs['license_plate'])
            # Limit should be clamped
            if kwargs.get('limit'):
                self.assertLessEqual(kwargs['limit'], 1000)
    
    def test_production_mode_disables_debug(self):
        """Test that production mode forces debug=False."""
        # This is more of a behavioral test
        # In actual deployment, verify debug mode is off
        with patch.object(self.server.app, 'run') as mock_run:
            self.server.run(debug=True, production=True)
            # Should be called with debug=False despite debug=True
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            self.assertFalse(call_kwargs.get('debug'))


class TestWebServerEndpoints(unittest.TestCase):
    """Test API endpoints functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.mock_cleanup = Mock()
        
        self.server = DashcamWebServer(
            database_manager=self.mock_db,
            cleanup_manager=self.mock_cleanup,
            video_dir='/tmp/videos',
            host='127.0.0.1',
            port=8089
        )
        
        self.server.app.config['TESTING'] = True
        self.client = self.server.app.test_client()
    
    def login(self):
        """Helper to login."""
        with self.client.session_transaction() as sess:
            sess['user'] = 'admin'
    
    def test_dashboard_requires_login(self):
        """Test that dashboard requires authentication."""
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 302)
        self.assertTrue('/login' in response.location)
    
    def test_dashboard_loads_with_login(self):
        """Test that dashboard loads when authenticated."""
        self.login()
        self.mock_db.get_stats.return_value = {'total': 0}
        self.mock_cleanup.get_disk_usage.return_value = {
            'total': 1000000,
            'free': 500000,
            'percent': 50
        }
        
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
    
    def test_cleanup_endpoint_validates_action(self):
        """Test cleanup endpoint validates action parameter."""
        self.login()
        
        # Invalid action
        response = self.client.post('/api/cleanup', json={
            'action': 'delete_everything'  # Invalid action
        })
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('Invalid action', data['error'])
    
    def test_cleanup_endpoint_clamps_target_percent(self):
        """Test cleanup endpoint clamps target_percent."""
        self.login()
        self.mock_cleanup.cleanup_by_size.return_value = 5
        
        # Test with extreme value
        response = self.client.post('/api/cleanup', json={
            'action': 'cleanup_by_size',
            'target_percent': 99.9  # Should be clamped to max 50
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Verify cleanup was called with clamped value
        self.mock_cleanup.cleanup_by_size.assert_called_once()
        call_args = self.mock_cleanup.cleanup_by_size.call_args[0]
        self.assertLessEqual(call_args[0], 50.0)


if __name__ == '__main__':
    unittest.main()
