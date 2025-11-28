"""
Web Dashboard - Flask-based web portal for video search, playback, and monitoring
"""
import os
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash
import mimetypes

logger = logging.getLogger(__name__)


class DashcamWebServer:
    """Flask web server for dashcam dashboard and API."""
    
    def __init__(self, database_manager, cleanup_manager, video_dir: str = '/videos',
                 host: str = '0.0.0.0', port: int = 8089,
                 admin_user: str = 'admin', admin_pass: str = 'admin'):
        """
        Initialize web server.
        
        Args:
            database_manager: DatabaseManager instance
            cleanup_manager: DiskCleanupManager instance
            video_dir: Directory with video files
            host: Server host
            port: Server port
            admin_user: Admin username
            admin_pass: Admin password
        """
        self.db = database_manager
        self.cleanup = cleanup_manager
        self.video_dir = video_dir
        self.host = host
        self.port = port
        
        # Setup Flask app
        self.app = Flask(__name__, 
                        template_folder='templates',
                        static_folder='static')
        self.app.secret_key = 'george-jetson-dashcam-secret-key-change-in-production'
        
        # Admin credentials (hash in production)
        self.admin_user = admin_user
        self.admin_pass_hash = generate_password_hash(admin_pass)
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup all Flask routes."""
        
        @self.app.route('/')
        def index():
            if 'user' not in session:
                return redirect(url_for('login'))
            return redirect(url_for('dashboard'))
        
        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            if request.method == 'POST':
                username = request.form.get('username', '')
                password = request.form.get('password', '')
                
                if username == self.admin_user and check_password_hash(self.admin_pass_hash, password):
                    session['user'] = username
                    return redirect(url_for('dashboard'))
                else:
                    return render_template('login.html', error='Invalid credentials')
            
            return render_template('login.html')
        
        @self.app.route('/logout')
        def logout():
            session.clear()
            return redirect(url_for('login'))
        
        @self.app.route('/dashboard')
        @self._require_login
        def dashboard():
            stats = self.db.get_stats()
            disk_usage = self.cleanup.get_disk_usage()
            
            return render_template('dashboard.html',
                                 stats=stats,
                                 disk_usage=disk_usage)
        
        @self.app.route('/api/search', methods=['POST'])
        @self._require_login
        def api_search():
            """Search API endpoint."""
            try:
                start_date = request.json.get('start_date')
                end_date = request.json.get('end_date')
                license_plate = request.json.get('license_plate')
                color = request.json.get('color')
                make = request.json.get('make')
                model = request.json.get('model')
                limit = int(request.json.get('limit', 100))
                
                events = self.db.search_events(
                    start_date=start_date,
                    end_date=end_date,
                    license_plate=license_plate,
                    color=color,
                    make=make,
                    model=model,
                    limit=limit
                )
                
                return jsonify({
                    'success': True,
                    'count': len(events),
                    'events': events
                })
            except Exception as e:
                logger.error(f"Search error: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
        
        @self.app.route('/api/events/<date>')
        @self._require_login
        def api_get_events_by_date(date):
            """Get events for specific date."""
            try:
                events = self.db.get_events_by_date(date, limit=500)
                return jsonify({'success': True, 'events': events})
            except Exception as e:
                logger.error(f"Error getting events: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
        
        @self.app.route('/api/events/video/<video_filename>')
        @self._require_login
        def api_get_events_by_video(video_filename):
            """Get events for specific video."""
            try:
                events = self.db.get_events_by_video(video_filename)
                return jsonify({'success': True, 'events': events})
            except Exception as e:
                logger.error(f"Error getting events: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
        
        @self.app.route('/api/videos')
        @self._require_login
        def api_get_videos():
            """Get list of video files."""
            try:
                sort_by = request.args.get('sort', 'date')
                descending = request.args.get('desc', 'true').lower() == 'true'
                
                videos = self.cleanup.get_video_list(sort_by=sort_by, descending=descending)
                
                return jsonify({'success': True, 'videos': videos})
            except Exception as e:
                logger.error(f"Error getting videos: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
        
        @self.app.route('/api/disk-usage')
        @self._require_login
        def api_disk_usage():
            """Get disk usage statistics."""
            try:
                usage = self.cleanup.get_disk_usage()
                videos = self.cleanup.get_video_list()
                
                return jsonify({
                    'success': True,
                    'usage': usage,
                    'video_count': len(videos),
                    'total_size_mb': sum(v['size_mb'] for v in videos)
                })
            except Exception as e:
                logger.error(f"Error getting disk usage: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
        
        @self.app.route('/api/stats')
        @self._require_login
        def api_stats():
            """Get database statistics."""
            try:
                stats = self.db.get_stats()
                return jsonify({'success': True, 'stats': stats})
            except Exception as e:
                logger.error(f"Error getting stats: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
        
        @self.app.route('/video/<filename>')
        @self._require_login
        def get_video(filename):
            """Stream video file."""
            try:
                # Validate filename to prevent directory traversal
                if '..' in filename or '/' in filename:
                    return 'Invalid filename', 400
                
                filepath = os.path.join(self.video_dir, filename)
                
                if not os.path.exists(filepath):
                    return 'Video not found', 404
                
                return send_file(filepath, mimetype='video/mp4')
            except Exception as e:
                logger.error(f"Error serving video: {e}")
                return 'Error serving video', 500
        
        @self.app.route('/api/export')
        @self._require_login
        def api_export():
            """Export events to CSV."""
            try:
                start_date = request.args.get('start_date')
                end_date = request.args.get('end_date')
                
                export_file = '/tmp/dashcam_export.csv'
                if self.db.export_csv(export_file, start_date=start_date, end_date=end_date):
                    return send_file(export_file, as_attachment=True, 
                                   download_name='dashcam_events.csv')
                else:
                    return 'No events to export', 400
            except Exception as e:
                logger.error(f"Error exporting: {e}")
                return 'Export failed', 500
        
        @self.app.route('/api/cleanup', methods=['POST'])
        @self._require_login
        def api_cleanup():
            """Trigger manual cleanup."""
            try:
                action = request.json.get('action', 'check')
                
                if action == 'cleanup':
                    deleted = self.cleanup.cleanup_old_files()
                    return jsonify({
                        'success': True,
                        'cleaned': deleted,
                        'message': f'Cleanup completed'
                    })
                elif action == 'cleanup_by_size':
                    target_percent = float(request.json.get('target_percent', 15.0))
                    deleted = self.cleanup.cleanup_by_size(target_percent)
                    return jsonify({
                        'success': True,
                        'cleaned': deleted,
                        'message': f'Deleted {deleted} files'
                    })
                else:
                    usage = self.cleanup.get_disk_usage()
                    return jsonify({'success': True, 'usage': usage})
            
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
    
    def _require_login(self, f):
        """Decorator to require login."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    
    def run(self, debug: bool = False):
        """Start the Flask development server."""
        logger.info(f"Starting web server on {self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=debug, threaded=True)
    
    def get_app(self):
        """Get Flask app for production servers (Gunicorn, uWSGI)."""
        return self.app


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    from database import DatabaseManager
    from cleanup import DiskCleanupManager
    
    db = DatabaseManager()
    cleanup = DiskCleanupManager()
    
    server = DashcamWebServer(
        database_manager=db,
        cleanup_manager=cleanup,
        host='0.0.0.0',
        port=8089,
        admin_user='admin',
        admin_pass='admin'
    )
    
    server.run(debug=True)
