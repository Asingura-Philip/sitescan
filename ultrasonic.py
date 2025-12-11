import RPi.GPIO as GPIO
import time
import logging

logger = logging.getLogger(__name__)

class Ultrasonic:
    """
    Ultrasonic distance sensor module (HC-SR04 or similar).
    
    Args:
        trig: GPIO pin number (BCM mode) for trigger
        echo: GPIO pin number (BCM mode) for echo
    """
    
    def __init__(self, trig: int, echo: int):
        """
        Initialize the ultrasonic sensor.
        
        Args:
            trig: Trigger pin number (BCM mode)
            echo: Echo pin number (BCM mode)
        """
        self.trig = trig
        self.echo = echo
        try:
            GPIO.setup(self.trig, GPIO.OUT)
            GPIO.setup(self.echo, GPIO.IN)
            GPIO.output(self.trig, GPIO.LOW)
            logger.info(f"Ultrasonic sensor initialized: TRIG={trig}, ECHO={echo}")
        except Exception as e:
            logger.error(f"Failed to initialize Ultrasonic sensor: {e}")
            raise

    def distance(self) -> float:
        """
        Measure distance using ultrasonic sensor.
        
        Returns:
            float: Distance in centimeters. Returns -1.0 on error.
        """
        try:
            # Send trigger pulse
            GPIO.output(self.trig, GPIO.HIGH)
            time.sleep(0.00001)  # 10 microseconds
            GPIO.output(self.trig, GPIO.LOW)

            # Wait for echo to start
            timeout = time.time() + 0.1  # 100ms timeout
            while GPIO.input(self.echo) == GPIO.LOW:
                if time.time() > timeout:
                    logger.warning("Ultrasonic sensor timeout waiting for echo start")
                    return -1.0
                start = time.time()

            # Wait for echo to end
            timeout = time.time() + 0.1  # 100ms timeout
            while GPIO.input(self.echo) == GPIO.HIGH:
                if time.time() > timeout:
                    logger.warning("Ultrasonic sensor timeout waiting for echo end")
                    return -1.0
                stop = time.time()

            elapsed = stop - start
            # Speed of sound = 343 m/s = 34300 cm/s
            # Distance = (time * speed) / 2 (round trip)
            distance = (elapsed * 34300) / 2
            
            # Sanity check
            if distance < 0 or distance > 400:  # HC-SR04 range is 2-400cm
                logger.warning(f"Ultrasonic reading out of range: {distance} cm")
                return -1.0
                
            return distance
        except Exception as e:
            logger.error(f"Error reading ultrasonic sensor: {e}")
            return -1.0
