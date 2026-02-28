#!/bin/bash
# Simple Raspberry Pi Security System Setup
# =========================================
# This is a straightforward setup that doesn't rely on complex paths

echo "🚨 Simple Raspberry Pi Security System Setup"
echo "============================================"
echo

# Update system
echo "📦 Updating system..."
sudo apt update && sudo apt full-upgrade -y

# Install dependencies
echo "🔧 Installing dependencies..."
sudo apt install -y python3-pip python3-opencv python3-numpy python3-rpi.gpio v4l-utils ffmpeg

# Install Python packages
echo "🐍 Installing Python packages..."
pip3 install --break-system-packages ultralytics requests opencv-python numpy

# Create project directory
echo "📁 Creating project directory..."
mkdir -p ~/security_system

# Copy files (assuming they're in /home/pi/)
echo "📋 Copying files to project directory..."
if [ -f "/home/pi/raspberry_pi_security_system.py" ]; then
    cp /home/pi/raspberry_pi_security_system.py ~/security_system/
    echo "✅ Main system file copied"
else
    echo "⚠️  Main system file not found in /home/pi/"
    echo "   Make sure you copied raspberry_pi_security_system.py to /home/pi/"
fi

if [ -f "/home/pi/yolov8n.pt" ]; then
    cp /home/pi/yolov8n.pt ~/security_system/
    echo "✅ YOLO model copied"
else
    echo "⚠️  YOLO model not found in /home/pi/"
    echo "   Make sure you copied yolov8n.pt to /home/pi/"
fi

# Create a simple test script
echo "📹 Creating simple test script..."
cat > ~/security_system/simple_test.py << 'EOF'
#!/usr/bin/env python3
"""
Simple test to verify the system works
"""

import cv2
from ultralytics import YOLO
import time

def main():
    print("📹 Simple Camera Test")
    print("=" * 20)
    
    # Load model
    try:
        model = YOLO("yolov8n.pt")
        print("✅ YOLO model loaded")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return
    
    # Test camera
    cap = cv2.VideoCapture(49)  # Logitech Brio 101
    if not cap.isOpened():
        print("❌ Cannot open camera at index 49")
        # Try index 0
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot open camera at index 0")
            return
        else:
            print("✅ Using camera at index 0")
    else:
        print("✅ Using camera at index 49 (Logitech Brio 101)")
    
    print("📸 Testing detection for 5 seconds...")
    
    start_time = time.time()
    while time.time() - start_time < 5:
        ret, frame = cap.read()
        if ret:
            # Run detection
            results = model(frame, verbose=False)
            
            # Check for people
            for result in results:
                for box in result.boxes:
                    cls = int(box.cls[0])
                    confidence = float(box.conf[0])
                    class_name = model.names[cls]
                    
                    if class_name == 'person' and confidence > 0.5:
                        print(f"🚨 PERSON DETECTED! Confidence: {confidence:.2f}")
                        break
            
            cv2.imshow("Test Feed", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    cap.release()
    cv2.destroyAllWindows()
    print("✅ Test completed!")

if __name__ == "__main__":
    main()
EOF

chmod +x ~/security_system/simple_test.py

# Create a simple run script
echo "🚀 Creating simple run script..."
cat > ~/security_system/run_system.py << 'EOF'
#!/usr/bin/env python3
"""
Simple script to run the security system
"""

import os
import sys

# Change to the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Add current directory to Python path
sys.path.insert(0, script_dir)

# Run the main system
try:
    import raspberry_pi_security_system
    print("🚨 Starting Security System...")
    raspberry_pi_security_system.main()
except ImportError as e:
    print(f"❌ Error importing main system: {e}")
    print("Make sure raspberry_pi_security_system.py is in the same directory")
except Exception as e:
    print(f"❌ Error running system: {e}")
EOF

chmod +x ~/security_system/run_system.py

# Create a GPIO test script
echo "🔌 Creating GPIO test script..."
cat > ~/security_system/test_gpio.py << 'EOF'
#!/usr/bin/env python3
"""
Test GPIO buzzer connection
"""

import RPi.GPIO as GPIO
import time

def main():
    print("🔌 GPIO Buzzer Test")
    print("=" * 20)
    
    # Setup GPIO
    GPIO.setmode(GPIO.BCM)
    BUZZER_PIN = 18
    
    try:
        GPIO.setup(BUZZER_PIN, GPIO.OUT)
        print("✅ GPIO pin 18 configured as output")
        
        print("🔊 Testing buzzer for 2 seconds...")
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(2)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        print("✅ Buzzer test completed")
        
    except Exception as e:
        print(f"❌ GPIO test failed: {e}")
        print("Make sure you're running this on a Raspberry Pi with proper permissions")
    
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
EOF

chmod +x ~/security_system/test_gpio.py

echo
echo "✅ Setup complete!"
echo
echo "📁 Files created in ~/security_system/:"
echo "   • simple_test.py - Test camera and detection"
echo "   • run_system.py - Run the main security system"
echo "   • test_gpio.py - Test buzzer connection"
echo
echo "🚀 Next steps:"
echo "   1. cd ~/security_system"
echo "   2. python3 simple_test.py (test camera and detection)"
echo "   3. python3 test_gpio.py (test buzzer)"
echo "   4. python3 run_system.py (run full system)"
echo
echo "💡 Make sure you have:"
echo "   • raspberry_pi_security_system.py in /home/pi/"
echo "   • yolov8n.pt in /home/pi/"
echo "   • Buzzer connected to GPIO pin 18"
echo "   • Logitech Brio 101 camera connected"