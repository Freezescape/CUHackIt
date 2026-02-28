#!/usr/bin/env python3
"""
ONNX-based Security System for Raspberry Pi
===========================================

This version uses ONNX Runtime instead of PyTorch, eliminating the "illegal instruction" errors.
Perfect for Raspberry Pi ARM architecture!

Features:
- Real-time human detection using ONNX model
- Buzzer alarm when human detected in restricted zone
- Automatic recording and logging of events
- No PyTorch required - uses ONNX Runtime (ARM-compatible)

Hardware Setup:
- Camera: Logitech Brio 101 (or any USB webcam)
- Buzzer: Active buzzer connected to GPIO pin 18
- Raspberry Pi: Any model with GPIO pins

Installation:
1. pip3 install opencv-python numpy onnxruntime
2. sudo apt install python3-rpi.gpio
3. Copy yolov8n.onnx to the same directory
4. Run: python3 onnx_security_system.py
"""

import cv2
import numpy as np
import onnxruntime as ort
import RPi.GPIO as GPIO
import time
import threading
import json
import logging
from datetime import datetime
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
# GPIO Setup
BUZZER_PIN = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.output(BUZZER_PIN, GPIO.LOW)

# Camera Setup
CAMERA_INDEX = 49  # Logitech Brio 101
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# Detection Settings
CONFIDENCE_THRESHOLD = 0.5
ALARM_DURATION = 5  # seconds
ALARM_COOLDOWN = 30  # seconds between alarms
IOU_THRESHOLD = 0.5  # Non-maximum suppression threshold

# File Paths
LOG_DIR = Path("security_logs")
LOG_DIR.mkdir(exist_ok=True)
ONNX_MODEL_PATH = "yolov8n.onnx"

# YOLO Model Configuration
CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake",
    "chair", "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop",
    "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
]

# ── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'onnx_security_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ── ONNX Model Class ──────────────────────────────────────────────────────────
class ONNXDetector:
    def __init__(self, model_path):
        self.session = ort.InferenceSession(model_path)
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [output.name for output in self.session.get_outputs()]
        
        # Get model input shape
        input_shape = self.session.get_inputs()[0].shape
        self.input_height = input_shape[2]
        self.input_width = input_shape[3]
        
        logger.info(f"✅ ONNX model loaded: {model_path}")
        logger.info(f"   Input shape: {input_shape}")
    
    def preprocess(self, frame):
        """Preprocess frame for ONNX model"""
        # Resize to model input size
        resized = cv2.resize(frame, (self.input_width, self.input_height))
        
        # Convert to RGB and normalize
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        normalized = rgb.astype(np.float32) / 255.0
        
        # Add batch dimension and transpose to CHW format
        input_tensor = np.transpose(normalized, (2, 0, 1))
        input_tensor = np.expand_dims(input_tensor, axis=0)
        
        return input_tensor
    
    def postprocess(self, outputs, original_shape):
        """Postprocess ONNX model outputs"""
        # ONNX output format: [batch, num_detections, 85]
        # 85 = 4 (bbox) + 1 (confidence) + 80 (class probabilities)
        
        detections = outputs[0]  # Get first batch
        
        boxes = []
        scores = []
        class_ids = []
        
        for detection in detections:
            confidence = detection[4]
            if confidence > CONFIDENCE_THRESHOLD:
                # Get class with highest probability
                class_probs = detection[5:]
                class_id = np.argmax(class_probs)
                class_score = class_probs[class_id]
                
                # Overall confidence = object confidence * class confidence
                overall_confidence = confidence * class_score
                
                if overall_confidence > CONFIDENCE_THRESHOLD:
                    # Get bounding box coordinates
                    x_center, y_center, width, height = detection[:4]
                    
                    # Convert to corner coordinates
                    x1 = int((x_center - width / 2) * original_shape[1] / self.input_width)
                    y1 = int((y_center - height / 2) * original_shape[0] / self.input_height)
                    x2 = int((x_center + width / 2) * original_shape[1] / self.input_width)
                    y2 = int((y_center + height / 2) * original_shape[0] / self.input_height)
                    
                    boxes.append([x1, y1, x2, y2])
                    scores.append(overall_confidence)
                    class_ids.append(class_id)
        
        # Apply non-maximum suppression
        indices = cv2.dnn.NMSBoxes(boxes, scores, CONFIDENCE_THRESHOLD, IOU_THRESHOLD)
        
        results = []
        if len(indices) > 0:
            for i in indices.flatten():
                results.append({
                    'class': CLASSES[class_ids[i]],
                    'confidence': float(scores[i]),
                    'bbox': boxes[i]
                })
        
        return results

