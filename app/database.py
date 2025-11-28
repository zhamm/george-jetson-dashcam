"""
Database Module - SQLite3 logging for vehicle detection events
"""
import sqlite3
import threading
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manage SQLite database for vehicle detection logging."""
    
    def __init__(self, db_path: str = '/var/www/html/george-jetson/db/db.sqlite3'):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Create database and tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create vehicle detection events table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS vehicle_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        video_filename TEXT NOT NULL,
                        lat REAL,
                        lon REAL,
                        license_plate TEXT,
                        car_description TEXT,
                        confidence REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(timestamp, video_filename, license_plate)
                    )
                ''')
                
                # Create indices for faster querying
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON vehicle_events(timestamp)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_license_plate 
                    ON vehicle_events(license_plate)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_video_filename 
                    ON vehicle_events(video_filename)
                ''')
                
                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def log_vehicle_event(self, timestamp: str, video_filename: str, 
                         lat: Optional[float], lon: Optional[float],
                         license_plate: Optional[str], car_description: Optional[str],
                         confidence: float = 0.0) -> bool:
        """
        Log a vehicle detection event.
        
        Args:
            timestamp: Event timestamp (YYYY-MM-DD HH:MM:SS)
            video_filename: Associated video file
            lat: Latitude coordinate
            lon: Longitude coordinate
            license_plate: Detected license plate
            car_description: Vehicle description (color, make, model)
            confidence: Detection confidence score (0-1)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO vehicle_events 
                        (timestamp, video_filename, lat, lon, license_plate, car_description, confidence)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (timestamp, video_filename, lat, lon, license_plate, car_description, confidence))
                    conn.commit()
            return True
        except sqlite3.IntegrityError:
            logger.debug(f"Duplicate entry: {video_filename} {license_plate} at {timestamp}")
            return False
        except Exception as e:
            logger.error(f"Error logging vehicle event: {e}")
            return False
    
    def search_events(self, start_date: Optional[str] = None, 
                     end_date: Optional[str] = None,
                     license_plate: Optional[str] = None,
                     color: Optional[str] = None,
                     make: Optional[str] = None,
                     model: Optional[str] = None,
                     limit: int = 100) -> List[Dict]:
        """
        Search vehicle events with filters.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            license_plate: Partial license plate match
            color: Partial color match
            make: Partial make match
            model: Partial model match
            limit: Maximum results
        
        Returns:
            List of event records
        """
        try:
            query = 'SELECT * FROM vehicle_events WHERE 1=1'
            params = []
            
            if start_date:
                query += ' AND timestamp >= ?'
                params.append(f"{start_date} 00:00:00")
            
            if end_date:
                query += ' AND timestamp <= ?'
                params.append(f"{end_date} 23:59:59")
            
            if license_plate:
                query += ' AND license_plate LIKE ?'
                params.append(f"%{license_plate}%")
            
            if color or make or model:
                # Build description filter
                desc_conditions = []
                if color:
                    desc_conditions.append('car_description LIKE ?')
                    params.append(f"%{color}%")
                if make:
                    desc_conditions.append('car_description LIKE ?')
                    params.append(f"%{make}%")
                if model:
                    desc_conditions.append('car_description LIKE ?')
                    params.append(f"%{model}%")
                
                if desc_conditions:
                    query += ' AND (' + ' OR '.join(desc_conditions) + ')'
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error searching events: {e}")
            return []
    
    def get_events_by_date(self, date: str, limit: int = 100) -> List[Dict]:
        """Get all events for a specific date."""
        return self.search_events(start_date=date, end_date=date, limit=limit)
    
    def get_events_by_license_plate(self, plate: str, limit: int = 100) -> List[Dict]:
        """Get all events for a specific license plate."""
        return self.search_events(license_plate=plate, limit=limit)
    
    def get_events_by_video(self, video_filename: str) -> List[Dict]:
        """Get all events associated with a video file."""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT * FROM vehicle_events WHERE video_filename = ? ORDER BY timestamp',
                        (video_filename,)
                    )
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting events by video: {e}")
            return []
    
    def delete_old_events(self, days: int = 30) -> int:
        """
        Delete events older than specified days.
        
        Args:
            days: Delete events older than this many days
        
        Returns:
            Number of deleted events
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        'DELETE FROM vehicle_events WHERE timestamp < ?',
                        (f"{cutoff_date} 00:00:00",)
                    )
                    conn.commit()
                    deleted = cursor.rowcount
                    
            logger.info(f"Deleted {deleted} events older than {cutoff_date}")
            return deleted
        except Exception as e:
            logger.error(f"Error deleting old events: {e}")
            return 0
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Total events
                    cursor.execute('SELECT COUNT(*) FROM vehicle_events')
                    total = cursor.fetchone()[0]
                    
                    # Unique license plates
                    cursor.execute('SELECT COUNT(DISTINCT license_plate) FROM vehicle_events WHERE license_plate IS NOT NULL')
                    unique_plates = cursor.fetchone()[0]
                    
                    # Events today
                    today = datetime.now().strftime("%Y-%m-%d")
                    cursor.execute(
                        'SELECT COUNT(*) FROM vehicle_events WHERE timestamp >= ?',
                        (f"{today} 00:00:00",)
                    )
                    today_count = cursor.fetchone()[0]
                    
                    # Latest event
                    cursor.execute('SELECT timestamp FROM vehicle_events ORDER BY timestamp DESC LIMIT 1')
                    latest = cursor.fetchone()
                    latest_time = latest[0] if latest else None
                    
                    return {
                        'total_events': total,
                        'unique_plates': unique_plates,
                        'today_events': today_count,
                        'latest_event': latest_time
                    }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    def export_csv(self, output_file: str, start_date: Optional[str] = None, 
                   end_date: Optional[str] = None) -> bool:
        """
        Export events to CSV file.
        
        Args:
            output_file: Output CSV file path
            start_date: Optional start date filter
            end_date: Optional end date filter
        
        Returns:
            True if successful
        """
        try:
            import csv
            
            events = self.search_events(start_date=start_date, end_date=end_date, limit=999999)
            
            if not events:
                logger.warning("No events to export")
                return False
            
            with open(output_file, 'w', newline='') as csvfile:
                fieldnames = ['id', 'timestamp', 'video_filename', 'lat', 'lon', 
                            'license_plate', 'car_description', 'confidence']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for event in events:
                    writer.writerow(event)
            
            logger.info(f"Exported {len(events)} events to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            return False


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    db = DatabaseManager()
    
    # Log sample events
    db.log_vehicle_event(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        video_filename="jetsoncam-20231127-123456.mp4",
        lat=40.7128,
        lon=-74.0060,
        license_plate="ABC123",
        car_description="Red Honda Civic 2020",
        confidence=0.95
    )
    
    # Search events
    events = db.search_events(license_plate="ABC")
    print(f"Found {len(events)} events")
    
    # Get stats
    stats = db.get_stats()
    print(f"Stats: {stats}")
