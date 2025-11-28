#!/usr/bin/env python3

"""
George Jetson Dashcam - Project Manifest & Setup Verification
"""

import os
import sys
import json
from pathlib import Path

PROJECT_ROOT = "/opt/george-jetson"

# Project structure definition
PROJECT_STRUCTURE = {
    "directories": {
        "app": "Main application modules",
        "db": "SQLite database storage",
        "videos": "Video recordings output",
        "models": "AI model storage",
        "logs": "Application logs",
        "templates": "Flask HTML templates",
        "static": "Static web assets",
    },
    "python_modules": {
        "app/utils.py": "Utility functions and configuration",
        "app/database.py": "SQLite database management",
        "app/gps_reader.py": "GPS NMEA data reading",
        "app/video_recorder.py": "Video recording with GPU acceleration",
        "app/ai_detector.py": "AI detection engine (ALPR + vehicle classifier)",
        "app/cleanup.py": "Disk cleanup and management",
        "app/web_server.py": "Flask web server and dashboard",
        "app/main.py": "Main application controller",
    },
    "templates": {
        "templates/login.html": "Web login page",
        "templates/dashboard.html": "Main dashboard interface",
    },
    "config_files": {
        "requirements.txt": "Python package dependencies",
        "config.ini": "Application configuration",
        "docker-compose.yml": "Docker deployment configuration",
    },
    "documentation": {
        "README.md": "Complete documentation and user guide",
        "INSTALL.sh": "Automated installation script",
        "examples.py": "Example usage code snippets",
    },
    "scripts": {
        "run.sh": "Main startup and control script",
    }
}

FEATURE_CHECKLIST = {
    "Video Recording": {
        "GPU-accelerated H.264 encoding": "video_recorder.py",
        "5-minute segment splitting": "video_recorder.py",
        "Real-time metadata overlay": "video_recorder.py",
        "FFmpeg NVENC integration": "video_recorder.py",
    },
    "GPS Integration": {
        "NMEA protocol support": "gps_reader.py",
        "Coordinate smoothing": "gps_reader.py",
        "Automatic fix detection": "gps_reader.py",
        "Multi-port fallback": "gps_reader.py",
    },
    "AI Detection": {
        "License plate recognition (ALPR)": "ai_detector.py",
        "Vehicle classification": "ai_detector.py",
        "TensorRT optimization": "ai_detector.py",
        "Configurable inference FPS": "ai_detector.py",
    },
    "Data Logging": {
        "SQLite3 event storage": "database.py",
        "Indexed search queries": "database.py",
        "CSV export functionality": "database.py",
        "Statistics aggregation": "database.py",
    },
    "Disk Management": {
        "Automatic cleanup on low space": "cleanup.py",
        "Configurable retention period": "cleanup.py",
        "Size-based deletion": "cleanup.py",
        "Video listing and sorting": "cleanup.py",
    },
    "Web Dashboard": {
        "Flask web server": "web_server.py",
        "User authentication": "web_server.py",
        "Advanced search interface": "dashboard.html",
        "Video playback streaming": "web_server.py",
        "Real-time statistics": "dashboard.html",
        "REST API endpoints": "web_server.py",
    },
}

DEPENDENCIES = {
    "System": [
        "Python 3.8+",
        "NVIDIA CUDA 11.4+",
        "TensorRT 8.0+",
        "FFmpeg 4.2+",
        "OpenCV 4.5+",
    ],
    "Python Packages": [
        "numpy",
        "opencv-python",
        "pyserial",
        "Flask",
        "Pillow",
        "requests",
        "python-dateutil",
    ],
    "Optional": [
        "tensorrt (GPU acceleration)",
        "torch (AI models)",
        "torchvision (Pre-trained models)",
        "gunicorn (Production server)",
    ]
}

API_ENDPOINTS = [
    "POST /login - Authenticate user",
    "GET /logout - End session",
    "GET /dashboard - Main dashboard",
    "POST /api/search - Search events with filters",
    "GET /api/events/<date> - Get events by date",
    "GET /api/events/video/<filename> - Get video events",
    "GET /api/videos - List video files",
    "GET /api/disk-usage - Disk statistics",
    "GET /api/stats - Database statistics",
    "GET /api/export - Export events to CSV",
    "GET /video/<filename> - Stream video",
    "POST /api/cleanup - Trigger cleanup",
]

