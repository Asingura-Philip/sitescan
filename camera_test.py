from picamera2 import Picamera2
import time

picam = Picamera2()

picam.start()
print("Camera started...")

time.sleep(5)

picam.stop()
print("Camera stopped.")
