"""
Unit tests for utils.py - Testing logging and utility functions
"""
import unittest
import sys
import os
import tempfile
import shutil
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.utils import (
    setup_logging,
    overlay_text_on_frame,
    get_formatted_timestamp,
    get_formatted_datetime,
    get_video_filename,
    ensure_directory_exists,
    get_disk_usage,
    format_bytes,
    parse_gps_coordinate,
    smooth_gps_coordinates,
    ConfigManager,
    DEFAULT_CONFIG
)


class TestLoggingRotation(unittest.TestCase):
    """Test log rotation functionality."""
    
    def setUp(self):
        """Create temporary directory for test logs."""
        self.test_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.test_dir, 'test.log')
    
    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)
        # Clear all handlers
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
    
    def test_log_rotation_setup(self):
        """Test that log rotation is properly configured."""
        setup_logging(
            log_file=self.log_file,
            max_bytes=1024,  # 1KB for testing
            backup_count=3
        )
        
        # Check that log file is created
        self.assertTrue(os.path.exists(self.log_file))
        
        # Get the root logger
        logger = logging.getLogger()
        
        # Check that RotatingFileHandler was added
        from logging.handlers import RotatingFileHandler
        has_rotating_handler = any(
            isinstance(h, RotatingFileHandler) for h in logger.handlers
        )
        self.assertTrue(has_rotating_handler)
    
    def test_log_rotation_occurs(self):
        """Test that logs actually rotate when size limit reached."""
        setup_logging(
            log_file=self.log_file,
            max_bytes=1024,  # 1KB
            backup_count=3
        )
        
        logger = logging.getLogger()
        
        # Write enough logs to trigger rotation
        for i in range(100):
            logger.info(f"Test log entry {i} " + "X" * 100)
        
        # Check that backup files were created
        backup_files = [
            f for f in os.listdir(self.test_dir)
            if f.startswith('test.log.')
        ]
        
        # Should have at least one backup
        self.assertGreater(len(backup_files), 0)
    
    def test_backup_count_limit(self):
        """Test that backup count is respected."""
        setup_logging(
            log_file=self.log_file,
            max_bytes=500,  # Small size to force rotation
            backup_count=2  # Only keep 2 backups
        )
        
        logger = logging.getLogger()
        
        # Write many logs to create multiple rotations
        for i in range(300):
            logger.info(f"Test log entry {i} " + "Y" * 100)
        
        # Count backup files
        backup_files = [
            f for f in os.listdir(self.test_dir)
            if f.startswith('test.log.')
        ]
        
        # Should not exceed backup_count
        self.assertLessEqual(len(backup_files), 2)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions."""
    
    def test_get_formatted_timestamp(self):
        """Test timestamp formatting."""
        timestamp = get_formatted_timestamp()
        # Should be in YYYYMMDD-HHMMSS format
        self.assertEqual(len(timestamp), 15)
        self.assertEqual(timestamp[8], '-')
    
    def test_get_formatted_datetime(self):
        """Test datetime formatting."""
        dt = get_formatted_datetime()
        # Should be in YYYY-MM-DD HH:MM:SS format
        self.assertRegex(dt, r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')
    
    def test_get_video_filename(self):
        """Test video filename generation."""
        filename = get_video_filename()
        self.assertTrue(filename.startswith('jetsoncam-'))
        self.assertTrue(filename.endswith('.mp4'))
    
    def test_ensure_directory_exists(self):
        """Test directory creation."""
        test_dir = tempfile.mktemp()
        try:
            ensure_directory_exists(test_dir)
            self.assertTrue(os.path.exists(test_dir))
            self.assertTrue(os.path.isdir(test_dir))
        finally:
            if os.path.exists(test_dir):
                os.rmdir(test_dir)
    
    def test_format_bytes(self):
        """Test byte formatting."""
        self.assertEqual(format_bytes(1024), '1.00 KB')
        self.assertEqual(format_bytes(1024 * 1024), '1.00 MB')
        self.assertEqual(format_bytes(1024 * 1024 * 1024), '1.00 GB')
    
    def test_parse_gps_coordinate_valid(self):
        """Test GPS coordinate parsing with valid data."""
        # Test latitude (DDMM.MMMM format)
        lat = parse_gps_coordinate('3723.2475', 'N')
        self.assertIsNotNone(lat)
        self.assertAlmostEqual(lat, 37.387458, places=4)
        
        # Test negative (South)
        lat_s = parse_gps_coordinate('3723.2475', 'S')
        self.assertIsNotNone(lat_s)
        self.assertLess(lat_s, 0)
        
        # Test longitude
        lon = parse_gps_coordinate('12158.3416', 'W')
        self.assertIsNotNone(lon)
        self.assertLess(lon, 0)  # West is negative
    
    def test_parse_gps_coordinate_invalid(self):
        """Test GPS coordinate parsing with invalid data."""
        self.assertIsNone(parse_gps_coordinate('', 'N'))
        self.assertIsNone(parse_gps_coordinate(None, 'N'))
        self.assertIsNone(parse_gps_coordinate('invalid', 'N'))
        self.assertIsNone(parse_gps_coordinate('123', None))
    
    def test_smooth_gps_coordinates(self):
        """Test GPS coordinate smoothing."""
        # Create buffer of coordinates
        coords = [
            (37.387, -122.082),
            (37.388, -122.083),
            (37.389, -122.084),
            (37.390, -122.085),
            (37.391, -122.086),
        ]
        
        # Should return average of last 5
        smoothed = smooth_gps_coordinates(coords, buffer_size=5)
        self.assertIsNotNone(smoothed)
        
        # Check that it's approximately the average
        avg_lat = sum(c[0] for c in coords) / len(coords)
        avg_lon = sum(c[1] for c in coords) / len(coords)
        
        self.assertAlmostEqual(smoothed[0], avg_lat, places=6)
        self.assertAlmostEqual(smoothed[1], avg_lon, places=6)
    
    def test_smooth_gps_coordinates_insufficient_data(self):
        """Test smoothing with insufficient data."""
        coords = [(37.387, -122.082), (37.388, -122.083)]
        
        # Should return None if buffer_size not met
        smoothed = smooth_gps_coordinates(coords, buffer_size=5)
        self.assertIsNone(smoothed)


class TestConfigManager(unittest.TestCase):
    """Test configuration manager."""
    
    def test_config_manager_get_set(self):
        """Test basic get/set operations."""
        config = ConfigManager({'key1': 'value1'})
        
        # Test get
        self.assertEqual(config.get('key1'), 'value1')
        self.assertIsNone(config.get('nonexistent'))
        self.assertEqual(config.get('nonexistent', 'default'), 'default')
        
        # Test set
        config.set('key2', 'value2')
        self.assertEqual(config.get('key2'), 'value2')
    
    def test_default_config_exists(self):
        """Test that default configuration is defined."""
        self.assertIsNotNone(DEFAULT_CONFIG)
        self.assertIn('VIDEO_DIR', DEFAULT_CONFIG)
        self.assertIn('DB_PATH', DEFAULT_CONFIG)
        self.assertIn('WEB_PORT', DEFAULT_CONFIG)


if __name__ == '__main__':
    unittest.main()
