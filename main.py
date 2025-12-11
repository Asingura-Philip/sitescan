"""
SiteScan Robot - Main sensor monitoring script.
Continuously monitors all sensors and alerts on anomalies.
"""

import time
import logging
import RPi.GPIO as GPIO
from config import (
    GPIO_PINS, SENSOR_THRESHOLDS, BUZZER_DURATION_MEDIUM,
    CAMERA_IMAGE_FOLDER, CAMERA_ENABLE_CRACK_DETECTION, 
    CAMERA_CRACK_THRESHOLD, CAMERA_CRACK_SCAN_INTERVAL,
    PIEZO_SENSOR, SERVO_CONFIG
)

from gpio_init import init_gpio, cleanup_gpio
from ultrasonic import Ultrasonic
from imu_mpu6050 import MPU6050
from piezo_sensor import PiezoSensor
from ir_sensor import IRSensor
from buzzer import Buzzer
from servo_controller import DualServoController

# Try to import camera (optional - may not be available)
try:
    from camera_module import SiteScanCamera
    CAMERA_AVAILABLE = True
except Exception as e:
    CAMERA_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"Camera not available: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize GPIO first
init_gpio()

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
    if distance < SENSOR_THRESHOLDS['ULTRASONIC_MIN'] or distance > SENSOR_THRESHOLDS['ULTRASONIC_MAX']:
        return True
    
    if abs(pitch) > SENSOR_THRESHOLDS['TILT_THRESHOLD'] or abs(roll) > SENSOR_THRESHOLDS['TILT_THRESHOLD']:
        return True
    
    return False

def main():
    """Main sensor monitoring loop."""
    # Initialize sensors
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
        camera = None
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
        servos = None
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
        
        if servos:
            logger.info("SiteScan Robot Running (Servos Enabled)...")
        else:
            logger.info("SiteScan Robot Running (Servos Disabled)...")
        time.sleep(1)
        
        # Track last crack scan time
        last_crack_scan = time.time()
        last_servo_scan = time.time() if servos and SERVO_CONFIG['SCAN_ENABLED'] else None
        
    except Exception as e:
        logger.error(f"Failed to initialize sensors: {e}")
        cleanup_gpio()
        return

    try:
        while True:
            current_time = time.time()
            
            # Read all sensors
            distance = ultra.distance()
            pitch, roll = mpu.get_tilt()
            obstacle = ir.is_obstacle()
            
            # Enhanced piezo tap test (hollow vs solid detection)
            tap_result = piezo.tap_test()
            piezo_val = piezo.detect()  # Simple binary for backward compatibility

            # Display readings
            logger.info("\n" + "=" * 40)
            logger.info(f"Distance: {distance:.2f} cm")
            logger.info(f"Tilt Pitch: {pitch:.2f}°, Roll: {roll:.2f}°")
            logger.info(f"Piezo vibration: {piezo_val}")
            logger.info(f"Obstacle detected: {obstacle}")
            
            # Display tap test results
            if tap_result["tap_detected"]:
                if tap_result["vibration_analysis"]:
                    vib = tap_result["vibration_analysis"]
                    logger.info(f"Tap detected - Duration: {vib['duration']:.3f}s, "
                              f"Oscillations: {vib['oscillation_count']}, "
                              f"Pattern: {vib['pattern']}")
                    if tap_result["is_hollow"]:
                        logger.warning("⚠️  HOLLOW TILE DETECTED! (Tap test)")
                    else:
                        logger.info("✓ Solid tile (Tap test)")

            # Floor unevenness alert
            if check_floor_flatness(distance, pitch, roll):
                logger.warning("WARNING: Floor unevenness detected!")
                buzzer.beep(BUZZER_DURATION_MEDIUM)
                if camera:
                    camera.capture("floor_uneven", detect_cracks=True)

            # Piezo tap test alert (hollow tile detection)
            if tap_result.get("is_hollow", False):
                logger.warning("WARNING: HOLLOW TILE DETECTED via tap test!")
                buzzer.beep(BUZZER_DURATION_LONG)
                if camera:
                    camera.capture("hollow_tile", detect_cracks=True)
            
            # Legacy piezo vibration alert (simple binary)
            elif piezo_val == 1:
                logger.warning("WARNING: Tile vibration anomaly detected!")
                buzzer.beep(BUZZER_DURATION_MEDIUM)
                if camera:
                    camera.capture("vibration_anomaly", detect_cracks=True)

            # IR obstacle alert
            if obstacle:
                logger.warning("WARNING: Obstacle detected by IR!")
                buzzer.beep(BUZZER_DURATION_MEDIUM)
                if camera:
                    camera.capture("obstacle", detect_cracks=True)

            # Periodic crack scan
            if camera and (current_time - last_crack_scan) >= CAMERA_CRACK_SCAN_INTERVAL:
                logger.info("Performing periodic crack scan...")
                crack_result = camera.scan_for_cracks()
                if crack_result.get("detected", False):
                    logger.warning(f"CRACK DETECTED! Confidence: {crack_result['confidence']:.2f}, "
                                 f"Cracks: {crack_result['crack_count']}")
                    buzzer.beep(BUZZER_DURATION_LONG)
                last_crack_scan = current_time

            # Periodic servo scan pattern (if enabled)
            if servos and SERVO_CONFIG['SCAN_ENABLED'] and last_servo_scan:
                if (current_time - last_servo_scan) >= SERVO_CONFIG['SCAN_INTERVAL']:
                    logger.info("Performing servo scan pattern...")
                    servos.scan_pattern("grid", steps=3)
                    last_servo_scan = current_time

            time.sleep(0.3)

    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        if camera:
            camera.stop()
        if servos:
            servos.cleanup()
        cleanup_gpio()

if __name__ == '__main__':
    main()