DB_SCHEMA = {
    "vehicle_events": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "timestamp": "TEXT NOT NULL",
        "video_filename": "TEXT NOT NULL",
        "lat": "REAL",
        "lon": "REAL",
        "license_plate": "TEXT",
        "car_description": "TEXT",
        "confidence": "REAL",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "indexes": ["timestamp", "license_plate", "video_filename"]
    }
}

def print_header(text):
    """Print formatted header."""
    width = 70
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)

def print_section(title):
    """Print section header."""
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print(f"{'─' * 70}")

def check_file_structure():
    """Verify project file structure."""
    print_section("PROJECT FILE STRUCTURE")
    
    all_good = True
    
    # Check directories
    print("\n📁 Directories:")
    for dir_name, description in PROJECT_STRUCTURE["directories"].items():
        dir_path = os.path.join(PROJECT_ROOT, dir_name)
        exists = os.path.isdir(dir_path)
        status = "✓" if exists else "✗"
        print(f"  {status} {dir_name:20} - {description}")
        all_good = all_good and exists
    
    # Check Python modules
    print("\n🐍 Python Modules:")
    for module, description in PROJECT_STRUCTURE["python_modules"].items():
        file_path = os.path.join(PROJECT_ROOT, module)
        exists = os.path.isfile(file_path)
        status = "✓" if exists else "✗"
        size = os.path.getsize(file_path) if exists else 0
        size_kb = size / 1024
        print(f"  {status} {module:30} ({size_kb:6.1f} KB) - {description}")
        all_good = all_good and exists
    
    # Check templates
    print("\n📄 Templates:")
    for template, description in PROJECT_STRUCTURE["templates"].items():
        file_path = os.path.join(PROJECT_ROOT, template)
        exists = os.path.isfile(file_path)
        status = "✓" if exists else "✗"
        print(f"  {status} {template:30} - {description}")
        all_good = all_good and exists
    
    # Check config files
    print("\n⚙️  Configuration:")
    for config, description in PROJECT_STRUCTURE["config_files"].items():
        file_path = os.path.join(PROJECT_ROOT, config)
        exists = os.path.isfile(file_path)
        status = "✓" if exists else "✗"
        print(f"  {status} {config:30} - {description}")
    
    # Check documentation
    print("\n📚 Documentation:")
    for doc, description in PROJECT_STRUCTURE["documentation"].items():
        file_path = os.path.join(PROJECT_ROOT, doc)
        exists = os.path.isfile(file_path)
        status = "✓" if exists else "✗"
        print(f"  {status} {doc:30} - {description}")
    
    # Check scripts
    print("\n🔧 Scripts:")
    for script, description in PROJECT_STRUCTURE["scripts"].items():
        file_path = os.path.join(PROJECT_ROOT, script)
        exists = os.path.isfile(file_path)
        is_executable = os.access(file_path, os.X_OK) if exists else False
        status = "✓" if (exists and is_executable) else "✗"
        print(f"  {status} {script:30} - {description}")
    
    return all_good

def show_features():
    """Display implemented features."""
    print_section("IMPLEMENTED FEATURES")
    
    for category, features in FEATURE_CHECKLIST.items():
        print(f"\n  {category}:")
        for feature, module in features.items():
            print(f"    ✓ {feature:40} ({module})")

def show_dependencies():
    """Display dependencies."""
    print_section("DEPENDENCIES")
    
    for category, deps in DEPENDENCIES.items():
        print(f"\n  {category}:")
        for dep in deps:
            print(f"    • {dep}")

def show_api():
    """Display API endpoints."""
    print_section("REST API ENDPOINTS")
    
    print("\n  Authentication & Navigation:")
    for endpoint in API_ENDPOINTS[:3]:
        print(f"    • {endpoint}")
    
    print("\n  Search & Query:")
    for endpoint in API_ENDPOINTS[3:7]:
        print(f"    • {endpoint}")
    
    print("\n  Media & Management:")
    for endpoint in API_ENDPOINTS[7:]:
        print(f"    • {endpoint}")

