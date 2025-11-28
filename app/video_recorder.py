"""
Video Recorder Module - Captures video with GPU acceleration and metadata overlay
"""
import cv2
import subprocess
import threading
import time
import logging
from datetime import datetime
from typing import Optional, Callable, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class VideoRecorder:
    """Record video with GPU acceleration and real-time overlay."""
    
    def __init__(self, output_dir: str = '/videos', 
                 width: int = 1920, height: int = 1080, fps: int = 30,
                 segment_duration: int = 300):
        """
        Initialize video recorder.
        
        Args:
            output_dir: Directory to save video files
            width: Video width
            height: Video height
            fps: Frames per second
            segment_duration: Duration of each segment in seconds (5 min = 300s)
        """
        self.output_dir = output_dir
        self.width = width
        self.height = height
        self.fps = fps
        self.segment_duration = segment_duration
        
        self.running = False
        self.thread = None
        self.writer = None
        self.cap = None
        
        # Current segment info
        self.current_segment_start = None
        self.current_filename = None
        
        # Callback for new frames (for overlay data)
        self.on_frame_callback: Optional[Callable] = None
        
        # Frame counter
        self.frame_count = 0
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    def _get_camera_source(self) -> Optional[cv2.VideoCapture]:
        """
        Get camera source. Tries CSI first, then USB cameras.
        
        Returns:
            VideoCapture object or None
        """
        # Try CSI camera (index 0)
        for cam_index in [0, 1, 2, 3]:
            try:
                cap = cv2.VideoCapture(cam_index)
                if cap.isOpened():
                    # Set resolution and FPS
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    cap.set(cv2.CAP_PROP_FPS, self.fps)
                    logger.info(f"Opened camera at index {cam_index}")
                    return cap
            except Exception as e:
                logger.debug(f"Camera {cam_index} not available: {e}")
        
        return None
    
    def _get_ffmpeg_command(self, output_file: str) -> list:
        """
        Generate FFmpeg command for GPU-accelerated H.264 encoding on Jetson.
        
        Uses NVENC (NVIDIA video encoder) for hardware acceleration.
        Fallback to software encoding if GPU unavailable.
        
        Args:
            output_file: Output video file path
        
        Returns:
            FFmpeg command as list
        """
        # Try to use NVIDIA NVENC encoder (Jetson GPU acceleration)
        # Format: ffmpeg -f rawvideo -pixel_format bgr24 -video_size WIDTHxHEIGHT -framerate FPS 
        #         -i - -c:v h264_nvenc -preset default -rc:v vbr output.mp4
        
        command = [
            'ffmpeg',
            '-f', 'rawvideo',
            '-pixel_format', 'bgr24',
            '-video_size', f'{self.width}x{self.height}',
            '-framerate', str(self.fps),
            '-i', '-',  # Read from stdin
            '-c:v', 'h264_nvenc',  # NVIDIA GPU encoder
            '-preset', 'default',  # fast, default, slow
            '-rc:v', 'vbr',  # Variable bitrate
            '-b:v', '5000k',  # Target bitrate
            '-y',  # Overwrite output file
            output_file
        ]
        
        return command
    
    def _get_ffmpeg_command_fallback(self, output_file: str) -> list:
        """Fallback FFmpeg command using software encoding."""
        command = [
            'ffmpeg',
            '-f', 'rawvideo',
            '-pixel_format', 'bgr24',
            '-video_size', f'{self.width}x{self.height}',
            '-framerate', str(self.fps),
            '-i', '-',
            '-c:v', 'libx264',  # Software encoder
            '-preset', 'fast',
            '-crf', '23',  # Quality (lower = better)
            '-y',
            output_file
        ]
        
        return command
    
    def _start_ffmpeg_encoder(self, output_file: str) -> Optional[subprocess.Popen]:
        """
        Start FFmpeg encoding process.
        
        Args:
            output_file: Output file path
        
        Returns:
            Popen object or None if failed
        """
        try:
            # Try GPU encoder first
            cmd = self._get_ffmpeg_command(output_file)
            logger.info(f"Starting FFmpeg with GPU encoder: {' '.join(cmd[:5])}...")
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8
            )
            
            return process
        except Exception as e:
            logger.warning(f"Failed to start GPU encoder: {e}, trying software encoder")
            
            try:
                cmd = self._get_ffmpeg_command_fallback(output_file)
                logger.info(f"Starting FFmpeg with software encoder")
                
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=10**8
                )
                
                return process
            except Exception as e:
                logger.error(f"Failed to start FFmpeg: {e}")
                return None
    
    def _generate_filename(self) -> str:
        """Generate video filename with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"jetsoncam-{timestamp}.mp4"
    
    def start(self) -> bool:
        """Start video recording in background thread."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._recording_loop, daemon=True)
            self.thread.start()
            logger.info("Video recorder started")
            return True
        return False
    
    def stop(self):
        """Stop video recording."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        self._close_encoder()
        self._close_camera()
        logger.info("Video recorder stopped")
    
    def _close_camera(self):
        """Close camera capture."""
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def _close_encoder(self):
        """Close FFmpeg encoder process."""
        if self.writer:
            try:
                self.writer.stdin.close()
                self.writer.wait(timeout=5)
            except Exception as e:
                logger.error(f"Error closing encoder: {e}")
                self.writer.kill()
            
            self.writer = None
    
    def _start_new_segment(self):
        """Start a new video segment."""
        self._close_encoder()
        
        self.current_filename = self._generate_filename()
        output_path = f"{self.output_dir}/{self.current_filename}"
        self.current_segment_start = time.time()
        self.frame_count = 0
        
        self.writer = self._start_ffmpeg_encoder(output_path)
        logger.info(f"Started new segment: {self.current_filename}")
    
    def _recording_loop(self):
        """Main recording loop (runs in background thread)."""
        self.cap = self._get_camera_source()
        
        if not self.cap:
            logger.error("Failed to open camera")
            self.running = False
            return
        
        self._start_new_segment()
        
        while self.running:
            try:
                ret, frame = self.cap.read()
                
                if not ret:
                    logger.warning("Failed to read frame from camera")
                    time.sleep(0.1)
                    continue
                
                # Resize if needed
                if frame.shape[1] != self.width or frame.shape[0] != self.height:
                    frame = cv2.resize(frame, (self.width, self.height))
                
                # Apply overlay data via callback
                if self.on_frame_callback:
                    overlay_data = self.on_frame_callback()
                    if overlay_data:
                        frame = self._apply_overlay(frame, overlay_data)
                
                # Write frame to FFmpeg encoder
                if self.writer and self.writer.stdin:
                    try:
                        self.writer.stdin.write(frame.tobytes())
                    except Exception as e:
                        logger.error(f"Error writing frame to encoder: {e}")
                        self._start_new_segment()
                
                self.frame_count += 1
                
                # Check if segment duration exceeded
                if time.time() - self.current_segment_start >= self.segment_duration:
                    logger.info(f"Segment duration reached, starting new segment")
                    self._start_new_segment()
            
            except Exception as e:
                logger.error(f"Error in recording loop: {e}")
                time.sleep(0.1)
    
    def _apply_overlay(self, frame: cv2.Mat, overlay_data: dict) -> cv2.Mat:
        """
        Apply overlay text to frame.
        
        Args:
            frame: Video frame
            overlay_data: Dict with 'timestamp', 'gps_lat', 'gps_lon', etc.
        
        Returns:
            Frame with overlay applied
        """
        try:
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            thickness = 2
            color = (0, 255, 0)  # BGR green
            x, y = 10, 30
            line_height = 30
            
            # Build text lines
            text_lines = []
            
            if 'timestamp' in overlay_data:
                text_lines.append(f"Time: {overlay_data['timestamp']}")
            
            if 'gps_lat' in overlay_data and 'gps_lon' in overlay_data:
                lat = overlay_data['gps_lat']
                lon = overlay_data['gps_lon']
                if lat is not None and lon is not None:
                    text_lines.append(f"GPS: {lat:.6f}, {lon:.6f}")
                else:
                    text_lines.append("GPS: No Fix")
            
            if 'vehicle_detections' in overlay_data:
                detections = overlay_data['vehicle_detections']
                if detections:
                    for i, det in enumerate(detections[:3]):  # Show top 3
                        text = f"Vehicle: {det.get('description', 'Unknown')}"
                        if det.get('license_plate'):
                            text += f" [{det['license_plate']}]"
                        text_lines.append(text)
            
            # Render text
            for i, text in enumerate(text_lines):
                cv2.putText(frame, text, (x, y + i * line_height), 
                           font, font_scale, color, thickness)
            
            return frame
        except Exception as e:
            logger.debug(f"Error applying overlay: {e}")
            return frame
    
    def set_on_frame_callback(self, callback: Callable):
        """
        Set callback to provide overlay data for each frame.
        
        Callback should return dict with optional keys:
        - timestamp: str
        - gps_lat: float
        - gps_lon: float
        - vehicle_detections: list of dicts
        """
        self.on_frame_callback = callback
    
    def get_current_segment(self) -> Optional[str]:
        """Get current segment filename."""
        with self.lock:
            return self.current_filename
    
    def get_frame_count(self) -> int:
        """Get frames recorded in current segment."""
        with self.lock:
            return self.frame_count


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    recorder = VideoRecorder(output_dir='/videos', width=1920, height=1080, fps=30, segment_duration=60)
    
    # Set overlay callback
    def get_overlay():
        return {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'gps_lat': 40.7128,
            'gps_lon': -74.0060,
            'vehicle_detections': [
                {'license_plate': 'ABC123', 'description': 'Red Honda Civic'}
            ]
        }
    
    recorder.set_on_frame_callback(get_overlay)
    
    if recorder.start():
        time.sleep(120)  # Record for 2 minutes
        recorder.stop()
        print(f"Recording stopped. Frames: {recorder.get_frame_count()}")
