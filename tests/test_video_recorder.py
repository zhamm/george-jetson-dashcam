"""
Unit tests for video_recorder.py - Testing resource cleanup
"""
import unittest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.video_recorder import VideoRecorder


class TestVideoRecorderResourceCleanup(unittest.TestCase):
    """Test resource cleanup in video recorder."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.recorder = VideoRecorder(
            output_dir='/tmp/test_videos',
            width=1920,
            height=1080,
            fps=30,
            segment_duration=300
        )
    
    def test_close_encoder_normal(self):
        """Test normal encoder closing."""
        # Mock FFmpeg process
        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.wait = Mock(return_value=0)
        
        self.recorder.writer = mock_process
        
        # Close encoder
        self.recorder._close_encoder()
        
        # Verify cleanup occurred
        mock_process.stdin.close.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)
        self.assertIsNone(self.recorder.writer)
    
    def test_close_encoder_timeout(self):
        """Test encoder closing with timeout."""
        # Mock FFmpeg process that times out
        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.wait = Mock(side_effect=subprocess.TimeoutExpired('ffmpeg', 5))
        mock_process.kill = Mock()
        
        self.recorder.writer = mock_process
        
        # Close encoder
        self.recorder._close_encoder()
        
        # Verify force kill was called
        mock_process.kill.assert_called()
        self.assertIsNone(self.recorder.writer)
    
    def test_close_encoder_error_handling(self):
        """Test encoder closing with errors."""
        # Mock FFmpeg process that raises exception
        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdin.close = Mock(side_effect=Exception("Test error"))
        mock_process.wait = Mock()
        mock_process.kill = Mock()
        
        self.recorder.writer = mock_process
        
        # Should not raise exception
        self.recorder._close_encoder()
        
        # Verify cleanup still occurred
        self.assertIsNone(self.recorder.writer)
    
    def test_close_encoder_none_safe(self):
        """Test closing encoder when writer is None."""
        self.recorder.writer = None
        
        # Should not raise exception
        self.recorder._close_encoder()
        
        self.assertIsNone(self.recorder.writer)
    
    def test_close_camera(self):
        """Test camera closing."""
        # Mock camera capture
        mock_cap = Mock()
        mock_cap.release = Mock()
        
        self.recorder.cap = mock_cap
        
        # Close camera
        self.recorder._close_camera()
        
        # Verify cleanup
        mock_cap.release.assert_called_once()
        self.assertIsNone(self.recorder.cap)
    
    def test_close_camera_none_safe(self):
        """Test closing camera when cap is None."""
        self.recorder.cap = None
        
        # Should not raise exception
        self.recorder._close_camera()
        
        self.assertIsNone(self.recorder.cap)
    
    @patch('cv2.VideoCapture')
    def test_recording_loop_cleanup_on_exception(self, mock_capture):
        """Test that resources are cleaned up even when exception occurs."""
        # Mock camera
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.side_effect = Exception("Test error")
        mock_capture.return_value = mock_cap
        
        # Mock encoder
        mock_process = Mock()
        mock_process.stdin = Mock()
        self.recorder.writer = mock_process
        
        # Set running flag
        self.recorder.running = True
        
        # Run recording loop (will fail immediately)
        with patch.object(self.recorder, '_start_new_segment'):
            with patch.object(self.recorder, '_close_encoder') as mock_close_enc:
                with patch.object(self.recorder, '_close_camera') as mock_close_cam:
                    # This will raise exception but should still clean up
                    try:
                        self.recorder._recording_loop()
                    except:
                        pass
                    
                    # Verify cleanup methods were called
                    # (may be called multiple times due to loop)
                    self.assertTrue(mock_close_enc.called or mock_close_cam.called)
    
    def test_stop_cleans_resources(self):
        """Test that stop() properly cleans up resources."""
        # Mock running recorder
        self.recorder.running = True
        self.recorder.thread = Mock()
        self.recorder.thread.join = Mock()
        
        mock_cap = Mock()
        mock_process = Mock()
        mock_process.stdin = Mock()
        
        self.recorder.cap = mock_cap
        self.recorder.writer = mock_process
        
        # Stop recorder
        self.recorder.stop()
        
        # Verify cleanup
        self.assertFalse(self.recorder.running)
        self.recorder.thread.join.assert_called_once()


class TestVideoRecorderConfiguration(unittest.TestCase):
    """Test video recorder configuration."""
    
    def test_initialization(self):
        """Test proper initialization."""
        recorder = VideoRecorder(
            output_dir='/test/videos',
            width=1280,
            height=720,
            fps=25,
            segment_duration=600
        )
        
        self.assertEqual(recorder.output_dir, '/test/videos')
        self.assertEqual(recorder.width, 1280)
        self.assertEqual(recorder.height, 720)
        self.assertEqual(recorder.fps, 25)
        self.assertEqual(recorder.segment_duration, 600)
        self.assertFalse(recorder.running)
    
    def test_ffmpeg_command_generation(self):
        """Test FFmpeg command generation."""
        recorder = VideoRecorder()
        
        command = recorder._get_ffmpeg_command('/tmp/output.mp4')
        
        # Verify essential FFmpeg parameters
        self.assertIn('ffmpeg', command)
        self.assertIn('-f', command)
        self.assertIn('rawvideo', command)
        self.assertIn('-c:v', command)
        
        # Check for NVENC encoder
        self.assertTrue(
            'h264_nvenc' in command or 'h265_nvenc' in command
        )


if __name__ == '__main__':
    unittest.main()
