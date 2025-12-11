from picamera2 import Picamera2
import time
import os
import logging
from typing import Optional, Dict
from pathlib import Path

# Import crack detector (optional - will fail gracefully if OpenCV not available)
CRACK_DETECTION_AVAILABLE = False
CRACK_DETECTION_ERROR = None

try:
    import cv2
    import numpy as np
    from crack_detector import CrackDetector
    CRACK_DETECTION_AVAILABLE = True
except ImportError as e:
    CRACK_DETECTION_ERROR = str(e)
    logger = logging.getLogger(__name__)
    if 'cv2' in str(e) or 'opencv' in str(e).lower():
        logger.warning("Crack detection not available: OpenCV (cv2) not installed. Install with: pip3 install opencv-python")
    else:
        logger.warning(f"Crack detection not available: {e}")
except Exception as e:
    CRACK_DETECTION_ERROR = str(e)
    logger = logging.getLogger(__name__)
    logger.warning(f"Crack detection not available: {e}")

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

class SiteScanCamera:
    """
    Camera module for capturing images when anomalies are detected.
    Includes crack detection functionality for floor tile analysis.
    Uses Raspberry Pi Camera Module v2 or compatible.
    """
    
    def __init__(self, image_folder: str = "~/sitescan_images", 
                 enable_crack_detection: bool = True,
                 crack_threshold: float = 0.15):
        """
        Initialize the camera module.
        
        Args:
            image_folder: Path to folder where images will be saved
            enable_crack_detection: Enable automatic crack detection on captured images
            crack_threshold: Sensitivity threshold for crack detection (0.0-1.0)
        """
        try:
            self.picam = Picamera2()
            self.picam.configure(self.picam.create_still_configuration())
            self.picam.start()
            time.sleep(0.5)  # Allow camera to initialize

            # Create image folder if it doesn't exist
            self.folder = os.path.expanduser(image_folder)
            if not os.path.exists(self.folder):
                os.makedirs(self.folder)
                logger.info(f"Created image folder: {self.folder}")

            # Initialize crack detector if available
            self.enable_crack_detection = enable_crack_detection and CRACK_DETECTION_AVAILABLE
            if self.enable_crack_detection:
                try:
                    self.crack_detector = CrackDetector(crack_threshold=crack_threshold)
                    logger.info("Crack detection enabled")
                except Exception as e:
                    logger.error(f"Failed to initialize crack detector: {e}")
                    self.enable_crack_detection = False
                    self.crack_detector = None
            else:
                self.crack_detector = None
                if enable_crack_detection:
                    error_msg = CRACK_DETECTION_ERROR or "OpenCV not installed"
                    logger.warning(f"Crack detection requested but not available: {error_msg}")
                    logger.warning("Install with: pip3 install opencv-python numpy")

            logger.info(f"Camera ready. Images will be saved to: {self.folder}")
        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            raise

    def capture(self, reason: str = "general", detect_cracks: bool = True) -> Optional[str]:
        """
        Capture an image and save it with a timestamp.
        
        Args:
            reason: Reason for capture (e.g., "floor_uneven", "vibration_anomaly", "crack_scan")
            detect_cracks: If True and crack detection is enabled, analyze image for cracks
            
        Returns:
            Optional[str]: Path to saved image file, or None on error
        """
        try:
            timestamp = int(time.time())
            filename = os.path.join(self.folder, f"sitescan_{reason}_{timestamp}.jpg")
            self.picam.capture_file(filename)
            logger.info(f"Captured image: {filename}")
            
            # Perform crack detection if enabled
            if detect_cracks and self.enable_crack_detection:
                crack_result = self.crack_detector.detect_cracks(filename, save_annotated=True)
                if crack_result["detected"]:
                    logger.warning(f"CRACK DETECTED! Confidence: {crack_result['confidence']:.2f}, "
                                 f"Cracks found: {crack_result['crack_count']}")
                    return filename
            
            return filename
        except Exception as e:
            logger.error(f"Error capturing image: {e}")
            return None

    def scan_for_cracks(self) -> Dict:
        """
        Capture an image and scan it for cracks.
        
        Returns:
            Dict with crack detection results:
                - detected: bool
                - confidence: float
                - crack_count: int
                - image_path: str (path to captured image)
                - annotated_path: str (path to annotated image, if cracks found)
        """
        try:
            # Capture image
            image_path = self.capture("crack_scan", detect_cracks=False)
            if not image_path:
                return {
                    "detected": False,
                    "confidence": 0.0,
                    "crack_count": 0,
                    "image_path": None,
                    "annotated_path": None
                }
            
            # Detect cracks
            if self.enable_crack_detection:
                result = self.crack_detector.detect_cracks(image_path, save_annotated=True)
                result["image_path"] = image_path
                return result
            else:
                error_msg = CRACK_DETECTION_ERROR or "OpenCV not installed"
                return {
                    "detected": False,
                    "confidence": 0.0,
                    "crack_count": 0,
                    "image_path": image_path,
                    "annotated_path": None,
                    "error": f"Crack detection not available: {error_msg}. Install with: pip3 install opencv-python numpy"
                }
        except Exception as e:
            logger.error(f"Error scanning for cracks: {e}")
            return {
                "detected": False,
                "confidence": 0.0,
                "crack_count": 0,
                "image_path": None,
                "annotated_path": None,
                "error": str(e)
            }

    def stop(self) -> None:
        """Stop the camera and release resources."""
        try:
            self.picam.stop()
            logger.info("Camera stopped")
        except Exception as e:
            logger.error(f"Error stopping camera: {e}")
