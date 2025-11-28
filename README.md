# George Jetson Dashcam

A production-grade dashcam application for NVIDIA Jetson Orin Nano Super with real-time GPU-accelerated vehicle detection, license plate recognition (ALPR), and web-based video management.

## Features

✅ **Video Recording**
- GPU-accelerated H.264/H.265 encoding with FFmpeg
- 5-minute video segments saved to NVMe SSD
- Real-time GPS and metadata overlay

✅ **GPS Integration**
- NMEA protocol support for USB GPS dongles
- Real-time coordinate smoothing and accuracy verification
- GPS overlay on video and database logging

✅ **AI Vehicle Detection (GPU-Accelerated)**
- Automatic License Plate Recognition (ALPR) with OpenALPR
- Vehicle attribute classification (make, model, color)
- TensorRT optimization for 5+ FPS inference on Jetson
- Stanford Cars Dataset model integration

✅ **Data Logging**
- SQLite3 database with vehicle detection events
- Indexed queries for fast searches
- Export to CSV functionality

✅ **Disk Management**
- Automatic cleanup when disk < 10% free
- 30-day log retention (configurable)
- Oldest-first deletion strategy

✅ **Web Dashboard**
- Modern Flask-based web interface
- Search by date range, license plate, color, make, model
- Video playback with timestamp overlay
- Real-time statistics and disk monitoring

## Hardware Requirements

- **CPU**: NVIDIA Jetson Orin Nano Super (8-core ARM64)
- **RAM**: 8GB LPDDR5
- **GPU**: Ampere architecture (40 CUDA cores)
- **Storage**: 1TB NVMe SSD mounted at `/videos`
- **Camera**: 5MP CSI or USB camera (1920x1080 @ 30fps)
- **GPS**: USB NMEA GPS dongle (typically `/dev/ttyUSB0`)

## Software Requirements

- **OS**: JetPack 5.0 or later (Ubuntu 20.04 or 22.04)
- **CUDA**: 11.4 or later (pre-installed with JetPack)
- **TensorRT**: 8.0 or later (pre-installed with JetPack)
- **Python**: 3.8+
- **FFmpeg**: 4.2+ with hardware encoder support
- **OpenCV**: 4.5+ with CUDA support

## Installation

### 1. Setup JetPack Environment

```bash
# Flash Jetson with latest JetPack
# Download from: https://developer.nvidia.com/jetpack

# After boot, verify JetPack installation
jetpack-components

# Verify CUDA
nvcc --version

# Verify TensorRT
python3 -c "import tensorrt; print(tensorrt.__version__)"
```

### 2. Clone and Setup Project

```bash
cd /var/www/html
git clone <repository-url> george-jetson
cd george-jetson

# Make run script executable
chmod +x run.sh

# Run setup
./run.sh setup
```

### 3. Install Dependencies

```bash
# Automated (via run.sh)
./run.sh setup

# Or manual
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install system packages
sudo apt-get update
sudo apt-get install -y \
    ffmpeg \
    libopencv-dev \
    python3-opencv \
    openalpr \
    openalpr-daemon
```

### 4. Download AI Models

```bash
# OpenALPR models (if not pre-installed)
mkdir -p models/openalpr
sudo cp /usr/share/openalpr/runtime_data/* models/openalpr/

# Stanford Cars classifier (optional - included in torchvision)
# For custom model, download from:
# https://ai.stanford.edu/~jkrause/cars/car_dataset.html

python3 -c "import torchvision; print(torchvision.models.list_models())"
```

## Configuration

Edit configuration in `/var/www/html/george-jetson/app/utils.py`:

```python
DEFAULT_CONFIG = {
    'VIDEO_DIR': '/videos',                    # Video output directory
    'DB_PATH': '/var/www/html/george-jetson/db/db.sqlite3',
    'SEGMENT_DURATION': 300,                   # 5 minutes in seconds
    'VIDEO_WIDTH': 1920,
    'VIDEO_HEIGHT': 1080,
    'VIDEO_FPS': 30,
    'GPS_PORT': '/dev/ttyUSB0',               # GPS device
    'GPS_BAUDRATE': 4800,                      # NMEA default
    'MIN_FREE_DISK_PERCENT': 10,              # Cleanup trigger
    'RETENTION_DAYS': 30,                      # Log retention
    'WEB_PORT': 8089,
    'WEB_HOST': '0.0.0.0',
    'ADMIN_USER': 'admin',
    'ADMIN_PASS': 'admin',                     # CHANGE IN PRODUCTION
    'AI_CONFIDENCE_THRESHOLD': 0.5,
    'AI_INFERENCE_FPS': 5,
}
```

