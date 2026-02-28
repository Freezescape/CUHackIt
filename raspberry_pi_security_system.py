#!/usr/bin/env python3
"""
Raspberry Pi Security System with Human Detection
===============================================

Features:
- Real-time human detection using YOLOv8
- Buzzer alarm when human detected in restricted zone
- Automatic recording and logging of events
- AI integration with Backboard.io counsel for incident analysis
- GPIO integration for Raspberry Pi hardware

Hardware Setup:
- Camera: Logitech Brio 101 (or any USB webcam)
- Buzzer: Active buzzer connected to GPIO pin 18
- Raspberry Pi: Any model with GPIO pins

Installation:
1. pip3 install opencv-python ultralytics numpy requests
2. sudo apt install python3-rpi.gpio
3. Set BACKBOARD_API_KEY environment variable
4. Run: python3 raspberry_pi_security_system.py
"""

import cv2
from ultralytics import YOLO
import RPi.GPIO as GPIO
import time
import threading
import requests
import json
import os
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

# AI Integration
BACKBOARD_API_KEY = os.environ.get("BACKBOARD_API_KEY", "")
BASE_URL = "https://app.backboard.io/api"

# Agent IDs (replace with your actual IDs)
TECHNICIAN_ID = "e734432b-dc99-4132-b12b-fef16ff3cb91"
AUDITOR_ID = "f0d83f5c-3364-4dda-8a8d-43a3c519dc02"
CHAIRMAN_ID = "11b491ae-f707-4e44-b315-ec85f28f7f34"

# File Paths
LOG_DIR = Path("security_logs")
LOG_DIR.mkdir(exist_ok=True)
YOLO_MODEL_PATH = "yolov8n.pt"

# ── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'security_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ── AI Client ─────────────────────────────────────────────────────────────────
class BackboardClient:
    def __init__(self):
        self.headers = {"X-API-Key": BACKBOARD_API_KEY}
    
    def create_thread(self, assistant_id: str) -> str:
        response = requests.post(
            f"{BASE_URL}/assistants/{assistant_id}/threads",
            json={},
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["thread_id"]
    
    def send_message(self, thread_id: str, content: str, llm_provider: str, model_name: str) -> str:
        response = requests.post(
            f"{BASE_URL}/threads/{thread_id}/messages",
            headers=self.headers,
            data={
                "content": content,
                "stream": "false",
                "memory": "Auto",
                "llm_provider": llm_provider,
                "model_name": model_name,
            }
        )
        response.raise_for_status()
        return response.json()["content"]

# ── Security System Class ─────────────────────────────────────────────────────
class SecuritySystem:
    def __init__(self):
        self.model = YOLO(YOLO_MODEL_PATH)
        self.client = BackboardClient() if BACKBOARD_API_KEY else None
        
        self.is_active = False
        self.last_alarm_time = 0
        self.current_incident = None
        self.detection_history = []
        
        # Video recording
        self.recording = False
        self.video_writer = None
        self.video_start_time = None
        
        logger.info("Security System initialized")
    
    def start(self):
        """Start the security system"""
        self.is_active = True
        logger.info("🚨 Security System Activated")
        
        # Start camera thread
        camera_thread = threading.Thread(target=self._camera_loop, daemon=True)
        camera_thread.start()
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        monitor_thread.start()
        
        try:
            while self.is_active:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Security System Stopped by User")
            self.stop()
    
    def stop(self):
        """Stop the security system"""
        self.is_active = False
        self._stop_recording()
        GPIO.cleanup()
        logger.info("Security System Stopped")
    
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
            results = self.model(frame, verbose=False)
            current_detections = self._process_detections(results, frame)
            
            # Check for human detection
            if any(d['class'] == 'person' for d in current_detections):
                self._handle_human_detection(frame, current_detections)
            else:
                self._handle_no_detection()
            
            # Display frame
            cv2.imshow("Security Feed", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.is_active = False
                break
        
        cap.release()
        cv2.destroyAllWindows()
    
    def _process_detections(self, results, frame):
        """Process YOLO detection results"""
        detections = []
        
        for result in results:
            for box in result.boxes:
                cls = int(box.cls[0])
                confidence = float(box.conf[0])
                class_name = self.model.names[cls]
                
                if confidence >= CONFIDENCE_THRESHOLD:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    # Draw bounding box
                    color = (0, 255, 0) if class_name == 'person' else (255, 255, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    
                    # Add label
                    label = f"{class_name}: {confidence:.2f}"
                    cv2.putText(frame, label, (x1, y1-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    
                    detections.append({
                        'class': class_name,
                        'confidence': confidence,
                        'bbox': (x1, y1, x2, y2)
                    })
        
        return detections
    
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
        self.current_incident = incident
        self.detection_history.append(incident)
        
        logger.warning(f"🚨 HUMAN DETECTED! - {incident['timestamp']}")
        
        # Send to AI counsel
        if self.client:
            self._send_to_ai_counsel(incident)
        else:
            logger.warning("⚠️  No AI counsel configured - saving incident locally")
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
            'status': "ACTIVE"
        }
        
        return incident
    
    def _send_to_ai_counsel(self, incident):
        """Send incident to AI counsel for analysis"""
        try:
            # Phase 1: Technician Analysis
            thread_1 = self.client.create_thread(TECHNICIAN_ID)
            tech_prompt = self._create_technician_prompt(incident)
            tech_response = self.client.send_message(
                thread_1, tech_prompt, "google", "gemini-2.5-flash"
            )
            
            # Phase 2: Auditor Review
            thread_2 = self.client.create_thread(AUDITOR_ID)
            audit_prompt = self._create_auditor_prompt(incident, tech_response)
            audit_response = self.client.send_message(
                thread_2, audit_prompt, "anthropic", "claude-sonnet-4-20250514"
            )
            
            # Phase 3: Chairman Ruling
            thread_3 = self.client.create_thread(CHAIRMAN_ID)
            chairman_prompt = self._create_chairman_prompt(incident, tech_response, audit_response)
            chairman_response = self.client.send_message(
                thread_3, chairman_prompt, "openai", "gpt-4o"
            )
            
            # Save complete analysis
            analysis = {
                'incident': incident,
                'technician_analysis': tech_response,
                'auditor_review': audit_response,
                'chairman_ruling': chairman_response,
                'analysis_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            self._save_ai_analysis(analysis)
            logger.info("🤖 AI analysis completed and saved")
            
        except Exception as e:
            logger.error(f"❌ AI analysis failed: {e}")
            self._save_incident_locally(incident)
    
    def _create_technician_prompt(self, incident):
        """Create prompt for technician analysis"""
        return f"""
SECURITY INCIDENT ANALYSIS REQUEST

Incident Details:
- Time: {incident['timestamp']}
- Location: {incident['zone']}
- Incident ID: {incident['incident_id']}
- Severity: {incident['severity']}

Detection Summary:
{len(incident['detections'])} objects detected:
{chr(10).join([f"- {d['class']} (confidence: {d['confidence']:.2f})" for d in incident['detections']])}

TASK:
Provide a rapid technical analysis of this security incident. Focus on:
1. Object detection accuracy and confidence levels
2. Timeline analysis and pattern recognition
3. System performance metrics
4. Immediate technical recommendations

Format your response with clear sections and actionable items.
"""
    
    def _create_auditor_prompt(self, incident, tech_response):
        """Create prompt for auditor review"""
        return f"""
AUDIT REVIEW REQUEST

Original Incident:
{incident}

Technician Analysis:
{tech_response}

TASK:
Audit the technician's analysis for:
1. Potential false positives or detection errors
2. Missing context or blind spots
3. Risk assessment accuracy
4. Safety and compliance concerns
5. Recommendations for improvement

Be adversarial and thorough. Identify any flaws in the analysis.
"""
    
    def _create_chairman_prompt(self, incident, tech_response, audit_response):
        """Create prompt for chairman ruling"""
        return f"""
FINAL RULING REQUEST

Security Incident: {incident['incident_id']}
Time: {incident['timestamp']}

Technician Analysis:
{tech_response}

Auditor Review:
{audit_response}

TASK:
Synthesize both analyses and issue a final ruling on this security incident. 
You MUST begin your response with exactly 'Consensus Reached:' if the analyses 
can be reconciled, or 'Deadlock:' if they are irreconcilable.

Provide:
1. Final assessment of the incident
2. Recommended security actions
3. System improvement suggestions
4. Risk mitigation strategies

This is for a restricted zone security system.
"""
    
    def _save_ai_analysis(self, analysis):
        """Save AI analysis to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = LOG_DIR / f"ai_analysis_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        logger.info(f"📄 AI analysis saved: {filename}")
    
    def _save_incident_locally(self, incident):
        """Save incident locally when AI is not available"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = LOG_DIR / f"incident_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(incident, f, indent=2)
        
        logger.info(f"📄 Incident report saved locally: {filename}")

# ── Main Execution ────────────────────────────────────────────────────────────
def main():
    print("🚨 Raspberry Pi Security System")
    print("=" * 50)
    print("Features:")
    print("• Real-time human detection")
    print("• Buzzer alarm")
    print("• Video recording")
    print("• AI counsel integration")
    print("=" * 50)
    
    if not BACKBOARD_API_KEY:
        print("⚠️  Warning: BACKBOARD_API_KEY not set")
        print("   AI integration will be disabled")
        print("   Installations will be saved locally only")
        print()
    
    try:
        system = SecuritySystem()
        system.start()
    except Exception as e:
        logger.error(f"❌ System error: {e}")
        GPIO.cleanup()

if __name__ == "__main__":
    main()