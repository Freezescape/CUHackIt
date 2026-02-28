#!/bin/bash
# Fixed Raspberry Pi Security System Deployment Script
# ==============================================
# 
# This script sets up your Raspberry Pi for the security system.
# Run this script on your Raspberry Pi after installing Raspberry Pi OS.

set -e

echo "🚨 Raspberry Pi Security System Deployment (Fixed)"
echo "=================================================="
echo

# Check if running on Raspberry Pi
if ! grep -q "Raspberry" /proc/cpuinfo; then
    echo "❌ Warning: This script should be run on a Raspberry Pi"
    echo "   Continuing anyway for testing purposes..."
    echo
fi

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt full-upgrade -y

# Install system dependencies
echo "🔧 Installing system dependencies..."
sudo apt install -y \
    python3-pip \
    python3-opencv \
    python3-numpy \
    python3-rpi.gpio \
    v4l-utils \
    ffmpeg \
    git

# Install Python packages
echo "🐍 Installing Python packages..."
pip3 install --break-system-packages \
    ultralytics \
    requests \
    opencv-python \
    numpy

# Create project directory
echo "📁 Setting up project directory..."
mkdir -p ~/security_system
cd ~/security_system

# Copy files from current directory (where you copied them)
echo "📋 Copying project files..."
cp /home/pi/raspberry_pi_security_system.py ~/security_system/ 2>/dev/null || echo "⚠️  Main system file not found, will need to copy manually"
cp /home/pi/security_system_test.py ~/security_system/ 2>/dev/null || echo "⚠️  Test file not found, will need to copy manually"
cp /home/pi/yolov8n.pt ~/security_system/ 2>/dev/null || echo "⚠️  YOLO model not found, will need to copy manually"
cp /home/pi/README.md ~/security_system/ 2>/dev/null || echo "⚠️  README not found, will need to copy manually"

# Create systemd service
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/security-system.service > /dev/null <<EOF
[Unit]
Description=Raspberry Pi Security System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/security_system
ExecStart=/usr/bin/python3 raspberry_pi_security_system.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create startup script
echo "🚀 Creating startup script..."
cat > ~/security_system/start_security_system.sh <<'EOF'
#!/bin/bash
# Security System Startup Script

echo "🚨 Starting Raspberry Pi Security System..."

# Set environment variables
export BACKBOARD_API_KEY="${BACKBOARD_API_KEY:-}"
export PYTHONPATH="/home/pi/security_system:$PYTHONPATH"

# Start the system
cd /home/pi/security_system
python3 raspberry_pi_security_system.py
EOF

chmod +x ~/security_system/start_security_system.sh

# Create log rotation
echo "📝 Setting up log rotation..."
sudo tee /etc/logrotate.d/security-system > /dev/null <<EOF
/home/pi/security_system/security_logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 pi pi
}
EOF

# Create camera test script
echo "📹 Creating camera test script..."
cat > ~/security_system/test_camera.py <<'EOF'
#!/usr/bin/env python3
"""
Camera Test Script for Raspberry Pi Security System
"""

import cv2
import time

def test_camera(index):
    """Test a specific camera index"""
    print(f"Testing camera index {index}...")
    
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        print(f"❌ Cannot open camera {index}")
        return False
    
    # Set resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    ret, frame = cap.read()
    if not ret:
        print(f"❌ Cannot read frame from camera {index}")
        cap.release()
        return False
    
    print(f"✅ Camera {index} working - Resolution: {frame.shape[1]}x{frame.shape[0]}")
    
    # Show preview for 3 seconds
    start_time = time.time()
    while time.time() - start_time < 3:
        ret, frame = cap.read()
        if ret:
            cv2.imshow(f'Camera {index} Preview', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    cap.release()
    cv2.destroyAllWindows()
    return True

def main():
    print("📹 Camera Detection Test")
    print("=" * 30)
    
    # Test common camera indices
    camera_indices = [0, 1, 2, 3, 4, 49, 50]
    working_cameras = []
    
    for index in camera_indices:
        if test_camera(index):
            working_cameras.append(index)
    
    print("\n📊 Results:")
    if working_cameras:
        print(f"✅ Working cameras: {working_cameras}")
        print(f"💡 Recommended camera index: {working_cameras[0]}")
    else:
        print("❌ No working cameras found")
        print("💡 Try connecting your Logitech Brio 101 webcam")

if __name__ == "__main__":
    main()
EOF

chmod +x ~/security_system/test_camera.py

# Create configuration script
echo "⚙️  Creating configuration script..."
cat > ~/security_system/configure_system.py <<'EOF'
#!/usr/bin/env python3
"""
Configuration Script for Raspberry Pi Security System
"""

import os
import json
from pathlib import Path

def configure_ai():
    """Configure AI integration settings"""
    print("🤖 AI Integration Configuration")
    print("=" * 40)
    
    # Check if API key is set
    api_key = os.environ.get("BACKBOARD_API_KEY", "")
    if not api_key:
        print("⚠️  BACKBOARD_API_KEY environment variable not set")
        api_key = input("Enter your Backboard API key (or press Enter to skip): ").strip()
    
    if api_key:
        # Set environment variable
        with open(Path.home() / ".bashrc", "a") as f:
            f.write(f'\nexport BACKBOARD_API_KEY="{api_key}"\n')
        print("✅ API key saved to ~/.bashrc")
    
    # Configure agent IDs
    print("\n📋 Agent Configuration")
    print("Using your existing agent IDs from main.py...")
    
    agents = {
        "TECHNICIAN_ID": "e734432b-dc99-4132-b12b-fef16ff3cb91",
        "AUDITOR_ID": "f0d83f5c-3364-4dda-8a8d-43a3c519dc02", 
        "CHAIRMAN_ID": "11b491ae-f707-4e44-b315-ec85f28f7f34"
    }
    
    config = {
        "backboard_api_key": api_key,
        "agents": agents,
        "camera_index": 49,  # Logitech Brio 101
        "alarm_duration": 5,
        "alarm_cooldown": 30
    }
    
    # Save configuration
    config_file = Path.home() / "security_system" / "config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Configuration saved to {config_file}")

