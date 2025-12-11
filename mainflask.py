"""
SiteScan Robot - Flask web server for real-time sensor monitoring.
Provides a web dashboard to view sensor readings in real-time.
"""

import logging
import RPi.GPIO as GPIO
import time
import os
from flask import Flask, render_template, jsonify, request, send_from_directory
from datetime import datetime
from werkzeug.utils import secure_filename

from config import (
    GPIO_PINS, SENSOR_THRESHOLDS, 
    BUZZER_DURATION_SHORT, BUZZER_DURATION_MEDIUM, BUZZER_DURATION_LONG,
    FLASK_HOST, FLASK_PORT, FLASK_DEBUG,
    CAMERA_IMAGE_FOLDER, CAMERA_ENABLE_CRACK_DETECTION, CAMERA_CRACK_THRESHOLD,
    PIEZO_SENSOR, SERVO_CONFIG
)

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize GPIO FIRST, before any sensor imports
from gpio_init import init_gpio, cleanup_gpio
init_gpio()

# Now import sensor modules (after GPIO is initialized)
from ultrasonic import Ultrasonic
from imu_mpu6050 import MPU6050
from piezo_sensor import PiezoSensor
from ir_sensor import IRSensor
from buzzer import Buzzer
from servo_controller import DualServoController

# Try to import camera (optional)
try:
    from camera_module import SiteScanCamera
    CAMERA_AVAILABLE = True
except Exception as e:
    CAMERA_AVAILABLE = False
    logger.warning(f"Camera not available: {e}")

# Try to import crack detector (for uploaded images)
try:
    from crack_detector import CrackDetector
    CRACK_DETECTOR_AVAILABLE = True
    crack_detector = CrackDetector(crack_threshold=CAMERA_CRACK_THRESHOLD)
    logger.info("Crack detector initialized for image uploads")
except Exception as e:
    CRACK_DETECTOR_AVAILABLE = False
    crack_detector = None
    logger.warning(f"Crack detector not available: {e}")

# Initialize sensors
ultra = None
mpu = None
piezo = None
ir = None
buzzer = None
camera = None
servos = None

try:
    ultra = Ultrasonic(GPIO_PINS['ULTRASONIC_TRIG'], GPIO_PINS['ULTRASONIC_ECHO'])
mpu = MPU6050()
    piezo = PiezoSensor(
        GPIO_PINS['PIEZO_SENSOR'],
        tap_threshold=PIEZO_SENSOR['TAP_THRESHOLD'],
        sample_window=PIEZO_SENSOR['SAMPLE_WINDOW'],
        hollow_duration_threshold=PIEZO_SENSOR['HOLLOW_DURATION_THRESHOLD']
    )
    ir = IRSensor(GPIO_PINS['IR_SENSOR'])
    buzzer = Buzzer(GPIO_PINS['BUZZER'])
    
    # Initialize camera if available
    if CAMERA_AVAILABLE:
        try:
            camera = SiteScanCamera(
                image_folder=CAMERA_IMAGE_FOLDER,
                enable_crack_detection=CAMERA_ENABLE_CRACK_DETECTION,
                crack_threshold=CAMERA_CRACK_THRESHOLD
            )
            logger.info("Camera with crack detection initialized")
        except Exception as e:
            logger.warning(f"Camera initialization failed: {e}")
    
    # Initialize servos if enabled
    if SERVO_CONFIG['ENABLED']:
        try:
            servos = DualServoController(
                pan_pin=GPIO_PINS['SERVO_PAN'],
                tilt_pin=GPIO_PINS['SERVO_TILT'],
                pan_range=SERVO_CONFIG['PAN_RANGE'],
                tilt_range=SERVO_CONFIG['TILT_RANGE']
            )
            servos.set_position(
                SERVO_CONFIG['DEFAULT_PAN'],
                SERVO_CONFIG['DEFAULT_TILT']
            )
            logger.info("Servos initialized and centered")
        except Exception as e:
            logger.warning(f"Servo initialization failed: {e}")
            servos = None
    
    logger.info("All sensors initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize sensors: {e}")
    cleanup_gpio()
    raise

