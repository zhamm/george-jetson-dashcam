"""
George Jetson Dashcam - Main Application
Integrated dashcam system with GPU-accelerated AI detection
"""
import sys
import os
import logging
import argparse
import signal
import time
from datetime import datetime

# Add app directory to path
sys.path.insert(0, '/var/www/html/george-jetson/app')

from utils import setup_logging, DEFAULT_CONFIG, ConfigManager
from database import DatabaseManager
from gps_reader import GPSReader
from video_recorder import VideoRecorder
from ai_detector import AIDetector
from cleanup import DiskCleanupManager
from web_server import DashcamWebServer

logger = logging.getLogger(__name__)


class GeorgJetsonDashcam:
    """Main dashcam application controller."""
    
    def __init__(self, config: dict = None):
        """
        Initialize dashcam application.
        
        Args:
            config: Configuration dictionary (uses defaults if not provided)
        """
        self.config = ConfigManager(config or DEFAULT_CONFIG)
        
        # Setup logging
        setup_logging()
        logger.info("=" * 60)
        logger.info("George Jetson Dashcam Application Starting")
        logger.info(f"Start time: {datetime.now()}")
        logger.info("=" * 60)
        
        # Initialize components
        self.db = None
        self.gps = None
        self.recorder = None
        self.ai_detector = None
        self.cleanup = None
        self.web_server = None
        
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, sig, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {sig}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def initialize(self) -> bool:
        """Initialize all components."""
        try:
            logger.info("Initializing components...")
            
            # Database
            logger.info("Initializing database...")
            self.db = DatabaseManager(self.config.get('DB_PATH'))
            
            # GPS Reader
            logger.info("Initializing GPS reader...")
            self.gps = GPSReader(
                port=self.config.get('GPS_PORT'),
                baudrate=self.config.get('GPS_BAUDRATE')
            )
            self.gps.set_on_new_data_callback(self._on_gps_data)
            
            # Video Recorder
            logger.info("Initializing video recorder...")
            self.recorder = VideoRecorder(
                output_dir=self.config.get('VIDEO_DIR'),
                width=self.config.get('VIDEO_WIDTH'),
                height=self.config.get('VIDEO_HEIGHT'),
                fps=self.config.get('VIDEO_FPS'),
                segment_duration=self.config.get('SEGMENT_DURATION')
            )
            self.recorder.set_on_frame_callback(self._get_overlay_data)
            
            # AI Detector
            logger.info("Initializing AI detector...")
            self.ai_detector = AIDetector(
                inference_fps=self.config.get('AI_INFERENCE_FPS'),
                confidence_threshold=self.config.get('AI_CONFIDENCE_THRESHOLD')
            )
            self.ai_detector.set_detections_callback(self._on_ai_detection)
            
            # Disk Cleanup Manager
            logger.info("Initializing disk cleanup manager...")
            self.cleanup = DiskCleanupManager(
                video_dir=self.config.get('VIDEO_DIR'),
                db_path=self.config.get('DB_PATH'),
                min_free_percent=self.config.get('MIN_FREE_DISK_PERCENT'),
                retention_days=self.config.get('RETENTION_DAYS'),
                check_interval=300
            )
            
            # Web Server
            logger.info("Initializing web server...")
            self.web_server = DashcamWebServer(
                database_manager=self.db,
                cleanup_manager=self.cleanup,
                video_dir=self.config.get('VIDEO_DIR'),
                host=self.config.get('WEB_HOST'),
                port=self.config.get('WEB_PORT'),
                admin_user=self.config.get('ADMIN_USER'),
                admin_pass=self.config.get('ADMIN_PASS')
            )
            
            logger.info("All components initialized successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error during initialization: {e}", exc_info=True)
            return False
    
    def start(self) -> bool:
        """Start all components."""
        if self.running:
            logger.warning("Application already running")
            return False
        
        try:
            logger.info("Starting components...")
            
            # Start GPS
            if not self.gps.start():
                logger.warning("Failed to start GPS reader")
            
            # Wait for GPS fix (optional, with timeout)
            logger.info("Waiting for GPS fix (timeout: 30s)...")
            if not self.gps.wait_for_fix(timeout=30):
                logger.warning("No GPS fix acquired, continuing anyway")
            
            # Start video recorder
            if not self.recorder.start():
                logger.error("Failed to start video recorder")
                return False
            
            # Start AI detector
            if not self.ai_detector.start():
                logger.warning("Failed to start AI detector")
            
            # Start disk cleanup manager
            if not self.cleanup.start():
                logger.warning("Failed to start disk cleanup manager")
            
            self.running = True
            logger.info("=" * 60)
            logger.info("Application started successfully")
            logger.info(f"Web dashboard: http://{self.config.get('WEB_HOST')}:{self.config.get('WEB_PORT')}")
            logger.info(f"Username: {self.config.get('ADMIN_USER')} / Password: {self.config.get('ADMIN_PASS')}")
            logger.info("=" * 60)
            
            return True
        
        except Exception as e:
            logger.error(f"Error starting application: {e}", exc_info=True)
            return False
    
    def stop(self):
        """Stop all components."""
        logger.info("Stopping components...")
        
        if self.ai_detector:
            self.ai_detector.stop()
        
        if self.recorder:
            self.recorder.stop()
        
        if self.gps:
            self.gps.stop()
        
        if self.cleanup:
            self.cleanup.stop()
        
        self.running = False
        logger.info("=" * 60)
        logger.info("Application stopped")
        logger.info(f"Stop time: {datetime.now()}")
        logger.info("=" * 60)
    
    def _on_gps_data(self, data: dict):
        """Called when new GPS data arrives."""
        if data['has_fix']:
            logger.debug(f"GPS: Lat={data['latitude']:.6f}, Lon={data['longitude']:.6f}, Sats={data['satellites']}")
    
    def _get_overlay_data(self) -> dict:
        """Get overlay data for current frame."""
        overlay = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Add GPS data
        gps_data = self.gps.get_current_data()
        overlay['gps_lat'] = gps_data.get('smoothed_latitude') or gps_data.get('latitude')
        overlay['gps_lon'] = gps_data.get('smoothed_longitude') or gps_data.get('longitude')
        
        # Add latest AI detections
        detections = self.ai_detector.get_latest_detections()
        if detections:
            overlay['vehicle_detections'] = [
                {
                    'license_plate': d.license_plate,
                    'description': f"{d.color} {d.make} {d.model}" if d.color and d.make else "Unknown",
                    'confidence': d.confidence
                }
                for d in detections
            ]
        
        return overlay
    
    def _on_ai_detection(self, detections):
        """Called when AI detection finds vehicles."""
        current_segment = self.recorder.get_current_segment()
        gps_data = self.gps.get_current_data()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for detection in detections:
            car_desc = f"{detection.color} {detection.make} {detection.model}" if detection.make else "Unknown"
            
            # Log to database
            self.db.log_vehicle_event(
                timestamp=timestamp,
                video_filename=current_segment,
                lat=gps_data.get('latitude'),
                lon=gps_data.get('longitude'),
                license_plate=detection.license_plate,
                car_description=car_desc,
                confidence=detection.confidence
            )
            
            logger.info(f"Detection: {car_desc} [{detection.license_plate}] at {timestamp}")
    
    def run_web_server(self, debug: bool = False):
        """Run web server (blocking)."""
        if not self.web_server:
            logger.error("Web server not initialized")
            return
        
        self.web_server.run(debug=debug)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='George Jetson Dashcam')
    parser.add_argument('--web-only', action='store_true', help='Run web server only')
    parser.add_argument('--no-web', action='store_true', help='Run without web server')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--gps-port', default='/dev/ttyUSB0', help='GPS device port')
    parser.add_argument('--video-dir', default='/videos', help='Video output directory')
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create config
    config = DEFAULT_CONFIG.copy()
    if args.gps_port:
        config['GPS_PORT'] = args.gps_port
    if args.video_dir:
        config['VIDEO_DIR'] = args.video_dir
    
    # Initialize application
    app = GeorgJetsonDashcam(config=config)
    
    if not app.initialize():
        logger.error("Failed to initialize application")
        sys.exit(1)
    
    if args.web_only:
        # Web server only (for testing without camera)
        logger.info("Running web server only (no video recording)")
        app.run_web_server(debug=args.debug)
    else:
        # Start recording
        if not app.start():
            logger.error("Failed to start application")
            sys.exit(1)
        
        if args.no_web:
            # Run without web server
            logger.info("Application running (no web server). Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                app.stop()
        else:
            # Start web server (blocking)
            app.run_web_server(debug=args.debug)


if __name__ == '__main__':
    main()
