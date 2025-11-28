#!/bin/bash

# George Jetson Dashcam - Startup Script
# Run with: ./run.sh [options]

set -e

PROJECT_DIR="/var/www/html/george-jetson"
APP_DIR="$PROJECT_DIR/app"
VENV_DIR="$PROJECT_DIR/venv"
LOG_FILE="$PROJECT_DIR/logs/dashcam.log"
PID_FILE="/var/run/george-jetson-dashcam.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

check_dependencies() {
    print_info "Checking dependencies..."
    
    # Check for Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found"
        exit 1
    fi
    print_info "Python 3 found: $(python3 --version)"
    
    # Check for FFmpeg
    if ! command -v ffmpeg &> /dev/null; then
        print_warning "FFmpeg not found - video encoding may not work"
    else
        print_info "FFmpeg found: $(ffmpeg -version | head -1)"
    fi
    
    # Check for CUDA (optional)
    if ! command -v nvcc &> /dev/null; then
        print_warning "CUDA not found - GPU acceleration unavailable"
    else
        print_info "CUDA found: $(nvcc --version | grep release)"
    fi
}

setup_venv() {
    print_info "Setting up Python virtual environment..."
    
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
        print_info "Virtual environment created"
    fi
    
    source "$VENV_DIR/bin/activate"
    print_info "Virtual environment activated"
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    # Install requirements
    print_info "Installing dependencies..."
    if [ -f "$PROJECT_DIR/requirements.txt" ]; then
        pip install -r "$PROJECT_DIR/requirements.txt"
        print_info "Dependencies installed"
    else
        print_warning "requirements.txt not found"
    fi
}

setup_directories() {
    print_info "Setting up directories..."
    
    mkdir -p "$PROJECT_DIR/videos"
    mkdir -p "$PROJECT_DIR/db"
    mkdir -p "$PROJECT_DIR/logs"
    mkdir -p "$PROJECT_DIR/models"
    mkdir -p "$PROJECT_DIR/templates"
    mkdir -p "$PROJECT_DIR/static"
    
    # Ensure permissions
    chmod 755 "$PROJECT_DIR/videos"
    chmod 755 "$PROJECT_DIR/db"
    chmod 755 "$PROJECT_DIR/logs"
    
    print_info "Directories ready"
}

start_dashcam() {
    print_info "Starting George Jetson Dashcam..."
    
    source "$VENV_DIR/bin/activate"
    
    cd "$APP_DIR"
    
    # Parse command line arguments
    ARGS=""
    if [ "$1" == "web-only" ]; then
        print_info "Starting web server only (no recording)"
        ARGS="--web-only"
    elif [ "$1" == "no-web" ]; then
        print_info "Starting recording only (no web server)"
        ARGS="--no-web"
    elif [ "$1" == "debug" ]; then
        print_info "Starting in debug mode"
        ARGS="--debug"
    fi
    
    # Start application
    if [ -n "$ARGS" ]; then
        python3 main.py $ARGS
    else
        python3 main.py
    fi
}

stop_dashcam() {
    print_info "Stopping George Jetson Dashcam..."
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            print_info "Application stopped (PID: $PID)"
            rm "$PID_FILE"
        fi
    else
        print_warning "No PID file found"
    fi
}

show_help() {
    echo "George Jetson Dashcam - Startup Script"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  start               Start the dashcam application (default)"
    echo "  stop                Stop the dashcam application"
    echo "  setup               Setup dependencies and directories"
    echo "  web-only            Start web server only (no recording)"
    echo "  no-web              Start recording only (no web server)"
    echo "  debug               Start in debug mode"
    echo "  status              Show application status"
    echo "  logs                Show application logs"
    echo "  help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run.sh start                # Start normal recording"
    echo "  ./run.sh web-only            # Start web server only"
    echo "  ./run.sh setup               # Install dependencies"
    echo "  ./run.sh logs                # View logs"
}

show_status() {
    print_info "George Jetson Dashcam Status"
    print_info "Project directory: $PROJECT_DIR"
    print_info "Virtual environment: $VENV_DIR"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            print_info "Status: RUNNING (PID: $PID)"
            return 0
        fi
    fi
    
    print_warning "Status: NOT RUNNING"
    return 1
}

show_logs() {
    if [ -f "$LOG_FILE" ]; then
        print_info "Last 50 log entries:"
        tail -50 "$LOG_FILE"
    else
        print_warning "Log file not found: $LOG_FILE"
    fi
}

# Main script
print_info "George Jetson Dashcam"
print_info "Project: $PROJECT_DIR"

case "${1:-start}" in
    start)
        check_dependencies
        setup_directories
        setup_venv
        start_dashcam "${2:-}"
        ;;
    stop)
        stop_dashcam
        ;;
    setup)
        check_dependencies
        setup_directories
        setup_venv
        print_info "Setup complete!"
        ;;
    web-only)
        check_dependencies
        setup_directories
        setup_venv
        start_dashcam "web-only"
        ;;
    no-web)
        check_dependencies
        setup_directories
        setup_venv
        start_dashcam "no-web"
        ;;
    debug)
        check_dependencies
        setup_directories
        setup_venv
        start_dashcam "debug"
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    help)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