# Global state
buzzer_state = "OFF"
last_image_path = None
last_crack_scan_result = None

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = os.path.expanduser(CAMERA_IMAGE_FOLDER)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def check_floor_flatness(distance: float, pitch: float, roll: float) -> bool:
    """
    Check if floor flatness is within acceptable limits.
    
    Args:
        distance: Ultrasonic distance reading in cm
        pitch: Pitch angle in degrees
        roll: Roll angle in degrees
        
    Returns:
        bool: True if floor is uneven (anomaly detected), False otherwise
    """
    if distance < 0:  # Invalid reading
        return False
        
    if distance < SENSOR_THRESHOLDS['ULTRASONIC_MIN'] or distance > SENSOR_THRESHOLDS['ULTRASONIC_MAX']:
        return True
    
    if abs(pitch) > SENSOR_THRESHOLDS['TILT_THRESHOLD'] or abs(roll) > SENSOR_THRESHOLDS['TILT_THRESHOLD']:
        return True
    
    return False

@app.route('/sensor-data')
def sensor_data():
    """Endpoint to get current sensor readings."""
    global buzzer_state, last_image_path

    # Check if sensors are initialized
    if not all([ultra, mpu, piezo, ir, buzzer]):
        return jsonify({
            "error": "Sensors not initialized",
            "distance": -1.0,
            "pitch": 0.0,
            "roll": 0.0,
            "vibration": 0,
            "obstacle": False,
            "buzzer_state": "ERROR",
            "time": datetime.now().strftime('%H:%M:%S')
        }), 500

    try:
        distance = ultra.distance()
        pitch, roll = mpu.get_tilt()
        obstacle = ir.is_obstacle()
        
        # Enhanced piezo tap test
        tap_result = piezo.tap_test()
        vibration = piezo.detect()  # Simple binary for backward compatibility

        issue_detected = False

        # Check for floor unevenness
        if check_floor_flatness(distance, pitch, roll):
            buzzer.beep(BUZZER_DURATION_SHORT)
            buzzer_state = "ON"
            issue_detected = True
            logger.warning("Floor unevenness detected")
            if camera:
                camera.capture("floor_uneven", detect_cracks=True)

        # Check for hollow tile (tap test)
        elif tap_result.get("is_hollow", False):
            buzzer.beep(BUZZER_DURATION_LONG)
            buzzer_state = "ON"
            issue_detected = True
            logger.warning("Hollow tile detected via tap test")
            if camera:
                camera.capture("hollow_tile", detect_cracks=True)

        # Check for vibration (legacy)
        elif vibration == 1:
            buzzer.beep(BUZZER_DURATION_MEDIUM)
            buzzer_state = "ON"
            issue_detected = True
            logger.warning("Vibration anomaly detected")
            if camera:
                camera.capture("vibration_anomaly", detect_cracks=True)

        # Check for obstacle
        elif obstacle:
            buzzer.beep(BUZZER_DURATION_MEDIUM)
            buzzer_state = "ON"
            issue_detected = True
            logger.warning("Obstacle detected")
            if camera:
                camera.capture("obstacle", detect_cracks=True)

        else:
            buzzer_state = "OFF"

    except Exception as e:
        logger.error(f"Error reading sensors: {e}")
        distance = -1.0
        pitch = roll = 0.0
        vibration = 0
        obstacle = False
        buzzer_state = "ERROR"

    # Include crack detection status if available
    crack_status = None
    if last_crack_scan_result:
        crack_status = {
            "detected": last_crack_scan_result.get("detected", False),
            "confidence": last_crack_scan_result.get("confidence", 0.0),
            "crack_count": last_crack_scan_result.get("crack_count", 0)
        }
    
    # Prepare tap test data
    tap_test_data = None
    if tap_result.get("tap_detected"):
        if tap_result.get("vibration_analysis"):
            vib = tap_result["vibration_analysis"]
            tap_test_data = {
                "tap_detected": True,
                "is_hollow": tap_result.get("is_hollow", False),
                "pattern": vib.get("pattern", "unknown"),
                "duration": vib.get("duration", 0.0),
                "oscillation_count": vib.get("oscillation_count", 0),
                "confidence": tap_result.get("confidence", 0.0)
            }
        else:
            tap_test_data = {
                "tap_detected": True,
                "is_hollow": None,
                "pattern": "unknown",
                "duration": 0.0,
                "oscillation_count": 0,
                "confidence": 0.0
            }
    else:
        tap_test_data = {
            "tap_detected": False,
            "is_hollow": None,
            "pattern": "none",
            "duration": 0.0,
            "oscillation_count": 0,
            "confidence": 0.0
        }
    
    # Get servo position if available
    servo_position = None
    if servos:
        try:
            pan, tilt = servos.get_position()
            servo_position = {"pan": round(pan, 1), "tilt": round(tilt, 1)}
        except:
            pass
    
    response_data = {
        "distance": round(distance, 2),
        "pitch": round(pitch, 2),
        "roll": round(roll, 2),
        "vibration": vibration,
        "obstacle": obstacle,
        "buzzer_state": buzzer_state,
        "time": datetime.now().strftime('%H:%M:%S'),
        "camera_available": CAMERA_AVAILABLE and camera is not None,
        "crack_status": crack_status,
        "tap_test": tap_test_data,
        "servo_available": servos is not None,
        "servo_position": servo_position
    }
    
    return jsonify(response_data)

