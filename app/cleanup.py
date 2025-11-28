"""
Disk Cleanup Module - Manages disk space and deletes old videos/logs
"""
import os
import shutil
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)


class DiskCleanupManager:
    """Manage disk space by cleaning old videos and logs."""
    
    def __init__(self, video_dir: str = '/videos',
                 db_path: str = '/opt/george-jetson/db/db.sqlite3',
                 min_free_percent: float = 10.0,
                 retention_days: int = 30,
                 check_interval: int = 300):
        """
        Initialize disk cleanup manager.
        
        Args:
            video_dir: Directory containing video files
            db_path: Path to database file
            min_free_percent: Minimum free disk percentage (e.g., 10%)
            retention_days: Retain logs for this many days
            check_interval: Check disk space every N seconds
        """
        self.video_dir = video_dir
        self.db_path = db_path
        self.min_free_percent = min_free_percent
        self.retention_days = retention_days
        self.check_interval = check_interval
        
        self.running = False
        self.thread = None
        
        Path(video_dir).mkdir(parents=True, exist_ok=True)
    
    def start(self) -> bool:
        """Start disk cleanup monitoring in background thread."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self.thread.start()
            logger.info("Disk cleanup manager started")
            return True
        return False
    
    def stop(self):
        """Stop disk cleanup monitoring."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Disk cleanup manager stopped")
    
    def _cleanup_loop(self):
        """Main cleanup loop (runs in background thread)."""
        while self.running:
            try:
                self.check_disk_space()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                time.sleep(self.check_interval)
    
    def get_disk_usage(self, path: str = None) -> Dict:
        """
        Get disk usage statistics.
        
        Args:
            path: Path to check (defaults to video_dir)
        
        Returns:
            Dict with 'total', 'used', 'free', 'percent'
        """
        if path is None:
            path = self.video_dir
        
        try:
            stat = shutil.disk_usage(path)
            total = stat.total
            used = stat.used
            free = stat.free
            percent_used = (used / total * 100) if total > 0 else 0
            
            return {
                'total': total,
                'used': used,
                'free': free,
                'percent_used': round(percent_used, 2),
                'percent_free': round(100 - percent_used, 2)
            }
        except Exception as e:
            logger.error(f"Error getting disk usage: {e}")
            return {}
    
    def check_disk_space(self) -> bool:
        """
        Check disk space and clean if necessary.
        
        Returns:
            True if cleanup was performed, False otherwise
        """
        usage = self.get_disk_usage()
        
        if not usage:
            return False
        
        percent_free = usage.get('percent_free', 0)
        
        logger.info(f"Disk usage: {percent_free:.1f}% free ({self._format_bytes(usage['free'])} free)")
        
        if percent_free < self.min_free_percent:
            logger.warning(f"Low disk space: {percent_free:.1f}% free (min: {self.min_free_percent}%)")
            return self.cleanup_old_files()
        
        return False
    
    def cleanup_old_files(self, days: int = None) -> bool:
        """
        Delete old video files and database records.
        
        Args:
            days: Delete files older than N days (defaults to retention_days)
        
        Returns:
            True if cleanup was performed
        """
        if days is None:
            days = self.retention_days
        
        cutoff_time = datetime.now() - timedelta(days=days)
        
        logger.info(f"Starting cleanup of files older than {cutoff_time.strftime('%Y-%m-%d')}")
        
        deleted_videos = self._cleanup_videos(cutoff_time)
        deleted_db_records = self._cleanup_database_records(days)
        
        if deleted_videos > 0 or deleted_db_records > 0:
            logger.info(f"Cleanup complete: {deleted_videos} videos, {deleted_db_records} DB records deleted")
            return True
        
        return False
    
    def _cleanup_videos(self, cutoff_time: datetime) -> int:
        """
        Delete video files older than cutoff time.
        
        Args:
            cutoff_time: Delete files modified before this time
        
        Returns:
            Number of deleted files
        """
        deleted_count = 0
        
        try:
            if not os.path.exists(self.video_dir):
                return 0
            
            for filename in os.listdir(self.video_dir):
                if not filename.endswith('.mp4'):
                    continue
                
                filepath = os.path.join(self.video_dir, filename)
                
                try:
                    mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    if mod_time < cutoff_time:
                        file_size = os.path.getsize(filepath)
                        os.remove(filepath)
                        logger.info(f"Deleted old video: {filename} ({self._format_bytes(file_size)})")
                        deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting video {filename}: {e}")
        
        except Exception as e:
            logger.error(f"Error cleaning up videos: {e}")
        
        return deleted_count
    
    def _cleanup_database_records(self, days: int) -> int:
        """
        Delete old database records.
        
        Args:
            days: Delete records older than N days
        
        Returns:
            Number of deleted records
        """
        try:
            import sqlite3
            
            if not os.path.exists(self.db_path):
                return 0
            
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'DELETE FROM vehicle_events WHERE timestamp < ?',
                    (f"{cutoff_date} 00:00:00",)
                )
                conn.commit()
                deleted_count = cursor.rowcount
                
                if deleted_count > 0:
                    logger.info(f"Deleted {deleted_count} old database records")
                
                return deleted_count
        
        except Exception as e:
            logger.error(f"Error cleaning up database: {e}")
            return 0
    
    def cleanup_by_size(self, target_free_percent: float = 15.0) -> int:
        """
        Delete oldest videos until target free space is reached.
        
        Args:
            target_free_percent: Target free percentage
        
        Returns:
            Number of deleted files
        """
        deleted_count = 0
        
        try:
            while True:
                usage = self.get_disk_usage()
                percent_free = usage.get('percent_free', 0)
                
                if percent_free >= target_free_percent:
                    break
                
                # Find oldest video
                oldest_file = self._get_oldest_video()
                
                if not oldest_file:
                    logger.warning("No more videos to delete")
                    break
                
                filepath = os.path.join(self.video_dir, oldest_file)
                file_size = os.path.getsize(filepath)
                
                os.remove(filepath)
                logger.info(f"Deleted {oldest_file} ({self._format_bytes(file_size)}) to free space")
                deleted_count += 1
        
        except Exception as e:
            logger.error(f"Error cleaning up by size: {e}")
        
        return deleted_count
    
    def _get_oldest_video(self) -> str:
        """
        Find the oldest video file in video directory.
        
        Returns:
            Filename of oldest video or None
        """
        try:
            if not os.path.exists(self.video_dir):
                return None
            
            videos = [f for f in os.listdir(self.video_dir) if f.endswith('.mp4')]
            
            if not videos:
                return None
            
            oldest = min(videos, key=lambda f: os.path.getmtime(os.path.join(self.video_dir, f)))
            return oldest
        
        except Exception as e:
            logger.error(f"Error finding oldest video: {e}")
            return None
    
    def get_video_list(self, sort_by: str = 'date', descending: bool = True) -> List[Dict]:
        """
        Get list of video files with metadata.
        
        Args:
            sort_by: 'date' or 'size'
            descending: Sort in descending order
        
        Returns:
            List of dicts with 'filename', 'size', 'modified_time'
        """
        videos = []
        
        try:
            if not os.path.exists(self.video_dir):
                return []
            
            for filename in os.listdir(self.video_dir):
                if not filename.endswith('.mp4'):
                    continue
                
                filepath = os.path.join(self.video_dir, filename)
                
                try:
                    stat = os.stat(filepath)
                    mod_time = datetime.fromtimestamp(stat.st_mtime)
                    
                    videos.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'modified_time': mod_time.strftime("%Y-%m-%d %H:%M:%S"),
                        'size_mb': round(stat.st_size / (1024 * 1024), 2)
                    })
                except Exception as e:
                    logger.debug(f"Error getting info for {filename}: {e}")
            
            # Sort
            reverse = descending
            if sort_by == 'date':
                videos.sort(key=lambda v: v['modified_time'], reverse=reverse)
            elif sort_by == 'size':
                videos.sort(key=lambda v: v['size'], reverse=reverse)
            
            return videos
        
        except Exception as e:
            logger.error(f"Error getting video list: {e}")
            return []
    
    def _format_bytes(self, bytes_val: int) -> str:
        """Convert bytes to human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    cleanup = DiskCleanupManager(
        video_dir='/videos',
        min_free_percent=10.0,
        retention_days=30
    )
    
    # Check disk usage
    usage = cleanup.get_disk_usage()
    print(f"Disk usage: {usage}")
    
    # Get video list
    videos = cleanup.get_video_list()
    print(f"Videos: {videos}")
    
    # Start background cleanup
    cleanup.start()
    time.sleep(5)
    cleanup.stop()
