"""
Example usage and integration code for George Jetson Dashcam
"""

# ==========================================
# Example 1: Basic Application Startup
# ==========================================

from app.main import GeorgJetsonDashcam

def example_basic_startup():
    """Start the dashcam application."""
    dashcam = GeorgJetsonDashcam()
    
    if not dashcam.initialize():
        print("Failed to initialize")
        return
    
    if not dashcam.start():
        print("Failed to start")
        return
    
    # Application is now recording
    print("Dashcam running. Press Ctrl+C to stop.")
    
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        dashcam.stop()


# ==========================================
# Example 2: Custom Configuration
# ==========================================

def example_custom_config():
    """Start with custom configuration."""
    from app.utils import DEFAULT_CONFIG
    
    # Copy default config and customize
    custom_config = DEFAULT_CONFIG.copy()
    custom_config['VIDEO_WIDTH'] = 1280
    custom_config['VIDEO_HEIGHT'] = 720
    custom_config['AI_INFERENCE_FPS'] = 3  # Lower load
    custom_config['MIN_FREE_DISK_PERCENT'] = 15
    custom_config['WEB_PORT'] = 8090
    
    dashcam = GeorgJetsonDashcam(config=custom_config)
    dashcam.initialize()
    dashcam.start()


# ==========================================
# Example 3: Database Queries
# ==========================================

def example_database_queries():
    """Examples of database operations."""
    from app.database import DatabaseManager
    from datetime import datetime, timedelta
    
    db = DatabaseManager()
    
    # Log a vehicle detection
    db.log_vehicle_event(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        video_filename="jetsoncam-20231127-120000.mp4",
        lat=40.7128,
        lon=-74.0060,
        license_plate="ABC123",
        car_description="Red Honda Civic 2020",
        confidence=0.95
    )
    
    # Search by license plate
    events = db.search_events(license_plate="ABC")
    print(f"Found {len(events)} events matching ABC")
    
    # Search by date range
    start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")
    events = db.search_events(start_date=start, end_date=end)
    print(f"Found {len(events)} events in last 7 days")
    
    # Search by vehicle attributes
    events = db.search_events(color="red", make="Honda")
    print(f"Found {len(events)} red Honda vehicles")
    
    # Get statistics
    stats = db.get_stats()
    print(f"Total events: {stats['total_events']}")
    print(f"Unique plates: {stats['unique_plates']}")
    print(f"Today events: {stats['today_events']}")
    
    # Export to CSV
    db.export_csv('/tmp/events_export.csv', start_date=start, end_date=end)
    print("Exported events to CSV")
    
    # Get events for specific video
    events = db.get_events_by_video("jetsoncam-20231127-120000.mp4")
    print(f"Found {len(events)} detections in video")


# ==========================================
# Example 4: GPS Data
# ==========================================

def example_gps_operations():
    """GPS reader examples."""
    from app.gps_reader import GPSReader
    import time
    
    gps = GPSReader(port='/dev/ttyUSB0', baudrate=4800)
    
    # Start GPS reader
    gps.start()
    
    # Wait for fix
    if gps.wait_for_fix(timeout=30):
        print("GPS fix acquired!")
        
        # Get current position
        lat, lon = gps.get_position()
        print(f"Position: {lat:.6f}, {lon:.6f}")
        
        # Get detailed data
        data = gps.get_current_data()
        print(f"Satellites: {data['satellites']}")
        print(f"Altitude: {data['altitude']:.2f}m")
        print(f"Speed: {data['speed']} knots")
    else:
        print("No GPS fix")
    
    # Read for 30 seconds
    for i in range(30):
        data = gps.get_current_data()
        if data['has_fix']:
            print(f"[{i}] GPS: {data['latitude']:.6f}, {data['longitude']:.6f}")
        time.sleep(1)
    
    gps.stop()


# ==========================================
# Example 5: Video Recording
# ==========================================

def example_video_recording():
    """Video recorder examples."""
    from app.video_recorder import VideoRecorder
    from datetime import datetime
    import time
    
    recorder = VideoRecorder(
        output_dir='/videos',
        width=1920,
        height=1080,
        fps=30,
        segment_duration=300
    )
    
    # Define overlay callback
    def get_overlay_data():
        return {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'gps_lat': 40.7128,
            'gps_lon': -74.0060,
            'vehicle_detections': [
                {
                    'license_plate': 'ABC123',
                    'description': 'Red Honda Civic',
                    'confidence': 0.95
                }
            ]
        }
    
    recorder.set_on_frame_callback(get_overlay_data)
    
    # Start recording
    recorder.start()
    print(f"Recording started to {recorder.get_current_segment()}")
    
    # Record for 2 minutes
    for i in range(120):
        time.sleep(1)
        frames = recorder.get_frame_count()
        print(f"[{i}] Recorded {frames} frames")
    
    recorder.stop()
    print("Recording stopped")


# ==========================================
# Example 6: AI Detection
# ==========================================

def example_ai_detection():
    """AI detection examples."""
    from app.ai_detector import AIDetector
    import numpy as np
    import time
    
    detector = AIDetector(
        inference_fps=5,
        confidence_threshold=0.5
    )
    
    # Define detection callback
    def on_detection(detections):
        for det in detections:
            print(f"Detected: {det.make} {det.model} "
                  f"({det.color}) [{det.license_plate}] "
                  f"Confidence: {det.confidence:.2f}")
    
    detector.set_detections_callback(on_detection)
    detector.start()
    
    # Feed dummy frames
    dummy_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    
    for i in range(60):
        detector.set_input_frame(dummy_frame)
        time.sleep(0.2)
        
        detections = detector.get_latest_detections()
        stats = detector.get_stats()
        print(f"[{i}] Detections: {stats['latest_detections']}")
    
    detector.stop()