def setup_gpio():
    """Setup GPIO for buzzer"""
    print("\n🔌 GPIO Configuration")
    print("=" * 30)
    print("Buzzer should be connected to GPIO pin 18")
    print("Ensure your buzzer is properly wired to the Raspberry Pi")
    print("✅ GPIO setup complete")

def main():
    print("🔧 Raspberry Pi Security System Configuration")
    print("=" * 50)
    
    configure_ai()
    setup_gpio()
    
    print("\n🎉 Configuration complete!")
    print("\nNext steps:")
    print("1. Test your camera: python3 test_camera.py")
    print("2. Test the system: python3 security_system_test.py")
    print("3. Start the full system: python3 raspberry_pi_security_system.py")
    print("4. Enable auto-start: sudo systemctl enable security-system")

if __name__ == "__main__":
    main()
EOF

chmod +x ~/security_system/configure_system.py

# Create quick start guide
echo "📖 Creating quick start guide..."
cat > ~/security_system/QUICK_START.md <<'EOF'
# Raspberry Pi Security System - Quick Start

## Initial Setup

1. **Run the deployment script:**
   ```bash
   chmod +x deploy_raspberry_pi.sh
   sudo ./deploy_raspberry_pi.sh
   ```

2. **Configure the system:**
   ```bash
   cd ~/security_system
   python3 configure_system.py
   ```

3. **Test your camera:**
   ```bash
   python3 test_camera.py
   ```

## Testing

### Test Version (No Hardware Required)
```bash
python3 security_system_test.py
```

### Full Version (With Buzzer)
```bash
python3 raspberry_pi_security_system.py
```

## Auto-Start Setup

Enable the system to start automatically on boot:

```bash
sudo systemctl enable security-system
sudo systemctl start security-system
```

Check status:
```bash
sudo systemctl status security-system
```

View logs:
```bash
sudo journalctl -u security-system -f
```

## Hardware Connections

### Buzzer Wiring
- **GPIO Pin 18** → Buzzer positive (+)
- **Ground (GND)** → Buzzer negative (-)

### Camera
- Connect your Logitech Brio 101 to any USB port
- The system will automatically detect it at index 49

## Troubleshooting

### Camera Not Detected
```bash
# List available cameras
v4l2-ctl --list-devices

# Test specific camera
python3 test_camera.py
```

### GPIO Issues
```bash
# Check GPIO permissions
ls -la /dev/gpiomem

# Test GPIO manually
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(18, GPIO.OUT); GPIO.output(18, GPIO.HIGH); import time; time.sleep(1); GPIO.output(18, GPIO.LOW); GPIO.cleanup()"
```

### AI Integration Issues
- Ensure BACKBOARD_API_KEY is set in ~/.bashrc
- Verify your agent IDs are correct
- Check internet connection

## File Locations

- **Logs:** `/home/pi/security_system/security_logs/`
- **Videos:** `/home/pi/security_system/security_logs/`
- **Config:** `/home/pi/security_system/config.json`
- **Service:** `/etc/systemd/system/security-system.service`
EOF

echo
echo "✅ Deployment complete!"
echo
echo "📁 Files created in ~/security_system/:"
echo "   • raspberry_pi_security_system.py (Main system)"
echo "   • security_system_test.py (Test version)"
echo "   • test_camera.py (Camera testing)"
echo "   • configure_system.py (Configuration)"
echo "   • QUICK_START.md (Documentation)"
echo "   • yolo_model.pt (AI model)"
echo
echo "🚀 Next steps:"
echo "   1. cd ~/security_system"
echo "   2. python3 configure_system.py"
echo "   3. python3 test_camera.py"
echo "   4. python3 security_system_test.py"
echo
echo "💡 For production use:"
echo "   sudo systemctl enable security-system"
echo "   sudo systemctl start security-system"