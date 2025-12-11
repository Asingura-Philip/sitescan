import RPi.GPIO as GPIO
import time
import logging
from typing import Dict, Optional, List
from collections import deque

logger = logging.getLogger(__name__)

class PiezoSensor:
    """
    Enhanced piezo sensor module for detecting vibrations and analyzing tap responses.
    Uses vibration pattern analysis to distinguish between hollow and solid tiles.
    
    The sensor detects taps/impacts and analyzes:
    - Vibration duration (how long the vibration lasts)
    - Vibration intensity (number of oscillations)
    - Decay pattern (how quickly vibrations fade)
    
    Hollow tiles typically produce:
    - Longer vibration duration
    - More oscillations
    - Different frequency characteristics
    - Different decay patterns
    """
    
    def __init__(self, pin: int, 
                 tap_threshold: float = 0.05,
                 sample_window: float = 0.5,
                 hollow_duration_threshold: float = 0.15):
        """
        Initialize the piezo sensor.
        
        Args:
            pin: GPIO pin number (BCM mode)
            tap_threshold: Minimum time between taps to consider separate events (seconds)
            sample_window: Time window to analyze vibration after a tap (seconds)
            hollow_duration_threshold: Minimum vibration duration to consider hollow (seconds)
        """
        self.pin = pin
        self.tap_threshold = tap_threshold
        self.sample_window = sample_window
        self.hollow_duration_threshold = hollow_duration_threshold
        
        # State tracking
        self.last_tap_time = 0
        self.vibration_samples = deque(maxlen=100)  # Store recent vibration patterns
        self.baseline_pattern = None  # Baseline for solid tile comparison
        
        try:
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            logger.info(f"PiezoSensor initialized on pin {pin}")
            logger.info(f"  Tap threshold: {tap_threshold}s, Sample window: {sample_window}s")
        except Exception as e:
            logger.error(f"Failed to initialize PiezoSensor on pin {pin}: {e}")
            raise

    def detect(self) -> int:
        """
        Simple binary detection (backward compatibility).
        
        Returns:
            int: Sensor reading (0 or 1)
        """
        try:
            return GPIO.input(self.pin)
        except Exception as e:
            logger.error(f"Error reading piezo sensor on pin {self.pin}: {e}")
            return 0

    def detect_tap(self) -> bool:
        """
        Detect if a tap/impact has occurred.
        
        Returns:
            bool: True if a tap is detected
        """
        try:
            current_value = GPIO.input(self.pin)
            current_time = time.time()
            
            # Detect rising edge (tap start)
            if current_value == GPIO.HIGH:
                time_since_last = current_time - self.last_tap_time
                if time_since_last > self.tap_threshold:
                    self.last_tap_time = current_time
                    return True
            return False
        except Exception as e:
            logger.error(f"Error detecting tap: {e}")
            return False

    def analyze_vibration(self) -> Optional[Dict]:
        """
        Analyze vibration pattern after a detected tap.
        This method should be called immediately after detect_tap() returns True.
        
        Returns:
            Dict with vibration analysis:
                - duration: float, vibration duration in seconds
                - oscillation_count: int, number of oscillations detected
                - max_intensity: float, maximum vibration intensity
                - decay_rate: float, how quickly vibration decays
                - pattern: str, "solid", "hollow", or "unknown"
        """
        try:
            start_time = time.time()
            end_time = start_time + self.sample_window
            
            oscillations = 0
            last_state = GPIO.input(self.pin)
            state_changes = []
            max_intensity_time = 0
            
            # Sample vibration pattern
            while time.time() < end_time:
                current_state = GPIO.input(self.pin)
                current_time = time.time()
                
                # Count oscillations (state changes)
                if current_state != last_state:
                    oscillations += 1
                    state_changes.append((current_time - start_time, current_state))
                    
                    # Track when we have maximum activity
                    if oscillations > max_intensity_time:
                        max_intensity_time = oscillations
                
                last_state = current_state
                time.sleep(0.001)  # 1ms sampling rate
            
            # Calculate duration (time until vibrations stop)
            duration = 0.0
            if state_changes:
                # Find last significant state change
                for i in range(len(state_changes) - 1, max(0, len(state_changes) - 10), -1):
                    if state_changes[i][1] == GPIO.HIGH:
                        duration = state_changes[i][0]
                        break
                
                # If still vibrating, use full sample window
                if duration == 0:
                    duration = self.sample_window
            
            # Calculate decay rate (oscillations per second decrease)
            decay_rate = 0.0
            if len(state_changes) > 10:
                # Compare first half vs second half
                mid_point = len(state_changes) // 2
                first_half_osc = mid_point
                second_half_osc = len(state_changes) - mid_point
                if first_half_osc > 0:
                    decay_rate = second_half_osc / first_half_osc
            
            # Determine pattern
            pattern = self._classify_pattern(duration, oscillations, decay_rate)
            
            result = {
                "duration": round(duration, 3),
                "oscillation_count": oscillations,
                "max_intensity": max_intensity_time,
                "decay_rate": round(decay_rate, 3),
                "pattern": pattern,
                "timestamp": time.time()
            }
            
            # Store for baseline comparison
            self.vibration_samples.append(result)
            
            logger.debug(f"Vibration analysis: duration={duration:.3f}s, "
                        f"oscillations={oscillations}, pattern={pattern}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing vibration: {e}")
            return None

    def _classify_pattern(self, duration: float, oscillations: int, decay_rate: float) -> str:
        """
        Classify vibration pattern as solid or hollow.
        
        Args:
            duration: Vibration duration in seconds
            oscillations: Number of oscillations
            decay_rate: Decay rate (lower = faster decay)
            
        Returns:
            str: "solid", "hollow", or "unknown"
        """
        # Hollow tiles typically:
        # - Vibrate longer (duration > threshold)
        # - Have more oscillations
        # - Different decay characteristics
        
        if duration >= self.hollow_duration_threshold:
            # Long duration suggests hollow
            if oscillations > 5:
                return "hollow"
            else:
                return "unknown"
        elif duration < 0.05:
            # Very short duration suggests solid
            return "solid"
        else:
            # Medium duration - use oscillation count
            if oscillations > 8:
                return "hollow"
            elif oscillations < 3:
                return "solid"
            else:
                return "unknown"

    def tap_test(self) -> Dict:
        """
        Perform a complete tap test: detect tap and analyze vibration.
        This is the main method for detecting hollow vs solid tiles.
        
        Returns:
            Dict with tap test results:
                - tap_detected: bool
                - vibration_analysis: Dict or None
                - is_hollow: bool or None
        """
        tap_detected = self.detect_tap()
        
        if tap_detected:
            logger.info("Tap detected - analyzing vibration pattern...")
            vibration = self.analyze_vibration()
            
            if vibration:
                is_hollow = vibration["pattern"] == "hollow"
                return {
                    "tap_detected": True,
                    "vibration_analysis": vibration,
                    "is_hollow": is_hollow,
                    "confidence": self._calculate_confidence(vibration)
                }
            else:
                return {
                    "tap_detected": True,
                    "vibration_analysis": None,
                    "is_hollow": None,
                    "confidence": 0.0
                }
        else:
            return {
                "tap_detected": False,
                "vibration_analysis": None,
                "is_hollow": None,
                "confidence": 0.0
            }

    def _calculate_confidence(self, vibration: Dict) -> float:
        """
        Calculate confidence score for the pattern classification.
        
        Args:
            vibration: Vibration analysis dictionary
            
        Returns:
            float: Confidence score (0.0-1.0)
        """
        pattern = vibration["pattern"]
        duration = vibration["duration"]
        oscillations = vibration["oscillation_count"]
        
        if pattern == "unknown":
            return 0.3
        
        # Higher confidence for clear patterns
        if pattern == "hollow":
            # More confidence if duration is well above threshold
            duration_ratio = duration / self.hollow_duration_threshold
            osc_ratio = min(oscillations / 10.0, 1.0)
            return min(0.5 + (duration_ratio * 0.3) + (osc_ratio * 0.2), 1.0)
        else:  # solid
            # More confidence if duration is very short
            if duration < 0.03:
                return 0.8
            elif duration < 0.05:
                return 0.6
            else:
                return 0.4

    def set_baseline(self, samples: int = 5) -> bool:
        """
        Set baseline pattern by analyzing multiple taps on a known solid tile.
        This helps calibrate the sensor for better accuracy.
        
        Args:
            samples: Number of tap samples to collect for baseline
            
        Returns:
            bool: True if baseline was successfully set
        """
        logger.info(f"Setting baseline pattern with {samples} samples...")
        baseline_samples = []
        
        for i in range(samples):
            logger.info(f"  Tap {i+1}/{samples} - please tap the tile...")
            start_time = time.time()
            
            # Wait for tap
            while time.time() - start_time < 5.0:  # 5 second timeout
                if self.detect_tap():
                    vibration = self.analyze_vibration()
                    if vibration:
                        baseline_samples.append(vibration)
                        break
                time.sleep(0.01)
            
            if len(baseline_samples) <= i:
                logger.warning(f"  No tap detected for sample {i+1}")
                time.sleep(1)
        
        if len(baseline_samples) >= 3:
            # Calculate average baseline
            avg_duration = sum(s["duration"] for s in baseline_samples) / len(baseline_samples)
            avg_oscillations = sum(s["oscillation_count"] for s in baseline_samples) / len(baseline_samples)
            
            self.baseline_pattern = {
                "duration": avg_duration,
                "oscillation_count": int(avg_oscillations),
                "samples": len(baseline_samples)
            }
            
            logger.info(f"Baseline set: duration={avg_duration:.3f}s, "
                       f"oscillations={avg_oscillations:.1f}")
            return True
        else:
            logger.error("Failed to set baseline - insufficient samples")
            return False

    def get_recent_patterns(self, count: int = 5) -> List[Dict]:
        """
        Get recent vibration patterns for analysis.
        
        Args:
            count: Number of recent patterns to return
            
        Returns:
            List of recent vibration analysis dictionaries
        """
        return list(self.vibration_samples)[-count:]
