#!/bin/bash

# George Jetson Dashcam - Complete Installation Guide
# This script automates the full setup process

set -e

PROJECT_HOME="/var/www/html/george-jetson"
JETPACK_VERSION="5.0"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
echo_success() { echo -e "${GREEN}[✓]${NC} $1"; }
echo_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
echo_error() { echo -e "${RED}[✗]${NC} $1"; }

# ============================================
# Step 1: Verify JetPack Installation
# ============================================

echo ""
echo_info "Step 1: Verifying JetPack installation..."

if ! command -v nvcc &> /dev/null; then
    echo_error "NVIDIA CUDA not found. Please install JetPack first."
    echo "Download from: https://developer.nvidia.com/jetpack"
    exit 1
fi

CUDA_VERSION=$(nvcc --version | grep release | awk '{print $(NF-1)}')
echo_success "CUDA found: $CUDA_VERSION"

if ! python3 -c "import tensorrt; print(tensorrt.__version__)" 2>/dev/null; then
    echo_warning "TensorRT not found. Some features may not work."
else
    TRT_VERSION=$(python3 -c "import tensorrt; print(tensorrt.__version__)")
    echo_success "TensorRT found: $TRT_VERSION"
fi

# ============================================
# Step 2: Install System Dependencies
# ============================================

echo ""
echo_info "Step 2: Installing system dependencies..."

sudo apt-get update
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    ffmpeg \
    libopencv-dev \
    python3-opencv \
    libsqlite3-dev \
    openalpr \
    openalpr-daemon \
    git \
    curl \
    wget \
    build-essential

echo_success "System dependencies installed"

# ============================================
# Step 3: Setup Project Directory
# ============================================

echo ""
echo_info "Step 3: Setting up project directory..."

# Determine the correct user (handle sudo invocation)
INSTALL_USER="${SUDO_USER:-$USER}"
if [ -z "$INSTALL_USER" ] || [ "$INSTALL_USER" = "root" ]; then
    echo_warning "Running as root. Please specify the user who will run the application:"
    read -p "Username: " INSTALL_USER
fi

echo_info "Installing for user: $INSTALL_USER"

sudo mkdir -p "$PROJECT_HOME"
sudo mkdir -p "$PROJECT_HOME/app"
sudo mkdir -p "$PROJECT_HOME/db"
sudo mkdir -p "$PROJECT_HOME/videos"
sudo mkdir -p "$PROJECT_HOME/models"
sudo mkdir -p "$PROJECT_HOME/logs"
sudo mkdir -p "$PROJECT_HOME/templates"
sudo mkdir -p "$PROJECT_HOME/static"

# Set ownership
sudo chown -R "$INSTALL_USER:$INSTALL_USER" "$PROJECT_HOME"

# Set restrictive permissions
# Root directory: owner can read/write/execute
chmod 750 "$PROJECT_HOME"
# App code: owner read/write, group/others read
chmod 755 "$PROJECT_HOME/app"
# Sensitive directories: owner only
chmod 700 "$PROJECT_HOME/db"
chmod 700 "$PROJECT_HOME/logs"
# Videos: owner read/write
chmod 750 "$PROJECT_HOME/videos"
# Models and templates: standard read
chmod 755 "$PROJECT_HOME/models"
chmod 755 "$PROJECT_HOME/templates"
chmod 755 "$PROJECT_HOME/static"

echo_success "Project directory created with secure permissions: $PROJECT_HOME"

# ============================================
# Step 4: Create Virtual Environment
# ============================================

echo ""
echo_info "Step 4: Creating Python virtual environment..."

cd "$PROJECT_HOME"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo_success "Virtual environment created"
fi

# Activate venv
source "$PROJECT_HOME/venv/bin/activate"

# Upgrade pip
pip install --upgrade pip setuptools wheel
echo_success "Python packages upgraded"

# ============================================
# Step 5: Install Python Dependencies
# ============================================

echo ""
echo_info "Step 5: Installing Python dependencies..."

pip install \
    numpy>=1.21.0 \
    opencv-python>=4.5.0 \
    pyserial>=3.5 \
    Flask>=2.0.0 \
    Pillow>=8.0.0 \
    requests>=2.25.0 \
    python-dateutil>=2.8.0

echo_success "Python dependencies installed"

# ============================================
# Step 6: Download AI Models
# ============================================

echo ""
echo_info "Step 6: Downloading AI models..."

# Create models directory
mkdir -p "$PROJECT_HOME/models/openalpr"
mkdir -p "$PROJECT_HOME/models/stanford_cars"

