"""
GPS Reader Module - Reads NMEA GPS data from USB dongle
"""
import serial
import threading
import time
import logging
from datetime import datetime
from typing import Optional, Tuple, Callable
from collections import deque

logger = logging.getLogger(__name__)


class GPSReader:
    """Read live NMEA GPS data from USB GPS dongle."""
    
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 4800, 
                 buffer_size: int = 10):
        """
        Initialize GPS reader.
        
        Args:
            port: Serial port (e.g., /dev/ttyUSB0)
            baudrate: Serial baud rate (default 4800 for NMEA)
            buffer_size: Size of coordinate buffer for smoothing
        """
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.running = False
        self.thread = None
        
        # Current GPS data
        self.latitude = None
        self.longitude = None
        self.timestamp = None
        self.altitude = None
        self.speed = None
        self.satellites = None
        self.fix_quality = None
        
        # Coordinate history for smoothing
        self.coord_buffer = deque(maxlen=buffer_size)
        self.smoothed_lat = None
        self.smoothed_lon = None
        
        # Callback for new GPS data
        self.on_new_data_callback: Optional[Callable] = None
        
        # Lock for thread-safe access
        self.lock = threading.Lock()
    
    def connect(self) -> bool:
        """Attempt to connect to GPS dongle."""
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
            logger.info(f"Connected to GPS on {self.port} at {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            logger.error(f"Failed to connect to GPS: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from GPS dongle."""
        if self.serial:
            self.serial.close()
            logger.info("GPS disconnected")
    
    def start(self):
        """Start GPS reading in background thread."""
        if not self.running:
            if not self.connect():
                logger.error("Cannot start GPS reader - failed to connect")
                return False
            
            self.running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            logger.info("GPS reader started")
            return True
        return False
    
    def stop(self):
        """Stop GPS reading."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        self.disconnect()
        logger.info("GPS reader stopped")
    
    def _read_loop(self):
        """Main GPS reading loop (runs in background thread)."""
        while self.running:
            try:
                if self.serial and self.serial.in_waiting > 0:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self._parse_nmea_sentence(line)
                        if self.on_new_data_callback:
                            self.on_new_data_callback(self.get_current_data())
            except Exception as e:
                logger.error(f"Error reading GPS: {e}")
                time.sleep(0.1)
    
    def _parse_nmea_sentence(self, sentence: str):
        """Parse NMEA GPS sentence."""
        try:
            if not sentence.startswith('$'):
                return
            
            # Extract checksum if present
            if '*' in sentence:
                sentence = sentence[:sentence.index('*')]
            
            parts = sentence.split(',')
            sentence_type = parts[0][1:]  # Remove $
            
            if sentence_type == 'GPGGA':
                self._parse_gga(parts)
            elif sentence_type == 'GPRMC':
                self._parse_rmc(parts)
        except Exception as e:
            logger.debug(f"Error parsing NMEA sentence: {e}")
    
    def _parse_gga(self, parts: list):
        """
        Parse GGA sentence (Global Positioning System Fix Data).
        Format: $GPGGA,hhmmss.ss,llll.ll,a,yyyyy.yy,a,x,xx,x.x,x.x,M,x.x,M,x.x,xxxx
        """
        try:
            if len(parts) < 9:
                return
            
            # Time: hhmmss.ss
            time_str = parts[1]
            
            # Latitude: llll.ll
            lat_str = parts[2]
            lat_dir = parts[3]
            
            # Longitude: yyyyy.yy
            lon_str = parts[4]
            lon_dir = parts[5]
            
            # Fix quality: 0=invalid, 1=GPS, 2=DGPS
            fix_quality = int(parts[6]) if parts[6] else 0
            
            # Number of satellites
            satellites = int(parts[7]) if parts[7] else 0
            
            # Altitude
            altitude_str = parts[9]
            
            # Parse coordinates
            lat = self._parse_coordinate(lat_str, lat_dir)
            lon = self._parse_coordinate(lon_str, lon_dir)
            
            with self.lock:
                self.fix_quality = fix_quality
                self.satellites = satellites
                
                if lat is not None and lon is not None and fix_quality >= 1:
                    self.latitude = lat
                    self.longitude = lon
                    
                    # Add to buffer for smoothing
                    self.coord_buffer.append((lat, lon))
                    self._smooth_coordinates()
                
                if altitude_str:
                    try:
                        self.altitude = float(altitude_str)
                    except ValueError:
                        pass
                
                if time_str:
                    self.timestamp = datetime.now().strftime("%Y-%m-%d") + " " + time_str[:8]
        
        except Exception as e:
            logger.debug(f"Error parsing GGA: {e}")
    
    def _parse_rmc(self, parts: list):
        """
        Parse RMC sentence (Recommended Minimum Navigation Information).
        Format: $GPRMC,hhmmss.ss,A,llll.ll,a,yyyyy.yy,a,x.x,x.x,ddmmyy,,,a
        """
        try:
            if len(parts) < 9:
                return
            
            # Status: A=active, V=void
            status = parts[2]
            
            # Speed in knots
            speed_str = parts[7]
            
            with self.lock:
                if speed_str:
                    try:
                        self.speed = float(speed_str)
                    except ValueError:
                        pass
        
        except Exception as e:
            logger.debug(f"Error parsing RMC: {e}")
    
    def _parse_coordinate(self, coord_str: str, direction: str) -> Optional[float]:
        """
        Parse NMEA coordinate string (DDMM.MMMM format).
        
        Args:
            coord_str: Coordinate string in DDMM.MMMM format
            direction: N/S for latitude, E/W for longitude
        
        Returns:
            Decimal degree coordinate or None
        """
        try:
            if not coord_str or not direction:
                return None
            
            if '.' not in coord_str:
                return None
            
            dot_index = coord_str.index('.')
            degrees = int(coord_str[:dot_index - 2])
            minutes = float(coord_str[dot_index - 2:])
            
            decimal = degrees + (minutes / 60.0)
            
            if direction in ['S', 'W']:
                decimal = -decimal
            
            return decimal
        except (ValueError, IndexError):
            return None
    
    def _smooth_coordinates(self):
        """Smooth coordinates using moving average."""
        if len(self.coord_buffer) >= 5:
            avg_lat = sum(c[0] for c in self.coord_buffer) / len(self.coord_buffer)
            avg_lon = sum(c[1] for c in self.coord_buffer) / len(self.coord_buffer)
            self.smoothed_lat = avg_lat
            self.smoothed_lon = avg_lon
    
    def get_current_data(self) -> dict:
        """Get current GPS data as dictionary."""
        with self.lock:
            return {
                'latitude': self.latitude,
                'longitude': self.longitude,
                'smoothed_latitude': self.smoothed_lat,
                'smoothed_longitude': self.smoothed_lon,
                'timestamp': self.timestamp,
                'altitude': self.altitude,
                'speed': self.speed,
                'satellites': self.satellites,
                'fix_quality': self.fix_quality,
                'has_fix': self.fix_quality is not None and self.fix_quality >= 1
            }
    
    def get_position(self) -> Tuple[Optional[float], Optional[float]]:
        """Get current (lat, lon) position."""
        with self.lock:
            if self.smoothed_lat is not None and self.smoothed_lon is not None:
                return (self.smoothed_lat, self.smoothed_lon)
            elif self.latitude is not None and self.longitude is not None:
                return (self.latitude, self.longitude)
            return (None, None)
    
    def set_on_new_data_callback(self, callback: Callable):
        """Set callback function to be called when new GPS data arrives."""
        self.on_new_data_callback = callback
    
    def wait_for_fix(self, timeout: int = 30) -> bool:
        """Wait for GPS fix to be acquired."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            data = self.get_current_data()
            if data['has_fix'] and data['satellites'] is not None and data['satellites'] >= 4:
                logger.info(f"GPS fix acquired with {data['satellites']} satellites")
                return True
            time.sleep(0.5)
        
        logger.warning(f"No GPS fix after {timeout} seconds")
        return False


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    gps = GPSReader(port='/dev/ttyUSB0', baudrate=4800)
    gps.set_on_new_data_callback(lambda data: print(f"GPS: {data['latitude']}, {data['longitude']}"))
    
    if gps.start():
        gps.wait_for_fix()
        
        for i in range(30):
            data = gps.get_current_data()
            print(f"[{i}] Lat: {data['latitude']:.6f}, Lon: {data['longitude']:.6f}, Sats: {data['satellites']}")
            time.sleep(1)
        
        gps.stop()
