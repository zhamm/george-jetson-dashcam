# Installation Path Update

**Date:** November 27, 2025

## Change Summary

Updated the default installation path from `/var/www/html/george-jetson` to `/opt/george-jetson`.

### Reason for Change

- `/var/www/html` is specifically for web server content (Apache/nginx)
- This application is a standalone service, not a web application served by Apache
- `/opt` is the standard Linux directory for optional/third-party software
- Apache may not even be installed on Jetson devices
- Follows Linux Filesystem Hierarchy Standard (FHS)

### Files Updated

All references updated across:
- ✅ Python source code (`app/*.py`)
- ✅ Shell scripts (`INSTALL.sh`, `run.sh`)
- ✅ Configuration files (`config.ini`, `docker-compose.yml`)
- ✅ Documentation (`*.md`)
- ✅ Test files (`tests/*.py`)
- ✅ Utility scripts (`*.py`)

**Total files updated:** 30+

### New Installation Location

```
/opt/george-jetson/
├── app/                    # Application code
├── db/                     # SQLite database
├── videos/                 # Video recordings
├── models/                 # AI models
├── logs/                   # Application logs
├── templates/              # Web templates
├── static/                 # Web assets
└── tests/                  # Test suite
```

### Installation Commands (Updated)

#### New Installation
```bash
# Clone to /opt directory
cd /opt
sudo git clone https://github.com/zhamm/george-jetson-dashcam.git george-jetson
cd george-jetson

# Set ownership
sudo chown -R $USER:$USER /opt/george-jetson

# Run installation
sudo bash INSTALL.sh
```

#### Migrating Existing Installation

If you have an existing installation at `/var/www/html/george-jetson`:

```bash
# Stop service if running
sudo systemctl stop george-jetson-dashcam

# Move installation
sudo mv /var/www/html/george-jetson /opt/george-jetson

# Update systemd service
sudo sed -i 's|/var/www/html/george-jetson|/opt/george-jetson|g' /etc/systemd/system/george-jetson-dashcam.service
sudo systemctl daemon-reload

# Restart service
sudo systemctl start george-jetson-dashcam
```

### Configuration Updates

All default paths now use `/opt/george-jetson`:

```python
# app/utils.py
DEFAULT_CONFIG = {
    'VIDEO_DIR': '/videos',
    'DB_PATH': '/opt/george-jetson/db/db.sqlite3',
    # ...
}
```

```bash
# INSTALL.sh
PROJECT_HOME="/opt/george-jetson"
```

```ini
# config.ini
path = /opt/george-jetson/db/db.sqlite3
log_file = /opt/george-jetson/logs/dashcam.log
```

### No Breaking Changes

- Application functionality unchanged
- All features work identically
- Only installation path modified
- Existing data can be migrated

### Benefits

1. **Standards Compliant** - Follows Linux FHS
2. **No Apache Dependency** - Works standalone
3. **Clearer Purpose** - Dedicated application directory
4. **Better Isolation** - Not mixed with web server files
5. **Professional Structure** - Industry standard for services

### Verification

Check installation path:
```bash
# Verify files are in /opt
ls -la /opt/george-jetson/

# Check service configuration
sudo systemctl cat george-jetson-dashcam | grep WorkingDirectory
# Should show: WorkingDirectory=/opt/george-jetson
```

### Documentation Updated

All documentation now reflects `/opt/george-jetson`:
- ✅ README.md
- ✅ INSTALL.sh
- ✅ All markdown documentation files
- ✅ Code comments
- ✅ Configuration examples
- ✅ Test suite

---

**This change makes the installation location more appropriate and follows Linux best practices.**