# Copy OpenALPR runtime data if available
if [ -d "/usr/share/openalpr/runtime_data" ]; then
    cp -r /usr/share/openalpr/runtime_data/* "$PROJECT_HOME/models/openalpr/" || true
    echo_success "OpenALPR models copied"
else
    echo_warning "OpenALPR runtime data not found"
fi

# Note: Stanford Cars model is loaded from torchvision
echo_info "Stanford Cars model will be downloaded on first run"

# ============================================
# Step 7: Configure Application
# ============================================

echo ""
echo_info "Step 7: Configuring application..."

# Create config file
cat > "$PROJECT_HOME/config.ini" << 'EOF'
[dashcam]
video_dir = /videos
db_path = /var/www/html/george-jetson/db/db.sqlite3
segment_duration = 300
video_width = 1920
video_height = 1080
video_fps = 30

[gps]
port = /dev/ttyUSB0
baudrate = 4800

[ai]
inference_fps = 5
confidence_threshold = 0.5

[web]
host = 0.0.0.0
port = 8089
admin_user = admin
admin_pass = admin
EOF

echo_success "Configuration file created"

# ============================================
# Step 8: Initialize Database
# ============================================

echo ""
echo_info "Step 8: Initializing database..."

python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/var/www/html/george-jetson/app')

from database import DatabaseManager

db = DatabaseManager()
stats = db.get_stats()
print(f"Database initialized successfully")
print(f"Stats: {stats}")
PYTHON_EOF

echo_success "Database initialized"

# ============================================
# Step 9: Test Components
# ============================================

echo ""
echo_info "Step 9: Testing components..."

echo ""
echo_info "Testing Python environment..."
python3 -c "
import sys
print(f'Python: {sys.version}')
print(f'Executable: {sys.executable}')
"

echo ""
echo_info "Testing OpenCV..."
python3 -c "
import cv2
print(f'OpenCV: {cv2.__version__}')
print(f'CUDA support: {cv2.cuda.getCudaEnabledDeviceCount()} devices')
" || echo_warning "OpenCV CUDA not available"

echo ""
echo_info "Testing database..."
python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/var/www/html/george-jetson/app')
from database import DatabaseManager
db = DatabaseManager()
print(f"Database OK")
PYTHON_EOF

echo ""
echo_info "Testing GPS module..."
python3 -c "
import sys
sys.path.insert(0, '/var/www/html/george-jetson/app')
from gps_reader import GPSReader
print('GPS module OK')
" || echo_warning "GPS module has dependency issues"

echo ""
echo_info "Testing Flask..."
python3 -c "
from flask import Flask
print(f'Flask OK')
"

echo_success "Component tests completed"

# ============================================
# Step 10: Create Startup Script
# ============================================

echo ""
echo_info "Step 10: Creating startup scripts..."

chmod +x "$PROJECT_HOME/run.sh"
echo_success "Startup script ready"

# ============================================
# Step 11: Verify GPU Setup
# ============================================

echo ""
echo_info "Step 11: Verifying GPU setup..."

python3 << 'PYTHON_EOF'
import subprocess

print("\n=== GPU Information ===")

# Check nvidia-smi
try:
    result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                          capture_output=True, text=True)
    print(f"GPU: {result.stdout.strip()}")
except:
    print("nvidia-smi: Not available")

# Check CUDA devices via Python
try:
    import cv2
    count = cv2.cuda.getCudaEnabledDeviceCount()
    print(f"CUDA devices: {count}")
    if count > 0:
        for i in range(count):
            name = cv2.cuda.Device(i).name()
            print(f"  Device {i}: {name}")
except Exception as e:
    print(f"CUDA check failed: {e}")

# Check TensorRT
try:
    import tensorrt as trt
    print(f"TensorRT: {trt.__version__}")
except:
    print("TensorRT: Not available")
PYTHON_EOF

# ============================================
# Step 12: Create Systemd Service (Optional)
# ============================================

echo ""
echo_info "Step 12: Creating systemd service (optional)..."

read -p "Create systemd service? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Get the home directory for the install user
    INSTALL_HOME=$(eval echo ~"$INSTALL_USER")
    
    sudo tee /etc/systemd/system/george-jetson-dashcam.service > /dev/null << EOF
[Unit]
Description=George Jetson Dashcam Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$INSTALL_USER
WorkingDirectory=$PROJECT_HOME
ExecStart=/bin/bash $PROJECT_HOME/run.sh start
Restart=always
RestartSec=10
Environment="HOME=$INSTALL_HOME"
Environment="FLASK_SECRET_KEY=$(openssl rand -hex 32)"
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    echo_success "Systemd service installed for user: $INSTALL_USER"
    echo_info "Service uses randomly generated Flask secret key"
    echo "Enable with: sudo systemctl enable george-jetson-dashcam"
    echo "Start with: sudo systemctl start george-jetson-dashcam"
fi

# ============================================
# Summary
# ============================================

echo ""
echo ""
echo_success "Installation Complete!"
echo ""
echo "Next steps:"
echo "1. Edit configuration: $PROJECT_HOME/app/utils.py"
echo "2. Verify GPS connection: ls -la /dev/ttyUSB*"
echo "3. Test application:"
echo "   cd $PROJECT_HOME"
echo "   source venv/bin/activate"
echo "   python3 app/main.py --web-only"
echo "4. Access web dashboard: http://localhost:8089"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "Or use startup script:"
echo "   $PROJECT_HOME/run.sh start"
echo ""
echo ""
echo_warning "⚠️  SECURITY RECOMMENDATIONS FOR PRODUCTION:"
echo "1. CHANGE DEFAULT CREDENTIALS immediately!"
echo "   Edit app/utils.py and update ADMIN_USER and ADMIN_PASS"
echo ""
echo "2. USE HTTPS with a reverse proxy (nginx/Apache)"
echo "   The web server is exposed on 0.0.0.0 (all interfaces)"
echo ""
echo "3. SET FLASK_SECRET_KEY environment variable"
echo "   export FLASK_SECRET_KEY=\$(openssl rand -hex 32)"
echo ""
echo "4. CONFIGURE FIREWALL to restrict access to port 8089"
echo "   sudo ufw allow from TRUSTED_IP to any port 8089"
echo ""
echo "5. REVIEW LOGS regularly: $PROJECT_HOME/logs/dashcam.log"
echo ""
echo "For more information, see: $PROJECT_HOME/README.md"
echo ""
