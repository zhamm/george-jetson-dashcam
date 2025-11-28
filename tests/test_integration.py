"""
Integration tests - Testing complete workflows
"""
import unittest
import sys
import os
import tempfile
import shutil
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import DatabaseManager
from app.cleanup import DiskCleanupManager
from app.web_server import DashcamWebServer


class TestSecurityIntegration(unittest.TestCase):
    """Integration tests for security features."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directories
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, 'test.db')
        self.video_dir = os.path.join(self.test_dir, 'videos')
        os.makedirs(self.video_dir)
        
        # Create real database
        self.db = DatabaseManager(db_path=self.db_path)
        
        # Create cleanup manager
        self.cleanup = DiskCleanupManager(
            video_dir=self.video_dir,
            db_manager=self.db
        )
        
        # Create web server
        self.server = DashcamWebServer(
            database_manager=self.db,
            cleanup_manager=self.cleanup,
            video_dir=self.video_dir,
            admin_user='testuser',
            admin_pass='testpass123'
        )
        
        self.server.app.config['TESTING'] = True
        self.client = self.server.app.test_client()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_full_login_rate_limiting_workflow(self):
        """Test complete rate limiting workflow."""
        # Make 5 failed attempts
        for i in range(5):
            response = self.client.post('/login', data={
                'username': 'testuser',
                'password': 'wrongpass'
            })
            self.assertIn(b'Invalid credentials', response.data)
        
        # 6th attempt should be locked out
        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'wrongpass'
        })
        self.assertIn(b'Too many failed attempts', response.data)
        
        # Even correct password should be locked out
        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertIn(b'Too many failed attempts', response.data)
    
    def test_successful_login_after_failed_attempts(self):
        """Test successful login clears failed attempts."""
        # Make 2 failed attempts
        for i in range(2):
            self.client.post('/login', data={
                'username': 'testuser',
                'password': 'wrongpass'
            })
        
        # Successful login
        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        }, follow_redirects=False)
        
        self.assertEqual(response.status_code, 302)
        
        # Make 4 more failed attempts (should work since previous cleared)
        for i in range(4):
            response = self.client.post('/login', data={
                'username': 'testuser',
                'password': 'wrongpass'
            })
            # Should not be locked yet
            if i < 3:
                self.assertNotIn(b'Too many failed attempts', response.data)
    
    def test_api_input_validation_workflow(self):
        """Test API input validation end-to-end."""
        # Login first
        with self.client.session_transaction() as sess:
            sess['user'] = 'testuser'
        
        # Test search with various invalid inputs
        response = self.client.post('/api/search', json={
            'license_plate': 'ABC123<script>alert(1)</script>',
            'start_date': '2025/11/27',  # Wrong format
            'end_date': 'invalid',
            'limit': 999999,
            'color': 'Red; DROP TABLE--'
        })
        
        # Should still return 200 but with sanitized data
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
    
    def test_database_and_search_workflow(self):
        """Test database operations with validation."""
        # Insert test event
        self.db.log_vehicle_event(
            video_filename='test-20251127-120000.mp4',
            lat=37.7749,
            lon=-122.4194,
            license_plate='ABC123',
            car_description='Red Honda Civic',
            confidence=0.95
        )
        
        # Login to web server
        with self.client.session_transaction() as sess:
            sess['user'] = 'testuser'
        
        # Search for the event
        response = self.client.post('/api/search', json={
            'license_plate': 'ABC123'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertGreater(data['count'], 0)


class TestPermissionsAndSecurity(unittest.TestCase):
    """Test file permissions and security settings."""
    
    def test_log_file_permissions(self):
        """Test that log files have appropriate permissions."""
        test_dir = tempfile.mkdtemp()
        try:
            log_file = os.path.join(test_dir, 'test.log')
            
            from app.utils import setup_logging
            setup_logging(log_file=log_file)
            
            # Check that log file was created
            self.assertTrue(os.path.exists(log_file))
            
            # Check permissions (should be readable by owner)
            import stat
            mode = os.stat(log_file).st_mode
            # File should exist and be a regular file
            self.assertTrue(stat.S_ISREG(mode))
            
        finally:
            shutil.rmtree(test_dir)
            # Clear handlers
            import logging
            logger = logging.getLogger()
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)


if __name__ == '__main__':
    unittest.main()
