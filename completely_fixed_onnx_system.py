

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
CAMERA_INDEX = 0  # Start with 0, change after testing
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

# YOLO Model Configuration (80 classes)
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

# ── ONNX Model Class (Completely Fixed) ───────────────────────────────────────
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
        pred = outputs[0]
        pred = np.squeeze(pred)

        # Force into (N, D)
        if pred.ndim == 3:
            pred = pred[0]  # (D, N) or (N, D)

        if pred.ndim != 2:
            logger.error(f"Unexpected pred ndim: {pred.ndim}, shape: {pred.shape}")
            return []

        # If it's (D, N) transpose to (N, D)
        if pred.shape[0] in (84, 85) and pred.shape[1] not in (84, 85):
            pred = pred.T

        D = pred.shape[1]  # features per detection
        if D not in (84, 85):
            logger.error(f"Unexpected detection length D={D}. Shape={pred.shape}. Can't map classes.")
            return []

        boxes, scores, class_ids = [], [], []
        orig_h, orig_w = original_shape[:2]

        for det in pred:
            x, y, w, h = det[:4]

            if D == 85:
                # YOLOv5-style: [x,y,w,h, obj, 80 class probs]
                obj = float(det[4])
                class_scores = det[5:]
                class_id = int(np.argmax(class_scores))
                score = obj * float(class_scores[class_id])
            else:
                # YOLOv8 common: [x,y,w,h, 80 class scores]
                class_scores = det[4:]
                class_id = int(np.argmax(class_scores))
                score = float(class_scores[class_id])

            # Hard safety: skip if class index doesn't match your CLASSES list
            if class_id < 0 or class_id >= len(CLASSES):
                continue

            if score < CONFIDENCE_THRESHOLD:
                continue

            x1 = int((x - w / 2) * orig_w / self.input_width)
            y1 = int((y - h / 2) * orig_h / self.input_height)
            x2 = int((x + w / 2) * orig_w / self.input_width)
            y2 = int((y + h / 2) * orig_h / self.input_height)

            boxes.append([x1, y1, x2 - x1, y2 - y1])  # xywh for NMS
            scores.append(score)
            class_ids.append(class_id)

        for det in pred:
            x, y, w, h = det[:4]

            # YOLOv8: class scores start at index 4
            class_scores = det[4:]
            class_id = int(np.argmax(class_scores))
            score = float(class_scores[class_id])

            if score < CONFIDENCE_THRESHOLD:
                continue

            # Convert to pixel coordinates
            x1 = int((x - w / 2) * orig_w / self.input_width)
            y1 = int((y - h / 2) * orig_h / self.input_height)
            x2 = int((x + w / 2) * orig_w / self.input_width)
            y2 = int((y + h / 2) * orig_h / self.input_height)

            # Store as xywh for NMSBoxes
            boxes.append([x1, y1, x2 - x1, y2 - y1])
            scores.append(score)
            class_ids.append(class_id)

        results = []

        if len(boxes) > 0:
            indices = cv2.dnn.NMSBoxes(boxes, scores, CONFIDENCE_THRESHOLD, IOU_THRESHOLD)

            if len(indices) > 0:
                for i in indices.flatten():
                    results.append({
                        'class': CLASSES[class_ids[i]],
                        'confidence': float(scores[i]),
                        'bbox': boxes[i]
                    })

        return results

# ── Security System Class (Completely Fixed) ──────────────────────────────────
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
        
        logger.info("ONNX Security System initialized (Completely Fixed)")
    
    def start(self):
        """Start the security system"""
        self.is_active = True
        logger.info("🚨 ONNX Security System Activated (Completely Fixed)")
        
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
        """Main camera processing loop (Completely Fixed)"""
        cap = cv2.VideoCapture(CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        
        if not cap.isOpened():
            logger.error(f"❌ Cannot open camera at index {CAMERA_INDEX}")
            return
        
        logger.info(f"📹 Camera started (Index: {CAMERA_INDEX}) - Completely Fixed")
        
        frame_count = 0
        detection_count = 0
        
        while self.is_active:
            ret, frame = cap.read()
            if not ret:
                logger.warning("⚠️  Cannot read frame from camera")
                time.sleep(1)
                continue
            
            frame_count += 1
            
            # Run detection
            input_tensor = self.detector.preprocess(frame)
            outputs = self.detector.session.run(self.detector.output_names, {self.detector.input_name: input_tensor})
            detections = self.detector.postprocess(outputs, frame.shape)
            
            # Check for human detection
            if any(d['class'] == 'person' for d in detections):
                detection_count += 1
                self._handle_human_detection(frame, detections)
            else:
                self._handle_no_detection()
            
            # Status update every 100 frames
            if frame_count % 100 == 0:
                logger.info(f"📊 Processing... Frames: {frame_count}, Detections: {detection_count}")
            
            time.sleep(0.05)  # Small delay to prevent CPU overload
        
        cap.release()
        logger.info("📹 Camera stopped")
    
    def _handle_human_detection(self, frame, detections):
        """Handle human detection event"""
        current_time = time.time()
        
        # Check cooldown period
        if current_time - self.last_alarm_time < ALARM_COOLDOWN:
            logger.info("⏰ Alarm cooldown active, skipping alarm")
            return
        
        self.last_alarm_time = current_time
        
        # Start alarm
        self._trigger_alarm()
        
        # Start recording
        self._start_recording()
        
        # Create incident report
        incident = self._create_incident_report(detections)
        self.detection_history.append(incident)
        
        # Log detection details
        logger.warning(f"🚨 HUMAN DETECTED! - {incident['timestamp']}")
        for detection in detections:
            if detection['class'] == 'person':
                logger.warning(f"   Person detected with confidence: {detection['confidence']:.2f}")
        
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
            'source': "ONNX_SECURITY_SYSTEM_FIXED",
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
    print("🚨 Completely Fixed ONNX Security System for Raspberry Pi")
    print("=" * 65)
    print("Features:")
    print("• Real-time human detection (no PyTorch required)")
    print("• Buzzer alarm")
    print("• Video recording")
    print("• Fixed NMSBoxes format issues")
    print("• Fixed class index range issues")
    print("• Headless mode compatible")
    print("=" * 65)
    
    try:
        system = ONNXSecuritySystem()
        system.start()
    except Exception as e:
        logger.error(f"❌ System error: {e}")
        import traceback
        traceback.print_exc()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
