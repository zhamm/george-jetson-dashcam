"""
Utility functions for George Jetson Dashcam
"""
import os
import cv2
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def setup_logging(log_file: str = "/var/www/html/george-jetson/logs/dashcam.log",
                 max_bytes: int = 10 * 1024 * 1024,  # 10 MB
                 backup_count: int = 5):
    """
    Configure logging for the application with rotation.
    
    Args:
        log_file: Path to log file
        max_bytes: Maximum size of log file before rotation (default 10MB)
        backup_count: Number of backup files to keep (default 5)
    """
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Create rotating file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def overlay_text_on_frame(frame: cv2.Mat, text_lines: list, position: Tuple[int, int] = (10, 30),
                         font_scale: float = 0.7, thickness: int = 2, color: Tuple[int, int, int] = (0, 255, 0)) -> cv2.Mat:
    """
    Overlay multiple lines of text on video frame.
    
    Args:
        frame: OpenCV frame
        text_lines: List of text strings to overlay
        position: (x, y) starting position
        font_scale: Font size multiplier
        thickness: Text line thickness
        color: BGR color tuple
    
    Returns:
        Frame with overlaid text
    """
    font = cv2.FONT_HERSHEY_SIMPLEX
    x, y = position
    line_height = int(30 * font_scale)
    
    for i, text in enumerate(text_lines):
        cv2.putText(frame, text, (x, y + i * line_height), font, font_scale, color, thickness)
    
    return frame


def get_formatted_timestamp() -> str:
    """Get current timestamp in YYYYMMDD-HHMMSS format."""
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def get_formatted_datetime() -> str:
    """Get current datetime in human-readable format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_video_filename(video_dir: str = "/videos") -> str:
    """Generate video filename with timestamp."""
    timestamp = get_formatted_timestamp()
    return f"jetsoncam-{timestamp}.mp4"


def ensure_directory_exists(path: str):
    """Ensure directory exists, create if needed."""
    os.makedirs(path, exist_ok=True)


def get_disk_usage(path: str = "/videos") -> dict:
    """
    Get disk usage statistics for a given path.
    
    Returns:
        Dict with 'total', 'used', 'free' (in bytes) and 'percent' (usage percentage)
    """
    import shutil
    stat = shutil.disk_usage(path)
    total = stat.total
    used = stat.used
    free = stat.free
    percent = (used / total * 100) if total > 0 else 0
    
    return {
        'total': total,
        'used': used,
        'free': free,
        'percent': percent,
        'free_percent': 100 - percent
    }


def format_bytes(bytes_val: int) -> str:
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} PB"


def parse_gps_coordinate(coord_str: str, direction: str) -> Optional[float]:
    """
    Parse NMEA GPS coordinate string.
    
    Args:
        coord_str: Coordinate in DDMM.MMMM format
        direction: N/S or E/W
    
    Returns:
        Decimal degree coordinate or None
    """
    try:
        if not coord_str or not direction:
            return None
        
        if len(coord_str) < 5:
            return None
        
        # Format: DDMM.MMMM
        if '.' in coord_str:
            dot_index = coord_str.index('.')
            degrees = int(coord_str[:dot_index - 2])
            minutes = float(coord_str[dot_index - 2:])
        else:
            degrees = int(coord_str[:-7])
            minutes = float(coord_str[-7:])
        
        decimal = degrees + (minutes / 60.0)
        
        if direction in ['S', 'W']:
            decimal = -decimal
        
        return decimal
    except (ValueError, IndexError):
        return None


def smooth_gps_coordinates(coords_buffer: list, buffer_size: int = 5) -> Optional[Tuple[float, float]]:
    """
    Smooth GPS coordinates using moving average.
    
    Args:
        coords_buffer: List of (lat, lon) tuples
        buffer_size: Size of buffer for averaging
    
    Returns:
        Smoothed (lat, lon) or None if insufficient data
    """
    if len(coords_buffer) < buffer_size:
        return None
    
    recent = coords_buffer[-buffer_size:]
    avg_lat = sum(c[0] for c in recent) / len(recent)
    avg_lon = sum(c[1] for c in recent) / len(recent)
    
    return (avg_lat, avg_lon)


class ConfigManager:
    """Manage application configuration."""
    
    def __init__(self, config_dict: dict = None):
        self.config = config_dict or {}
    
    def get(self, key: str, default=None):
        """Get config value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        """Set config value."""
        self.config[key] = value


# Default configuration
DEFAULT_CONFIG = {
    'VIDEO_DIR': '/videos',
    'DB_PATH': '/var/www/html/george-jetson/db/db.sqlite3',
    'SEGMENT_DURATION': 300,  # 5 minutes in seconds
    'VIDEO_WIDTH': 1920,
    'VIDEO_HEIGHT': 1080,
    'VIDEO_FPS': 30,
    'GPS_PORT': '/dev/ttyUSB0',
    'GPS_BAUDRATE': 4800,
    'MIN_FREE_DISK_PERCENT': 10,
    'RETENTION_DAYS': 30,
    'WEB_PORT': 8089,
    'WEB_HOST': '0.0.0.0',
    'ADMIN_USER': 'admin',
    'ADMIN_PASS': 'admin',
    'AI_CONFIDENCE_THRESHOLD': 0.5,
    'AI_INFERENCE_FPS': 5,
    'OVERLAY_POSITION': (10, 30),
    'OVERLAY_FONT_SCALE': 0.7,
    'OVERLAY_THICKNESS': 2,
    'OVERLAY_COLOR': (0, 255, 0),  # BGR green
}