## Usage

### Quick Start

```bash
# Start full application (recording + web server)
./run.sh start

# Start web server only (for testing without camera)
./run.sh web-only

# Start recording without web interface
./run.sh no-web

# View logs
./run.sh logs

# Check status
./run.sh status
```

### Python API

```python
from app.main import GeorgJetsonDashcam

# Initialize
dashcam = GeorgJetsonDashcam()
dashcam.initialize()
dashcam.start()

# Dashcam now recording with AI detection
# Access web dashboard at http://localhost:8089

# Query database
events = dashcam.db.search_events(license_plate="ABC")
print(f"Found {len(events)} matching events")

# Check disk usage
usage = dashcam.cleanup.get_disk_usage()
print(f"Disk: {usage['percent_used']:.1f}% used")

# Stop
dashcam.stop()
```

## API Endpoints

### Authentication
- `POST /login` - Login with credentials
- `GET /logout` - Logout

### Dashboard
- `GET /` - Dashboard (redirects to /login if not authenticated)
- `GET /dashboard` - Main dashboard page

### Search & Query
- `POST /api/search` - Search events with filters
  ```json
  {
    "start_date": "2023-11-01",
    "end_date": "2023-11-30",
    "license_plate": "ABC",
    "color": "red",
    "make": "Honda",
    "model": "Civic",
    "limit": 100
  }
  ```

- `GET /api/events/<date>` - Get events for specific date
- `GET /api/events/video/<filename>` - Get events for video
- `GET /api/videos` - List all video files
- `GET /api/disk-usage` - Disk usage statistics
- `GET /api/stats` - Database statistics
- `GET /api/export` - Export events to CSV

### Media
- `GET /video/<filename>` - Stream video file
- `POST /api/cleanup` - Trigger manual cleanup

## Database Schema

### vehicle_events table

```sql
CREATE TABLE vehicle_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,              -- Event timestamp
    video_filename TEXT NOT NULL,          -- Associated video file
    lat REAL,                              -- Latitude coordinate
    lon REAL,                              -- Longitude coordinate
    license_plate TEXT,                    -- Detected license plate
    car_description TEXT,                  -- Color, make, model
    confidence REAL,                       -- Detection confidence (0-1)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(timestamp, video_filename, license_plate)
);

-- Indices for performance
CREATE INDEX idx_timestamp ON vehicle_events(timestamp);
CREATE INDEX idx_license_plate ON vehicle_events(license_plate);
CREATE INDEX idx_video_filename ON vehicle_events(video_filename);
```

## FFmpeg GPU Encoding

The application uses NVIDIA NVENC encoder for hardware-accelerated video encoding:

```bash
# Check available encoders
ffmpeg -encoders | grep -i nvenc

# Manual encoding (for testing)
ffmpeg -f rawvideo -pixel_format bgr24 -video_size 1920x1080 \
  -framerate 30 -i input.raw \
  -c:v h264_nvenc -preset default -rc:v vbr -b:v 5000k \
  -y output.mp4
```

## TensorRT Optimization

For production deployment, export models to TensorRT:

```python
import torch
import tensorrt as trt

# Convert PyTorch model to TensorRT engine
model = torch.hub.load('pytorch/vision:v0.10.0', 'resnet50', pretrained=True)
model.eval()

# Export to ONNX
torch.onnx.export(model, dummy_input, "model.onnx")

# Convert ONNX to TensorRT
# Use trtexec: /usr/src/tensorrt/bin/trtexec --onnx=model.onnx --saveEngine=model.trt
```

## Troubleshooting

### Camera not detected
```bash
# List available cameras
ls -la /dev/video*

# Test camera
ffmpeg -f v4l2 -list_formats all -i /dev/video0

# Try different camera index in code
```

