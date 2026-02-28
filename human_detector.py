import cv2
from ultralytics import YOLO

# Load the YOLO model
model = YOLO("yolov8n.pt")

def main():
    print("=== Camera Detection System ===")
    print("Available cameras on your system:")
    print("1. Intel MIPI Camera (Built-in) - /dev/video0")
    print("2. Logitech Brio 101 (USB) - /dev/video49, /dev/video50")
    print("3. Virtual Camera (v4l2loopback) - /dev/video1-48")
    
    print("\nYour code currently tries to use: /dev/video0 (Intel MIPI Camera)")
    print("This is your built-in desktop camera, NOT the Logitech webcam.")
    
    # Test different cameras
    test_camera(0, "Intel MIPI Camera (Built-in)")
    test_camera(49, "Logitech Brio 101 (USB Webcam)")
    test_camera(50, "Logitech Brio 101 (Alternative)")

def test_camera(camera_index, camera_name):
    """Test a specific camera"""
    print(f"\n--- Testing {camera_name} (Index: {camera_index}) ---")
    
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print(f"❌ Cannot open {camera_name}")
        print("   This could be due to:")
        print("   - No physical camera connected")
        print("   - Camera busy with another application")
        print("   - User not in 'video' group for permissions")
        return
    
    print(f"✅ {camera_name} opened successfully!")
    print("   Press 'q' to quit this camera test")
    
    try:
        frame_count = 0
        while True:  # Changed from 'frame_count < 100' to 'True' for continuous operation
            ret, frame = cap.read()
            if not ret:
                print(f"❌ Cannot read frame from {camera_name}")
                break

            # Run detection
            results = model(frame, verbose=False)
            human_detected = False
            detections = []

            for result in results:
                for box in result.boxes:
                    cls = int(box.cls[0])
                    confidence = float(box.conf[0])
                    class_name = model.names[cls]
                    
                    detections.append(f"{class_name}: {confidence:.2f}")
                    
                    if class_name == "person":
                        human_detected = True
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        label = f"Person: {confidence:.2f}"
                        cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

            # Display detection info
            info_text = f"{camera_name}: {'HUMAN' if human_detected else 'NO HUMAN'}"
            cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
            if detections:
                detections_text = ", ".join(detections)
                cv2.putText(frame, detections_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            cv2.imshow(f"Camera Test - {camera_name}", frame)
            
            # Print to console
            if human_detected:
                print(f"   ✅ HUMAN DETECTED! ({len(detections)} total objects)")
            else:
                print(f"   ❌ No human detected ({len(detections)} total objects)")
                if detections:
                    print(f"      Detected: {', '.join(detections)}")

            frame_count += 1
            
            # Check for 'q' key to quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print(f"\n⏹️  Stopped testing {camera_name} (user pressed 'q')")
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()