# ── Security System Class ─────────────────────────────────────────────────────
class ONNXSecuritySystem:
    def __init__(self):
        self.detector = ONNXDetector(ONNX_MODEL_PATH)
        self.is_active = False
        self.last_alarm_time = 0
        self.detection_history = []
        
        # Video recording
        self.recording = False
        self.video_writer = None
        self.video_start_time = None
        
        logger.info("ONNX Security System initialized")
    
    def start(self):
        """Start the security system"""
        self.is_active = True
        logger.info("🚨 ONNX Security System Activated")
        
        # Start camera thread
        camera_thread = threading.Thread(target=self._camera_loop, daemon=True)
        camera_thread.start()
        
        try:
            while self.is_active:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 ONNX Security System Stopped by User")
            self.stop()
    
    def stop(self):
        """Stop the security system"""
        self.is_active = False
        self._stop_recording()
        GPIO.cleanup()
        logger.info("ONNX Security System Stopped")
    
    def _camera_loop(self):
        """Main camera processing loop"""
        cap = cv2.VideoCapture(CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        
        if not cap.isOpened():
            logger.error(f"❌ Cannot open camera at index {CAMERA_INDEX}")
            return
        
        logger.info(f"📹 Camera started (Index: {CAMERA_INDEX})")
        
        while self.is_active:
            ret, frame = cap.read()
            if not ret:
                logger.warning("⚠️  Cannot read frame from camera")
                time.sleep(1)
                continue
            
            # Run detection
            input_tensor = self.detector.preprocess(frame)
            outputs = self.detector.session.run(self.detector.output_names, {self.detector.input_name: input_tensor})
            detections = self.detector.postprocess(outputs, frame.shape)
            
            # Check for human detection
            if any(d['class'] == 'person' for d in detections):
                self._handle_human_detection(frame, detections)
            else:
                self._handle_no_detection()
            
            # Display frame
            cv2.imshow("ONNX Security Feed", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.is_active = False
                break
        
        cap.release()
        cv2.destroyAllWindows()
    
    def _handle_human_detection(self, frame, detections):
        """Handle human detection event"""
        current_time = time.time()
        
        # Check cooldown period
        if current_time - self.last_alarm_time < ALARM_COOLDOWN:
            return
        
        self.last_alarm_time = current_time
        
        # Start alarm
        self._trigger_alarm()
        
        # Start recording
        self._start_recording()
        
        # Create incident report
        incident = self._create_incident_report(detections)
        self.detection_history.append(incident)
        
        logger.warning(f"🚨 HUMAN DETECTED! - {incident['timestamp']}")
        self._save_incident_locally(incident)
    
    def _handle_no_detection(self):
        """Handle when no humans are detected"""
        if self.recording and time.time() - self.video_start_time > 10:
            self._stop_recording()
    
    def _trigger_alarm(self):
        """Trigger the buzzer alarm"""
        logger.info(f"🔊 Buzzer ON for {ALARM_DURATION} seconds")
        
        def alarm_thread():
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
            time.sleep(ALARM_DURATION)
            GPIO.output(BUZZER_PIN, GPIO.LOW)
            logger.info("🔊 Buzzer OFF")
        
        threading.Thread(target=alarm_thread, daemon=True).start()
    
    def _start_recording(self):
        """Start video recording"""
        if self.recording:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = LOG_DIR / f"incident_{timestamp}.avi"
        
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.video_writer = cv2.VideoWriter(
            str(filename), fourcc, 20.0, (FRAME_WIDTH, FRAME_HEIGHT)
        )
        self.recording = True
        self.video_start_time = time.time()
        
        logger.info(f"📹 Recording started: {filename}")
    
    def _stop_recording(self):
        """Stop video recording"""
        if not self.recording:
            return
        
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        
        self.recording = False
        logger.info("📹 Recording stopped")
    
    def _create_incident_report(self, detections):
        """Create a structured incident report"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        incident = {
            'timestamp': timestamp,
            'incident_id': f"INC-{int(time.time())}",
            'detections': detections,
            'zone': "RESTRICTED_ZONE_01",
            'severity': "HIGH",
            'status': "ACTIVE",
            'source': "ONNX_SECURITY_SYSTEM",
            'camera_index': CAMERA_INDEX,
            'confidence_threshold': CONFIDENCE_THRESHOLD
        }
        
        return incident
    
    def _save_incident_locally(self, incident):
        """Save incident locally"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = LOG_DIR / f"incident_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(incident, f, indent=2)
        
        logger.info(f"📄 Incident report saved: {filename}")

# ── Main Execution ────────────────────────────────────────────────────────────
def main():
    print("🚨 ONNX Security System for Raspberry Pi")
    print("=" * 50)
    print("Features:")
    print("• Real-time human detection (no PyTorch required)")
    print("• Buzzer alarm")
    print("• Video recording")
    print("• ARM-compatible (no illegal instruction errors)")
    print("=" * 50)
    
    try:
        system = ONNXSecuritySystem()
        system.start()
    except Exception as e:
        logger.error(f"❌ System error: {e}")
        GPIO.cleanup()

if __name__ == "__main__":
    main()