### GPS not acquiring fix
```bash
# Check device
ls -la /dev/ttyUSB*

# Test GPS output
cat /dev/ttyUSB0

# Monitor GPS in real-time
python3 -c "from app.gps_reader import GPSReader; \
gps = GPSReader(); gps.start(); gps.wait_for_fix(60)"
```

### Disk space issues
```bash
# Check disk usage
df -h /videos

# Manually cleanup old videos
python3 -c "from app.cleanup import DiskCleanupManager; \
dm = DiskCleanupManager(); dm.cleanup_by_size(15.0)"
```

### TensorRT not available
```bash
# Verify TensorRT installation
python3 -c "import tensorrt; print(tensorrt.__version__)"

# If missing, reinstall JetPack or:
sudo apt-get install tensorrt
```

### Web server won't start
```bash
# Check port binding
sudo lsof -i :8089

# Kill existing process if needed
sudo pkill -f "python3 main.py"

# Try different port in config
# PORT_8089 -> PORT_8090 in utils.py
```

## Performance Tuning

### GPU Utilization

```python
# Monitor GPU usage
import cv2
print(f"CUDA devices: {cv2.cuda.getCudaEnabledDeviceCount()}")

# Force GPU for OpenCV operations
frame_gpu = cv2.cuda_GpuMat()
frame_gpu.upload(frame)
```

### Inference Optimization

```python
# Reduce inference FPS to save GPU
# In utils.py: AI_INFERENCE_FPS: 2-3 for lower resource usage

# Use lower video resolution for AI
# VIDEO_WIDTH: 1280, VIDEO_HEIGHT: 720 reduces AI load 4x
```

### Disk I/O

```bash
# Use faster SSD settings
# Check current settings
cat /sys/block/nvme0n1/queue/scheduler

# Optimize for throughput
echo noop | sudo tee /sys/block/nvme0n1/queue/scheduler
```

## Systemd Service (Optional)

Create `/etc/systemd/system/george-jetson-dashcam.service`:

```ini
[Unit]
Description=George Jetson Dashcam Service
After=network.target

[Service]
Type=simple
User=jetson
WorkingDirectory=/var/www/html/george-jetson
ExecStart=/bin/bash /var/www/html/george-jetson/run.sh start
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable george-jetson-dashcam
sudo systemctl start george-jetson-dashcam
sudo systemctl status george-jetson-dashcam
```

## Docker Deployment

```bash
# Build and run with Docker (requires nvidia-docker)
docker-compose build
docker-compose up -d

# View logs
docker-compose logs -f dashcam

# Stop service
docker-compose down
```

## Security Considerations

⚠️ **Important**: These are development defaults. For production:

1. Change admin credentials in `utils.py`
2. Use HTTPS (install SSL certificate)
3. Run behind reverse proxy (nginx, Apache)
4. Restrict network access (firewall rules)
5. Use environment variables for sensitive data
6. Enable authentication on web endpoints
7. Sanitize database queries
8. Implement rate limiting

```python
# Production security example
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PREFERRED_URL_SCHEME'] = 'https'
```

## License

This project uses:
- OpenALPR (open source license)
- OpenCV (BSD license)
- PyTorch/TorchVision (BSD license)
- TensorRT (proprietary NVIDIA license)

See LICENSE file for details.

## Support & Documentation

- NVIDIA Jetson Orin Documentation: https://docs.nvidia.com/jetson/
- JetPack Documentation: https://docs.nvidia.com/jetpack/
- TensorRT Developer Guide: https://docs.nvidia.com/deeplearning/tensorrt/
- OpenCV with CUDA: https://docs.opencv.org/master/

## Changelog

### v1.0.0 (Initial Release)
- Full video recording with GPU acceleration
- GPS integration with smoothing
- AI vehicle detection with TensorRT
- SQLite event logging
- Flask web dashboard
- Disk cleanup management

## Contributing

Pull requests welcome! Please ensure:
- Code follows PEP 8 style guide
- All modules have docstrings
- Changes are tested on Jetson hardware
- Documentation is updated

## Authors

George Jetson Dashcam Development Team

---

**Disclaimer**: This software is provided as-is for educational and commercial use on NVIDIA Jetson platforms. Ensure compliance with local privacy laws before deploying vehicle recognition systems in production.
