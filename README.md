# Human Detection System

A real-time human detection system using YOLO (You Only Look Once) object detection with OpenCV and Ultralytics.

## 🎯 Features

- **Real-time human detection** using YOLOv8 model
- **Multi-camera support** - automatically detects available cameras
- **Debug mode** - shows exactly what objects are being detected
- **GPIO integration ready** - includes commented GPIO code for Raspberry Pi
- **Works without camera** - includes test image generation for debugging

## 📋 Requirements

### Hardware
- **Camera**: Logitech Brio 101 (recommended) or any USB webcam
- **Optional**: Raspberry Pi with GPIO pins for LED control

### Software
- Python 3.8+
- OpenCV
- Ultralytics YOLO
- NumPy

## 🚀 Installation

### 1. Install Required Packages
```bash
pip3 install --break-system-packages opencv-python ultralytics numpy
```

### 2. Camera Permissions (Linux)
If using a webcam, add your user to the video group:
```bash
sudo usermod -a -G video $USER
# Log out and back in for changes to take effect
```

### 3. Download YOLO Model
The `yolov8n.pt` model file should be in the project directory.

## 📁 Files Overview

| File | Description |
|------|-------------|
| `test.py` | Original code with GPIO integration (commented out) |
| `detector.py` | Full version with GPIO support for Raspberry Pi |
| `final_working_version.py` | Complete working solution with test images |
| `camera_specific_version.py` | Tests all available cameras (limited to 100 frames) |
| `camera_specific_version_fixed.py` | **Recommended** - Tests cameras continuously |
| `debug_detection.py` | Debug tool to see what YOLO detects |
| `test_fixed.py` | Alternative version that works without camera |
| `yolov8n.pt` | YOLO model file (pre-trained) |

## 🎮 Usage

### Quick Start
```bash
# Run the complete working version
python3 final_working_version.py

# Test all cameras (recommended)
python3 camera_specific_version_fixed.py
```

### Camera Testing
The camera-specific version will:
1. **List all available cameras** on your system
2. **Test each camera** automatically
3. **Show detection results** in real-time
4. **Display console output** with detailed information

### Key Camera Indices
- **`/dev/video0`** - Intel MIPI Camera (Built-in desktop camera)
- **`/dev/video49`** - Logitech Brio 101 (USB webcam) ✅ **Recommended**
- **`/dev/video50`** - Logitech Brio 101 (Alternative - usually fails)

## 🔧 Configuration

### Using Your Logitech Webcam
Change the camera index in any script:
```python
# From (built-in camera):
cap = cv2.VideoCapture(0)

# To (Logitech webcam):
cap = cv2.VideoCapture(49)
```

### GPIO Integration (Raspberry Pi)
Uncomment the GPIO lines in `detector.py`:
```python
import RPi.GPIO as GPIO

LED_PIN = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)

# In the detection loop:
if human_detected:
    GPIO.output(LED_PIN, GPIO.HIGH)  # LED ON
else:
    GPIO.output(LED_PIN, GPIO.LOW)   # LED OFF
```

## 🐛 Troubleshooting

### Common Issues

#### 1. "Cannot open camera"
```
❌ Cannot open camera - this is expected if no webcam is connected
```
**Solution**: Connect a USB webcam or use test image mode.

#### 2. Permission Denied
```
[video4linux2,v4l2 @ 0x...] Cannot open video device /dev/videoX: Permission denied
```
**Solution**: Add user to video group:
```bash
sudo usermod -a -G video $USER
```

#### 3. ModuleNotFoundError: No module named 'cv2'
**Solution**: Install OpenCV:
```bash
pip3 install opencv-python
```

#### 4. Always detecting humans when no one is there
**Solution**: Point camera at a blank wall or use test images to verify detection logic.

### Camera Selection
Your code currently uses `/dev/video0` (built-in camera), but your **Logitech Brio 101** is at `/dev/video49`. Use the camera-specific version to test which works best.

## 📊 Detection Output

### Console Output
```
✅ HUMAN DETECTED! (1 total objects)
❌ No human detected (2 total objects)
   Detected: kite: 0.73, person: 0.45
```

### On-Screen Display
- **Green boxes** around detected humans
- **Red text** showing "HUMAN" or "NO HUMAN"
- **White text** showing all detected objects

## 🔍 Debug Tools

### Debug Detection
```bash
python3 debug_detection.py
```
Shows exactly what objects YOLO detects in test images.

### Camera Testing
```bash
python3 camera_specific_version_fixed.py
```
Tests all cameras and shows which one works best.

## 📐 Technical Details

### YOLO Model
- **Model**: YOLOv8n (nano version - fast and lightweight)
- **Classes**: 80 object classes including "person"
- **Confidence**: Objects detected with confidence > 0.5

### Performance
- **Frame Rate**: ~30 FPS (depends on hardware)
- **Detection Speed**: ~50ms per frame
- **Accuracy**: High accuracy for human detection

### Camera Specifications
- **Logitech Brio 101**: 4K UHD, excellent for computer vision
- **Intel MIPI**: Built-in laptop/desktop camera
- **Virtual Cameras**: Software-generated camera streams

## 🤖 Advanced Usage

### Custom Detection Thresholds
Modify confidence threshold in any script:
```python
if confidence > 0.7:  # Only detect with 70%+ confidence
    # Process detection
```

### Multiple Object Detection
The system can detect all 80 YOLO classes, not just humans:
```python
if class_name in ["person", "car", "dog"]:  # Detect multiple objects
    # Process detection
```

### Video Recording
Add video recording to any script:
```python
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter('output.avi', fourcc, 20.0, (640, 480))

# In the loop:
out.write(frame)

# At the end:
out.release()
```

## 📝 License

This project is open source and available under the MIT License.

## 🤝 Contributing

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 Support

For questions or support:
- Check the troubleshooting section above
- Review the debug tools
- Test with different cameras
- Verify camera permissions

## 🙏 Acknowledgments

- **Ultralytics** for the excellent YOLO implementation
- **OpenCV** for powerful computer vision tools
- **Logitech** for high-quality webcams