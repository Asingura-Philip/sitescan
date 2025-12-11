"""
Crack detection module using computer vision.
Analyzes images to detect floor tile cracks.
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

class CrackDetector:
    """
    Detects cracks in floor tile images using computer vision techniques.
    Uses edge detection and line analysis to identify crack patterns.
    """
    
    def __init__(self, 
                 crack_threshold: float = 0.15,
                 min_crack_length: int = 50,
                 edge_low_threshold: int = 50,
                 edge_high_threshold: int = 150):
        """
        Initialize the crack detector.
        
        Args:
            crack_threshold: Minimum crack density to consider a crack detected (0.0-1.0)
            min_crack_length: Minimum length in pixels for a crack to be considered
            edge_low_threshold: Lower threshold for Canny edge detection
            edge_high_threshold: Upper threshold for Canny edge detection
        """
        self.crack_threshold = crack_threshold
        self.min_crack_length = min_crack_length
        self.edge_low_threshold = edge_low_threshold
        self.edge_high_threshold = edge_high_threshold
        logger.info(f"CrackDetector initialized with threshold={crack_threshold}")
    
    def detect_cracks(self, image_path: str, save_annotated: bool = True) -> Dict:
        """
        Detect cracks in an image.
        
        Args:
            image_path: Path to the image file
            save_annotated: If True, save an annotated version with detected cracks marked
            
        Returns:
            Dict with keys:
                - detected: bool, whether cracks were detected
                - confidence: float, confidence score (0.0-1.0)
                - crack_count: int, number of cracks found
                - annotated_path: str, path to annotated image (if saved)
        """
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"Could not read image: {image_path}")
                return {
                    "detected": False,
                    "confidence": 0.0,
                    "crack_count": 0,
                    "annotated_path": None
                }
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Edge detection using Canny
            edges = cv2.Canny(blurred, self.edge_low_threshold, self.edge_high_threshold)
            
            # Use HoughLinesP to detect line segments (cracks often appear as lines)
            lines = cv2.HoughLinesP(
                edges,
                rho=1,
                theta=np.pi/180,
                threshold=50,
                minLineLength=self.min_crack_length,
                maxLineGap=20
            )
            
            # Analyze detected lines
            crack_count = 0
            annotated_img = img.copy()
            
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    
                    # Calculate line length
                    length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                    
                    # Filter by length and angle (cracks are typically longer and more linear)
                    if length >= self.min_crack_length:
                        # Draw detected crack line
                        cv2.line(annotated_img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        crack_count += 1
            
            # Calculate crack density (ratio of crack pixels to total image area)
            edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
            
            # Calculate confidence based on crack count and edge density
            confidence = min(1.0, (crack_count * 0.1) + (edge_density * 2.0))
            
            # Determine if cracks are detected
            detected = confidence >= self.crack_threshold or crack_count > 0
            
            result = {
                "detected": detected,
                "confidence": round(confidence, 3),
                "crack_count": crack_count,
                "edge_density": round(edge_density, 3),
                "annotated_path": None
            }
            
            # Save annotated image if requested
            if save_annotated and (detected or crack_count > 0):
                annotated_path = self._save_annotated_image(image_path, annotated_img, edges)
                result["annotated_path"] = annotated_path
            
            logger.info(f"Crack detection: detected={detected}, confidence={confidence:.3f}, "
                       f"cracks={crack_count}, density={edge_density:.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error detecting cracks in {image_path}: {e}")
            return {
                "detected": False,
                "confidence": 0.0,
                "crack_count": 0,
                "annotated_path": None
            }
    
    def _save_annotated_image(self, original_path: str, annotated_img: np.ndarray, 
                              edges: np.ndarray) -> str:
        """
        Save annotated image with detected cracks marked.
        
        Args:
            original_path: Path to original image
            annotated_img: Image with crack annotations
            edges: Edge detection result
            
        Returns:
            Path to saved annotated image
        """
        try:
            original_path_obj = Path(original_path)
            annotated_path = original_path_obj.parent / f"{original_path_obj.stem}_cracks{original_path_obj.suffix}"
            
            # Create side-by-side comparison (original + annotated + edges)
            h, w = annotated_img.shape[:2]
            comparison = np.zeros((h, w * 3, 3), dtype=np.uint8)
            
            # Original image
            comparison[:, :w] = cv2.imread(original_path)
            
            # Annotated image
            comparison[:, w:w*2] = annotated_img
            
            # Edge detection visualization
            edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            comparison[:, w*2:] = edges_colored
            
            cv2.imwrite(str(annotated_path), comparison)
            logger.info(f"Saved annotated image: {annotated_path}")
            return str(annotated_path)
            
        except Exception as e:
            logger.error(f"Error saving annotated image: {e}")
            return original_path

