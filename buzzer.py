import RPi.GPIO as GPIO
import time
import logging

logger = logging.getLogger(__name__)

class Buzzer:
    """
    Buzzer control module for audio alerts.
    
    Args:
        pin: GPIO pin number (BCM mode) connected to the buzzer
    """
    
    def __init__(self, pin: int):
        """
        Initialize the buzzer.
        
        Args:
            pin: GPIO pin number (BCM mode)
        """
        self.pin = pin
        try:
            GPIO.setup(self.pin, GPIO.OUT)
            GPIO.output(self.pin, GPIO.LOW)
            logger.info(f"Buzzer initialized on pin {pin}")
        except Exception as e:
            logger.error(f"Failed to initialize Buzzer on pin {pin}: {e}")
            raise

    def beep(self, duration: float = 0.2) -> None:
        """
        Activate the buzzer for a specified duration.
        
        Args:
            duration: Duration in seconds to keep buzzer on
        """
        try:
            GPIO.output(self.pin, GPIO.HIGH)
            time.sleep(duration)
            GPIO.output(self.pin, GPIO.LOW)
            logger.debug(f"Buzzer beeped for {duration}s")
        except Exception as e:
            logger.error(f"Error controlling buzzer on pin {self.pin}: {e}")
