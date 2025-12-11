import RPi.GPIO as GPIO
import logging

logger = logging.getLogger(__name__)

class IRSensor:
    """
    IR (Infrared) obstacle sensor module.
    
    Args:
        pin: GPIO pin number (BCM mode) connected to the IR sensor output
    """
    
    def __init__(self, pin: int):
        """
        Initialize the IR sensor.
        
        Args:
            pin: GPIO pin number (BCM mode)
        """
        self.pin = pin
        try:
            GPIO.setup(pin, GPIO.IN)
            logger.info(f"IRSensor initialized on pin {pin}")
        except Exception as e:
            logger.error(f"Failed to initialize IRSensor on pin {pin}: {e}")
            raise

    def is_obstacle(self) -> bool:
        """
        Check if an obstacle is detected.
        
        Returns:
            bool: True if obstacle detected (sensor reads LOW), False otherwise
        """
        try:
            # Most IR sensors output LOW when obstacle is detected
            return GPIO.input(self.pin) == GPIO.LOW
        except Exception as e:
            logger.error(f"Error reading IR sensor on pin {self.pin}: {e}")
            return False
