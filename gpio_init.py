"""
GPIO initialization helper module.
Ensures GPIO is properly initialized before any modules use it.
"""

import RPi.GPIO as GPIO
import logging
import time

logger = logging.getLogger(__name__)

_gpio_initialized = False

def init_gpio():
    """
    Initialize GPIO system. Safe to call multiple times.
    """
    global _gpio_initialized
    
    if _gpio_initialized:
        logger.debug("GPIO already initialized")
        return
    
    try:
        # Try to clean up any previous GPIO state first (if it exists)
        # This is safe even if GPIO wasn't previously initialized
        try:
            # Check if GPIO mode is set before trying to cleanup
            # If mode isn't set, cleanup will fail, which is fine
            GPIO.cleanup()
            time.sleep(0.05)  # Small delay after cleanup
        except (RuntimeError, ValueError, AttributeError):
            # GPIO wasn't initialized before, which is fine
            pass
        except Exception as cleanup_error:
            logger.debug(f"GPIO cleanup warning (may be normal): {cleanup_error}")
        
        # Set GPIO mode - this must be called before any GPIO operations
        # This allocates the GPIO system
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Small delay to ensure GPIO system is fully ready
        time.sleep(0.1)
        
        _gpio_initialized = True
        logger.info("GPIO initialized (BCM mode)")
    except Exception as e:
        logger.error(f"Failed to initialize GPIO: {e}")
        _gpio_initialized = False
        raise

def cleanup_gpio():
    """
    Clean up GPIO resources.
    """
    global _gpio_initialized
    try:
        GPIO.cleanup()
        _gpio_initialized = False
        logger.info("GPIO cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up GPIO: {e}")

