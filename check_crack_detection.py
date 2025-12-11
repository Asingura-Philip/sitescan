#!/usr/bin/env python3
"""
Diagnostic script to check if crack detection dependencies are properly installed.
Run this to diagnose why crack detection might not be working.
"""

import sys

print("=" * 60)
print("Crack Detection Diagnostic Tool")
print("=" * 60)

# Check Python version
print(f"\n✓ Python version: {sys.version}")

# Check OpenCV
print("\n[1] Checking OpenCV (cv2)...")
try:
    import cv2
    print(f"   ✓ OpenCV version: {cv2.__version__}")
    print("   ✓ OpenCV is installed correctly")
except ImportError as e:
    print(f"   ✗ OpenCV NOT FOUND: {e}")
    print("   → Install with: pip3 install opencv-python")
    sys.exit(1)
except Exception as e:
    print(f"   ✗ Error importing OpenCV: {e}")
    sys.exit(1)

# Check NumPy
print("\n[2] Checking NumPy...")
try:
    import numpy as np
    print(f"   ✓ NumPy version: {np.__version__}")
    print("   ✓ NumPy is installed correctly")
except ImportError as e:
    print(f"   ✗ NumPy NOT FOUND: {e}")
    print("   → Install with: pip3 install numpy")
    sys.exit(1)
except Exception as e:
    print(f"   ✗ Error importing NumPy: {e}")
    sys.exit(1)

# Check crack_detector module
print("\n[3] Checking crack_detector module...")
try:
    from crack_detector import CrackDetector
    print("   ✓ crack_detector module imported successfully")
    
    # Try to instantiate
    detector = CrackDetector()
    print("   ✓ CrackDetector instantiated successfully")
except ImportError as e:
    print(f"   ✗ Cannot import crack_detector: {e}")
    print("   → Check that crack_detector.py exists in the project directory")
    sys.exit(1)
except Exception as e:
    print(f"   ✗ Error with crack_detector: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Check camera module
print("\n[4] Checking camera_module...")
try:
    from camera_module import SiteScanCamera, CRACK_DETECTION_AVAILABLE, CRACK_DETECTION_ERROR
    print(f"   ✓ camera_module imported successfully")
    print(f"   ✓ CRACK_DETECTION_AVAILABLE: {CRACK_DETECTION_AVAILABLE}")
    if CRACK_DETECTION_ERROR:
        print(f"   ⚠ CRACK_DETECTION_ERROR: {CRACK_DETECTION_ERROR}")
    else:
        print("   ✓ No errors detected")
except ImportError as e:
    print(f"   ✗ Cannot import camera_module: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"   ✗ Error with camera_module: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Check Picamera2 (optional, for actual camera)
print("\n[5] Checking Picamera2 (for camera hardware)...")
try:
    from picamera2 import Picamera2
    print("   ✓ Picamera2 is installed")
    print("   → Note: Camera hardware may not be available, but software is ready")
except ImportError as e:
    print(f"   ⚠ Picamera2 NOT FOUND: {e}")
    print("   → Install with: pip3 install picamera2")
    print("   → This is only needed if you have a Raspberry Pi Camera Module")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
if CRACK_DETECTION_AVAILABLE:
    print("✓ All crack detection dependencies are properly installed!")
    print("✓ Crack detection should work correctly.")
else:
    print("✗ Crack detection is NOT available.")
    if CRACK_DETECTION_ERROR:
        print(f"  Error: {CRACK_DETECTION_ERROR}")
    print("\nTo fix:")
    print("  1. Install OpenCV: pip3 install opencv-python")
    print("  2. Install NumPy: pip3 install numpy")
    print("  3. Restart the Flask server")
print("=" * 60)

