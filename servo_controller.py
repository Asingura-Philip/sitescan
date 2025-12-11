import RPi.GPIO as GPIO
import time
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class Servo:
    """
    Servo motor controller module optimized for MG996R high-torque servos.
    Supports standard 180-degree servo motors with improved control.
    
    MG996R Specifications:
    - Operating voltage: 4.8V - 7.2V
    - Stall torque: 9.4kg/cm @ 4.8V, 11kg/cm @ 6V
    - Speed: 0.17s/60° @ 4.8V, 0.13s/60° @ 6V
    - Weight: 55g
    - Angle range: 0-180 degrees
    """
    
    def __init__(self, pin: int, min_angle: float = 0.0, max_angle: float = 180.0,
                 min_pulse: float = 0.5, max_pulse: float = 2.5):
        """
        Initialize the servo controller.
        
        Args:
            pin: GPIO pin number (BCM mode) connected to the servo signal wire
            min_angle: Minimum angle in degrees (default: 0)
            max_angle: Maximum angle in degrees (default: 180)
            min_pulse: Minimum pulse width in milliseconds (default: 0.5ms for MG996R)
            max_pulse: Maximum pulse width in milliseconds (default: 2.5ms for MG996R)
        """
        self.pin = pin
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.min_pulse = min_pulse
        self.max_pulse = max_pulse
        self.current_angle = 90.0  # Default center position
        
        try:
            GPIO.setup(self.pin, GPIO.OUT)
            self.pwm = GPIO.PWM(self.pin, 50)  # 50Hz frequency for servos
            self.pwm.start(0)
            # Move to center position on initialization
            self.angle(90.0, immediate=True)
            logger.info(f"Servo initialized on pin {pin} (MG996R)")
        except Exception as e:
            logger.error(f"Failed to initialize Servo on pin {pin}: {e}")
            raise

    def angle(self, angle: float, immediate: bool = False) -> None:
        """
        Set the servo to a specific angle.
        
        Args:
            angle: Target angle in degrees (clamped to min_angle-max_angle)
            immediate: If True, don't wait for servo to reach position (faster)
        """
        try:
            # Clamp angle to valid range
            angle = max(self.min_angle, min(self.max_angle, angle))
            self.current_angle = angle
            
            # Convert angle to duty cycle
            # MG996R uses 0.5ms (0°) to 2.5ms (180°) pulse width
            # At 50Hz, period is 20ms
            pulse_width_ms = self.min_pulse + (angle / 180.0) * (self.max_pulse - self.min_pulse)
            duty_cycle = (pulse_width_ms / 20.0) * 100.0  # Convert to percentage
            
            self.pwm.ChangeDutyCycle(duty_cycle)
            
            if not immediate:
                # Calculate wait time based on angle change (MG996R speed: ~0.15s/60°)
                angle_change = abs(angle - self.current_angle)
                wait_time = (angle_change / 60.0) * 0.15
                wait_time = max(0.1, min(wait_time, 0.5))  # Clamp between 0.1s and 0.5s
                time.sleep(wait_time)
            
            logger.debug(f"Servo pin {self.pin} set to {angle:.1f}° (duty: {duty_cycle:.2f}%)")
        except Exception as e:
            logger.error(f"Error setting servo angle on pin {self.pin}: {e}")

    def get_angle(self) -> float:
        """Get the current servo angle."""
        return self.current_angle

    def center(self) -> None:
        """Move servo to center position (90°)."""
        self.angle(90.0)

    def sweep(self, start_angle: float = 0.0, end_angle: float = 180.0, 
              step: float = 1.0, delay: float = 0.05) -> None:
        """
        Sweep the servo through a range of angles.
        
        Args:
            start_angle: Starting angle in degrees
            end_angle: Ending angle in degrees
            step: Angle step size in degrees
            delay: Delay between steps in seconds
        """
        try:
            if start_angle < end_angle:
                angles = [a for a in range(int(start_angle), int(end_angle) + 1, int(step))]
            else:
                angles = [a for a in range(int(start_angle), int(end_angle) - 1, -int(step))]
            
            for angle in angles:
                self.angle(angle, immediate=True)
                time.sleep(delay)
        except Exception as e:
            logger.error(f"Error during servo sweep: {e}")

    def cleanup(self) -> None:
        """Stop PWM and cleanup GPIO resources."""
        try:
            self.pwm.stop()
            logger.info(f"Servo on pin {self.pin} cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up servo on pin {self.pin}: {e}")


