import smbus
import time
import math
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# MPU6050 I2C address
MPU_ADDR = 0x68

class MPU6050:
    """
    MPU6050 6-axis accelerometer and gyroscope sensor module.
    Provides tilt measurements (pitch and roll).
    """
    
    def __init__(self, bus_num: int = 1):
        """
        Initialize the MPU6050 sensor.
        
        Args:
            bus_num: I2C bus number (default: 1 for Raspberry Pi)
        """
        try:
            self.bus = smbus.SMBus(bus_num)
            # Wake up the MPU6050 (set sleep bit to 0)
            self.bus.write_byte_data(MPU_ADDR, 0x6B, 0)
            time.sleep(0.1)  # Allow sensor to initialize
            logger.info(f"MPU6050 initialized on I2C bus {bus_num}, address 0x{MPU_ADDR:02X}")
        except Exception as e:
            logger.error(f"Failed to initialize MPU6050: {e}")
            raise

    def read_word(self, reg: int) -> int:
        """
        Read a 16-bit word from the MPU6050.
        
        Args:
            reg: Register address (high byte)
            
        Returns:
            int: 16-bit signed integer value
        """
        try:
            h = self.bus.read_byte_data(MPU_ADDR, reg)
            l = self.bus.read_byte_data(MPU_ADDR, reg + 1)
            value = (h << 8) + l
            # Convert to signed 16-bit integer
            if value >= 0x8000:
                return -((65535 - value) + 1)
            else:
                return value
        except Exception as e:
            logger.error(f"Error reading MPU6050 register 0x{reg:02X}: {e}")
            return 0

    def get_tilt(self) -> Tuple[float, float]:
        """
        Calculate pitch and roll angles from accelerometer data.
        
        Returns:
            Tuple[float, float]: (pitch, roll) in degrees
        """
        try:
            # Read accelerometer data (16-bit values, ±2g range = ±16384)
            acc_x = self.read_word(0x3B) / 16384.0
            acc_y = self.read_word(0x3D) / 16384.0
            acc_z = self.read_word(0x3F) / 16384.0

            # Calculate pitch and roll using accelerometer data
            pitch = math.degrees(math.atan(acc_x / math.sqrt(acc_y**2 + acc_z**2)))
            roll = math.degrees(math.atan(acc_y / math.sqrt(acc_x**2 + acc_z**2)))

            return pitch, roll
        except Exception as e:
            logger.error(f"Error calculating tilt from MPU6050: {e}")
            return 0.0, 0.0