# ==========================================
# Example 7: Disk Management
# ==========================================

def example_disk_management():
    """Disk cleanup examples."""
    from app.cleanup import DiskCleanupManager
    
    cleanup = DiskCleanupManager(
        video_dir='/videos',
        min_free_percent=10.0,
        retention_days=30
    )
    
    # Check disk usage
    usage = cleanup.get_disk_usage()
    print(f"Disk usage: {usage['percent_used']:.1f}%")
    print(f"Free space: {usage['free'] / (1024**3):.2f} GB")
    
    # Get video list
    videos = cleanup.get_video_list(sort_by='date', descending=True)
    print(f"\nLatest videos:")
    for video in videos[:10]:
        print(f"  {video['filename']} - {video['size_mb']} MB - {video['modified_time']}")
    
    # Check if cleanup needed
    if cleanup.check_disk_space():
        print("Cleanup performed")
    
    # Manual cleanup of old files
    deleted = cleanup.cleanup_by_size(target_free_percent=20.0)
    print(f"Deleted {deleted} old videos")
    
    # Cleanup by date
    deleted = cleanup.cleanup_old_files(days=30)
    print(f"Deleted {deleted} videos older than 30 days")


# ==========================================
# Example 8: Web Server & API
# ==========================================

def example_web_api():
    """Web server and API examples."""
    from app.web_server import DashcamWebServer
    from app.database import DatabaseManager
    from app.cleanup import DiskCleanupManager
    
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
    
    # Start server (blocking)
    print("Starting web server on http://localhost:8089")
    print("Login: admin / admin")
    server.run(debug=False)


# ==========================================
# Example 9: API Client
# ==========================================

def example_api_client():
    """Client code to interact with web API."""
    import requests
    import json
    
    BASE_URL = "http://localhost:8089"
    
    # Create session
    session = requests.Session()
    
    # Login
    login_data = {
        'username': 'admin',
        'password': 'admin'
    }
    r = session.post(f"{BASE_URL}/login", data=login_data)
    print(f"Login: {r.status_code}")
    
    # Get statistics
    r = session.get(f"{BASE_URL}/api/stats")
    stats = r.json()
    print(f"Total events: {stats['stats']['total_events']}")
    
    # Search events
    search_data = {
        'license_plate': 'ABC',
        'limit': 50
    }
    r = session.post(f"{BASE_URL}/api/search", json=search_data)
    results = r.json()
    print(f"Search results: {results['count']} events")
    
    # Get disk usage
    r = session.get(f"{BASE_URL}/api/disk-usage")
    disk = r.json()
    print(f"Disk usage: {disk['usage']['percent_used']:.1f}%")
    
    # Get videos list
    r = session.get(f"{BASE_URL}/api/videos?sort=date&desc=true")
    videos = r.json()
    print(f"Videos: {len(videos['videos'])} files")
    
    # Export CSV
    r = session.get(f"{BASE_URL}/api/export?start_date=2023-11-01&end_date=2023-11-30")
    with open('events.csv', 'wb') as f:
        f.write(r.content)
    print("Exported CSV")


# ==========================================
# Example 10: Performance Monitoring
# ==========================================

def example_performance_monitoring():
    """Monitor performance metrics."""
    from app.main import GeorgJetsonDashcam
    import time
    import psutil
    import cv2
    
    dashcam = GeorgJetsonDashcam()
    dashcam.initialize()
    dashcam.start()
    
    # Monitor for 60 seconds
    for i in range(60):
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # GPU utilization (if available)
        try:
            gpu_count = cv2.cuda.getCudaEnabledDeviceCount()
            gpu_info = f"GPU devices: {gpu_count}"
        except:
            gpu_info = "GPU: N/A"
        
        # Frame count
        frames = dashcam.recorder.get_frame_count()
        
        print(f"[{i}] CPU: {cpu_percent:.1f}% | "
              f"Mem: {memory.percent:.1f}% | "
              f"Frames: {frames} | {gpu_info}")
        
        time.sleep(1)
    
    dashcam.stop()


# ==========================================
# Main Test Runner
# ==========================================

if __name__ == '__main__':
    import sys
    
    examples = {
        '1': ('Basic Startup', example_basic_startup),
        '2': ('Custom Configuration', example_custom_config),
        '3': ('Database Queries', example_database_queries),
        '4': ('GPS Operations', example_gps_operations),
        '5': ('Video Recording', example_video_recording),
        '6': ('AI Detection', example_ai_detection),
        '7': ('Disk Management', example_disk_management),
        '8': ('Web Server', example_web_api),
        '9': ('API Client', example_api_client),
        '10': ('Performance Monitoring', example_performance_monitoring),
    }
    
    print("George Jetson Dashcam - Examples")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        if example_num in examples:
            print(f"\nRunning: {examples[example_num][0]}")
            print("=" * 50)
            examples[example_num][1]()
        else:
            print(f"Example {example_num} not found")
    else:
        print("\nAvailable examples:")
        for num, (name, _) in examples.items():
            print(f"  {num}: {name}")
        print("\nUsage: python3 examples.py <number>")