class DualServoController:
    """
    Controller for managing two MG996R servos (e.g., pan/tilt mechanism).
    Useful for camera positioning, sensor scanning, or other dual-axis applications.
    """
    
    def __init__(self, pan_pin: int, tilt_pin: int, 
                 pan_range: Tuple[float, float] = (0.0, 180.0),
                 tilt_range: Tuple[float, float] = (0.0, 180.0)):
        """
        Initialize dual servo controller.
        
        Args:
            pan_pin: GPIO pin for pan servo (horizontal movement)
            tilt_pin: GPIO pin for tilt servo (vertical movement)
            pan_range: (min, max) angle range for pan servo
            tilt_range: (min, max) angle range for tilt servo
        """
        try:
            self.pan_servo = Servo(pan_pin, min_angle=pan_range[0], max_angle=pan_range[1])
            self.tilt_servo = Servo(tilt_pin, min_angle=tilt_range[0], max_angle=tilt_range[1])
            logger.info(f"DualServoController initialized: Pan pin {pan_pin}, Tilt pin {tilt_pin}")
        except Exception as e:
            logger.error(f"Failed to initialize DualServoController: {e}")
            raise

    def set_position(self, pan_angle: float, tilt_angle: float, 
                     immediate: bool = False) -> None:
        """
        Set both servos to specific angles.
        
        Args:
            pan_angle: Pan servo angle in degrees
            tilt_angle: Tilt servo angle in degrees
            immediate: If True, don't wait for servos to reach position
        """
        try:
            self.pan_servo.angle(pan_angle, immediate=immediate)
            self.tilt_servo.angle(tilt_angle, immediate=immediate)
            logger.debug(f"Servos set to: Pan={pan_angle:.1f}°, Tilt={tilt_angle:.1f}°")
        except Exception as e:
            logger.error(f"Error setting servo positions: {e}")

    def get_position(self) -> Tuple[float, float]:
        """
        Get current pan and tilt angles.
        
        Returns:
            Tuple of (pan_angle, tilt_angle)
        """
        return (self.pan_servo.get_angle(), self.tilt_servo.get_angle())

    def center(self) -> None:
        """Move both servos to center position (90°, 90°)."""
        self.set_position(90.0, 90.0)

    def scan_pattern(self, pattern: str = "grid", steps: int = 5) -> None:
        """
        Perform automated scanning patterns.
        
        Args:
            pattern: Scan pattern type ("grid", "horizontal", "vertical", "circular")
            steps: Number of steps in the pattern
        """
        try:
            if pattern == "grid":
                # Grid scan: pan left-right, tilt up-down
                pan_angles = [0, 45, 90, 135, 180][:steps]
                tilt_angles = [45, 90, 135][:steps]
                for pan in pan_angles:
                    for tilt in tilt_angles:
                        self.set_position(pan, tilt)
                        time.sleep(0.2)
            
            elif pattern == "horizontal":
                # Horizontal sweep
                for angle in range(0, 181, 180 // steps):
                    self.set_position(angle, 90.0)
                    time.sleep(0.1)
            
            elif pattern == "vertical":
                # Vertical sweep
                for angle in range(0, 181, 180 // steps):
                    self.set_position(90.0, angle)
                    time.sleep(0.1)
            
            elif pattern == "circular":
                # Circular pattern
                import math
                center_pan, center_tilt = 90.0, 90.0
                radius = 30.0
                for i in range(steps * 4):
                    angle_rad = (i / (steps * 4)) * 2 * math.pi
                    pan = center_pan + radius * math.cos(angle_rad)
                    tilt = center_tilt + radius * math.sin(angle_rad)
                    self.set_position(pan, tilt)
                    time.sleep(0.1)
            
            # Return to center
            self.center()
            logger.info(f"Scan pattern '{pattern}' completed")
        except Exception as e:
            logger.error(f"Error during scan pattern: {e}")

    def cleanup(self) -> None:
        """Cleanup both servos."""
        try:
            self.pan_servo.cleanup()
            self.tilt_servo.cleanup()
            logger.info("DualServoController cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up DualServoController: {e}")