@app.route('/scan-cracks', methods=['POST'])
def scan_cracks():
    """Manually trigger a crack scan."""
    global last_crack_scan_result
    
    if not CAMERA_AVAILABLE:
        return jsonify({
            "error": "Camera module not available. Check camera hardware and ensure picamera2 is installed.",
            "detected": False,
            "crack_count": 0,
            "confidence": 0.0
        }), 503
    
    if not camera:
        return jsonify({
            "error": "Camera not initialized. Check camera hardware connection and permissions.",
            "detected": False,
            "crack_count": 0,
            "confidence": 0.0
        }), 503
    
    try:
        result = camera.scan_for_cracks()
        last_crack_scan_result = result
        
        if result.get("detected", False):
            buzzer.beep(BUZZER_DURATION_LONG)
            logger.warning(f"CRACK DETECTED! Confidence: {result['confidence']:.2f}, "
                         f"Cracks: {result['crack_count']}")
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error scanning for cracks: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Error during crack scan: {str(e)}",
            "detected": False,
            "crack_count": 0,
            "confidence": 0.0
        }), 500

@app.route('/upload-image', methods=['POST'])
def upload_image():
    """Upload and analyze an image for cracks."""
    if 'file' not in request.files:
        return jsonify({
            "error": "No file provided",
            "success": False
        }), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({
            "error": "No file selected",
            "success": False
        }), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            "error": "Invalid file type. Allowed: PNG, JPG, JPEG, GIF, BMP",
            "success": False
        }), 400
    
    if not CRACK_DETECTOR_AVAILABLE:
        return jsonify({
            "error": "Crack detection not available. Install opencv-python.",
            "success": False
        }), 503
    
    try:
        # Ensure upload folder exists
        upload_folder = app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = int(time.time())
        filename = f"upload_{timestamp}_{filename}"
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        logger.info(f"Image uploaded: {filepath}")
        
        # Analyze for cracks
        result = crack_detector.detect_cracks(filepath, save_annotated=True)
        
        # Prepare response
        response_data = {
            "success": True,
            "detected": result.get("detected", False),
            "confidence": result.get("confidence", 0.0),
            "crack_count": result.get("crack_count", 0),
            "edge_density": result.get("edge_density", 0.0),
            "original_image": filename,
            "annotated_image": None,
            "message": ""
        }
        
        if result.get("annotated_path"):
            # Return relative path for annotated image
            annotated_filename = os.path.basename(result["annotated_path"])
            response_data["annotated_image"] = annotated_filename
        
        if result.get("detected", False):
            response_data["message"] = f"Cracks detected! Confidence: {result['confidence']:.1%}, Cracks: {result['crack_count']}"
            logger.warning(f"CRACKS DETECTED in uploaded image: {response_data['message']}")
        else:
            response_data["message"] = "No cracks detected in uploaded image"
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error processing uploaded image: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Error processing image: {str(e)}",
            "success": False
        }), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded images."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template("index.html", current_time=datetime.now().strftime('%H:%M:%S'))

if __name__ == '__main__':
    try:
        logger.info(f"Starting Flask server on {FLASK_HOST}:{FLASK_PORT}")
        app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG, use_reloader=False)
    except Exception as e:
        logger.error(f"Flask server error: {e}")
    finally:
        if servos:
            servos.cleanup()
        cleanup_gpio()