def show_database_schema():
    """Display database schema."""
    print_section("DATABASE SCHEMA")
    
    for table_name, schema in DB_SCHEMA.items():
        print(f"\n  Table: {table_name}")
        print(f"  {'Column':<20} {'Type':<30} {'Description'}")
        print(f"  {'-' * 60}")
        
        for col, type_str in schema.items():
            if col == "indexes":
                continue
            print(f"  {col:<20} {type_str:<30}")
        
        if "indexes" in schema:
            print(f"\n  Indexes: {', '.join(schema['indexes'])}")

def show_quick_start():
    """Display quick start guide."""
    print_section("QUICK START GUIDE")
    
    print("""
  1. Installation:
     cd /opt/george-jetson
     chmod +x INSTALL.sh
     ./INSTALL.sh

  2. Configuration:
     Edit app/utils.py and set your parameters

  3. Start Application:
     ./run.sh start

  4. Access Dashboard:
     http://localhost:8089
     Login: admin / admin

  5. View Logs:
     ./run.sh logs

  Additional Commands:
     ./run.sh web-only     # Web server only (no recording)
     ./run.sh no-web       # Recording only (no web server)
     ./run.sh debug        # Debug mode with verbose logging
     ./run.sh status       # Check application status
     ./run.sh stop         # Stop the application
    """)

def show_folder_tree():
    """Display project folder tree."""
    print_section("PROJECT FOLDER STRUCTURE")
    
    tree = """
  /opt/george-jetson/
  ├── app/
  │   ├── __init__.py
  │   ├── main.py                 # Main application controller
  │   ├── utils.py                # Configuration & utilities
  │   ├── database.py             # SQLite database manager
  │   ├── gps_reader.py           # GPS NMEA reader
  │   ├── video_recorder.py       # GPU-accelerated video recorder
  │   ├── ai_detector.py          # AI detection engine
  │   ├── cleanup.py              # Disk cleanup manager
  │   └── web_server.py           # Flask web server
  │
  ├── templates/
  │   ├── login.html              # Authentication page
  │   └── dashboard.html          # Main dashboard UI
  │
  ├── static/                     # Static web assets (CSS, JS, images)
  │
  ├── db/
  │   └── db.sqlite3              # SQLite database (auto-created)
  │
  ├── videos/                     # Video recordings directory
  │
  ├── models/                     # AI models storage
  │   ├── openalpr/               # OpenALPR models
  │   └── stanford_cars/          # Vehicle classifier models
  │
  ├── logs/                       # Application logs
  │
  ├── run.sh                      # Startup/control script
  ├── INSTALL.sh                  # Installation script
  ├── requirements.txt            # Python dependencies
  ├── config.ini                  # Configuration file
  ├── docker-compose.yml          # Docker deployment
  ├── README.md                   # Documentation
  ├── examples.py                 # Example code
  └── manifest.py                 # This file
    """
    
    print(tree)

def main():
    """Main manifest display."""
    print_header("GEORGE JETSON DASHCAM - PROJECT MANIFEST")
    print(f"\n  Project Root: {PROJECT_ROOT}")
    print(f"  Purpose: GPU-accelerated dashcam with vehicle detection")
    print(f"  Target: NVIDIA Jetson Orin Nano Super")
    print(f"  Python: 3.8+")
    
    # Show content based on arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "structure":
            show_folder_tree()
            check_file_structure()
        elif command == "features":
            show_features()
        elif command == "dependencies":
            show_dependencies()
        elif command == "api":
            show_api()
        elif command == "schema":
            show_database_schema()
        elif command == "quickstart":
            show_quick_start()
        elif command == "all":
            show_folder_tree()
            if check_file_structure():
                print("\n✓ All files present!")
            show_features()
            show_dependencies()
            show_api()
            show_database_schema()
            show_quick_start()
        else:
            print(f"\n❌ Unknown command: {command}")
            print_usage()
    else:
        # Default: show comprehensive overview
        show_folder_tree()
        check_file_structure()
        show_features()
        show_dependencies()
        show_quick_start()
    
    print_header("END OF MANIFEST")

def print_usage():
    """Print usage information."""
    print("""
  Usage: python3 manifest.py [command]
  
  Commands:
    structure       Show folder structure and file locations
    features        List all implemented features
    dependencies    Show required dependencies
    api             Display REST API endpoints
    schema          Show database schema
    quickstart      Quick start guide
    all             Show everything
    (default)       Show overview
    """)

if __name__ == '__main__':
    main()
