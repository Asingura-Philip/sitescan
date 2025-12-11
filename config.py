"""
Configuration file for SiteScan Robot project.
Centralizes all GPIO pin assignments and system settings.
"""

# GPIO Pin Configuration (BCM mode)
GPIO_PINS = {
    'ULTRASONIC_TRIG': 23,
    'ULTRASONIC_ECHO': 24,
    'IR_SENSOR': 5,
    'PIEZO_SENSOR': 16,
    'BUZZER': 18,
    'SERVO_PAN': 12,   # Pan servo (horizontal) - MG996R
    'SERVO_TILT': 13,   # Tilt servo (vertical) - MG996R
}

# Sensor Thresholds
SENSOR_THRESHOLDS = {
    'ULTRASONIC_MIN': 2.0,  # cm
    'ULTRASONIC_MAX': 10.0,  # cm
    'TILT_THRESHOLD': 5.0,   # degrees
}

# Piezo Sensor Settings (Tap Test / Hollow Detection)
PIEZO_SENSOR = {
    'TAP_THRESHOLD': 0.05,  # Minimum seconds between taps
    'SAMPLE_WINDOW': 0.5,   # Seconds to analyze vibration after tap
    'HOLLOW_DURATION_THRESHOLD': 0.15,  # Minimum duration (seconds) to consider hollow
    'AUTO_TAP_DETECTION': True,  # Automatically detect taps in monitoring loop
}

# Buzzer Settings
BUZZER_DURATION_SHORT = 0.1
BUZZER_DURATION_MEDIUM = 0.2
BUZZER_DURATION_LONG = 0.3

# Flask Settings
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000
FLASK_DEBUG = True

# Camera Settings
CAMERA_IMAGE_FOLDER = '~/sitescan_images'
CAMERA_ENABLE_CRACK_DETECTION = True
CAMERA_CRACK_THRESHOLD = 0.15  # Sensitivity (0.0-1.0, lower = more sensitive)
CAMERA_CRACK_SCAN_INTERVAL = 5.0  # Seconds between automatic crack scans

# Crack Detection Settings
CRACK_DETECTION = {
    'MIN_CRACK_LENGTH': 50,  # pixels
    'EDGE_LOW_THRESHOLD': 50,
    'EDGE_HIGH_THRESHOLD': 150,
}

# Servo Settings (MG996R)
SERVO_CONFIG = {
    'ENABLED': True,  # Enable/disable servo control
    'PAN_RANGE': (0.0, 180.0),  # Pan servo angle range (min, max)
    'TILT_RANGE': (0.0, 180.0),  # Tilt servo angle range (min, max)
    'DEFAULT_PAN': 90.0,  # Default pan angle (center)
    'DEFAULT_TILT': 90.0,  # Default tilt angle (center)
    'SCAN_ENABLED': False,  # Enable automatic scanning patterns
    'SCAN_INTERVAL': 10.0,  # Seconds between scans (if enabled)
}

# Logging Settings
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

