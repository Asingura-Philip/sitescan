# SiteScan Robot

An embedded systems project for monitoring floor conditions using various sensors on a Raspberry Pi. The robot detects floor unevenness, vibrations, and obstacles using ultrasonic, IMU, piezo, and IR sensors.

## Features

- **Ultrasonic Sensor**: Measures distance to detect floor height variations
- **IMU (MPU6050)**: Monitors pitch and roll to detect floor tilt
- **Piezo Sensor**: Advanced tap test for detecting hollow vs solid tiles using vibration pattern analysis
- **IR Sensor**: Obstacle detection
- **Buzzer**: Audio alerts for detected issues
- **Dual MG996R Servos**: Pan/tilt control for camera positioning and scanning
- **Camera Module**: Image capture on anomalies with **automatic crack detection**
- **Crack Detection**: Computer vision-based floor tile crack detection using OpenCV
- **Web Dashboard**: Real-time sensor monitoring with servo controls and manual crack scanning

## Hardware Requirements

- Raspberry Pi (with GPIO support)
- Ultrasonic sensor (HC-SR04 or similar)
- MPU6050 IMU sensor
- Piezo vibration sensor
- IR obstacle sensor
- Buzzer module
- 2x MG996R servo motors (for pan/tilt mechanism)
- Optional: Raspberry Pi Camera Module

## Software Requirements

- Python 3.7+
- Raspberry Pi OS (or compatible Linux distribution)
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone or download this repository:
```bash
cd proj
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

3. Ensure I2C is enabled for MPU6050:
```bash
sudo raspi-config
# Navigate to Interface Options > I2C > Enable
```

4. Wire your sensors according to the GPIO pin configuration in `config.py`

## Usage

### Command Line Mode

Run the main sensor monitoring script:
```bash
python3 main.py
```

This will continuously monitor all sensors and print readings to the console. Press `Ctrl+C` to stop.

### Web Dashboard Mode

Run the Flask web server:
```bash
python3 mainflask.py
```

Then open your web browser and navigate to:
```
http://<raspberry-pi-ip>:5000
```

The dashboard will update sensor readings every second.

### Tap Test / Hollow Tile Detection

The piezo sensor performs automated "tap tests" to detect hollow vs solid tiles:

- **How it works**: When you tap the floor, the sensor analyzes the vibration pattern:
  - **Vibration Duration**: Hollow tiles vibrate longer than solid ones
  - **Oscillation Count**: Number of vibration cycles detected
  - **Decay Pattern**: How quickly vibrations fade
  
- **Detection**: The system automatically detects taps and analyzes the response
- **Alerts**: Triggers buzzer alerts when hollow tiles are detected
- **Calibration**: Use `piezo.set_baseline()` to calibrate on known solid tiles for better accuracy

**Usage**: Simply tap the floor tile with a small hammer or mallet. The system will automatically detect and analyze the tap. Hollow tiles typically produce longer-duration vibrations with more oscillations.

### Servo Control (Pan/Tilt)

The dual MG996R servo system provides pan/tilt control for camera positioning and automated scanning:

- **Manual Control**: Use sliders in the web dashboard to control pan and tilt angles
- **Automated Scanning**: Perform grid, horizontal, vertical, or circular scan patterns
- **Camera Positioning**: Position camera for optimal crack detection and image capture
- **Center Function**: Quickly return servos to center position (90°, 90°)

**Web Controls**:
- Pan/Tilt sliders for real-time positioning
- Center button to return to default position
- Scan pattern buttons for automated scanning
- Real-time position display

**Configuration** (`SERVO_CONFIG` in `config.py`):
- `ENABLED`: Enable/disable servo control
- `PAN_RANGE`: Pan servo angle range (default: 0-180°)
- `TILT_RANGE`: Tilt servo angle range (default: 0-180°)
- `SCAN_ENABLED`: Enable automatic periodic scanning
- `SCAN_INTERVAL`: Seconds between automatic scans

### Crack Detection

The camera module includes automatic crack detection using computer vision:

- **Automatic Scanning**: Periodically scans for cracks (configurable interval in `config.py`)
- **Manual Scanning**: Use the "Scan for Cracks" button in the web dashboard
- **Alert System**: Automatically triggers buzzer alerts when cracks are detected
- **Annotated Images**: Saves images with detected cracks marked in red
- **Confidence Scores**: Provides detection confidence and crack count

Crack detection uses edge detection and line analysis algorithms optimized for floor tile cracks. Adjust sensitivity via `CAMERA_CRACK_THRESHOLD` in `config.py` (lower = more sensitive).

**Image Upload**: You can upload images of cracked tiles directly through the web dashboard:
- Click "Choose Image File" to select an image
- Click "Analyze Image" to process it
- View detection results with confidence scores
- See side-by-side comparison of original and annotated images
- Supported formats: PNG, JPG, JPEG, GIF, BMP

## Project Structure

```
proj/
├── main.py              # Command-line sensor monitoring
├── mainflask.py         # Flask web server
├── config.py            # Centralized configuration
├── gpio_init.py         # GPIO initialization helper
├── buzzer.py            # Buzzer control module
├── camera_module.py     # Camera capture module with crack detection
├── crack_detector.py    # Computer vision crack detection module
├── imu_mpu6050.py       # MPU6050 IMU sensor module
├── ir_sensor.py         # IR obstacle sensor module
├── piezo_sensor.py      # Enhanced piezo sensor with tap test/hollow detection
├── servo_controller.py  # Dual MG996R servo controller with pan/tilt support
├── ultrasonic.py        # Ultrasonic distance sensor module
├── templates/
│   └── index.html       # Web dashboard HTML
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Configuration

All GPIO pins and thresholds can be configured in `config.py`. Modify the values according to your hardware setup.

**Piezo Sensor Configuration** (`PIEZO_SENSOR` in `config.py`):
- `TAP_THRESHOLD`: Minimum seconds between taps (default: 0.05s)
- `SAMPLE_WINDOW`: Time window to analyze vibration after tap (default: 0.5s)
- `HOLLOW_DURATION_THRESHOLD`: Minimum vibration duration to consider hollow (default: 0.15s)

Adjust these values based on your tile type and sensor sensitivity. For better accuracy, calibrate the sensor using `piezo.set_baseline()` on a known solid tile.

## Troubleshooting

- **GPIO errors**: Ensure you're running with appropriate permissions (may need `sudo` or add user to `gpio` group)
- **I2C errors**: Verify I2C is enabled and MPU6050 is properly connected
- **Camera errors**: Ensure camera is enabled in `raspi-config` if using camera module
- **Import errors**: Make sure all dependencies are installed via `pip3 install -r requirements.txt`
- **OpenCV errors**: If crack detection fails, ensure `opencv-python` is installed: `pip3 install opencv-python`
- **Crack detection not working**: Check that camera is properly initialized and images are being captured. Review logs for detection confidence scores.

## License

This project is provided as-is for educational and development purposes.

