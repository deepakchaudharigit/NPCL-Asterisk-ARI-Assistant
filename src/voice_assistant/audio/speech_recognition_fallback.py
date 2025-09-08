"""
Fallback speech recognition module that works without PyAudio
Uses system default microphone through speech_recognition library
"""

import logging
import speech_recognition as sr
from typing import Optional, Tuple
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings

logger = logging.getLogger(__name__)


class SpeechRecognizerFallback:
    """Speech recognition handler without PyAudio dependency"""
    
    def __init__(self):
        """Initialize speech recognizer with fallback method"""
        self.settings = get_settings()
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self._setup_microphone()
    
    def _setup_microphone(self):
        """Setup microphone with fallback method"""
        try:
            # Try to use default microphone without PyAudio
            self.microphone = sr.Microphone()
            logger.info("Microphone detected successfully (fallback mode)")
            
            # Basic calibration
            logger.info("Calibrating microphone...")
            try:
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                logger.info("Microphone calibration completed")
            except Exception as e:
                logger.warning(f"Calibration failed, using defaults: {e}")
                # Set reasonable defaults
                self.recognizer.energy_threshold = 300
                self.recognizer.dynamic_energy_threshold = True
            
        except Exception as e:
            logger.error(f"Microphone setup failed: {e}")
            logger.info("Trying alternative microphone setup...")
            
            # Try alternative setup
            try:
                # Use system default
                self.microphone = sr.Microphone(device_index=None)
                self.recognizer.energy_threshold = 300
                self.recognizer.dynamic_energy_threshold = True
                logger.info("Alternative microphone setup successful")
            except Exception as e2:
                logger.error(f"Alternative microphone setup also failed: {e2}")
                self.microphone = None
    
    def listen_for_speech(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Listen for speech input with fallback handling
        
        Returns:
            Tuple of (success, recognized_text, error_message)
        """
        if not self.microphone:
            return False, None, "Microphone not available"
        
        try:
            logger.debug("Listening for speech (fallback mode)...")
            
            # Use shorter timeout for better responsiveness
            timeout = min(self.settings.listen_timeout, 10.0)
            phrase_limit = min(self.settings.phrase_time_limit, 8.0)
            
            with self.microphone as source:
                # Listen with timeout and phrase limit
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout,
                    phrase_time_limit=phrase_limit
                )
            
            logger.debug("Processing speech...")
            
            # Recognize speech using Google Speech Recognition
            text = self.recognizer.recognize_google(audio)
            logger.info(f"Speech recognized: {text}")
            
            return True, text, None
            
        except sr.WaitTimeoutError:
            error_msg = f"No speech detected in {timeout} seconds"
            logger.debug(error_msg)
            return False, None, error_msg
            
        except sr.UnknownValueError:
            error_msg = "Could not understand the speech clearly"
            logger.debug(error_msg)
            return False, None, error_msg
            
        except sr.RequestError as e:
            error_msg = f"Speech recognition service error: {e}"
            logger.error(error_msg)
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error during speech recognition: {e}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def is_microphone_available(self) -> bool:
        """Check if microphone is available"""
        return self.microphone is not None
    
    def recalibrate_microphone(self):
        """Recalibrate microphone for ambient noise"""
        if not self.microphone:
            logger.warning("Cannot recalibrate: microphone not available")
            return
        
        try:
            logger.info("Recalibrating microphone...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info("Microphone recalibration completed")
        except Exception as e:
            logger.warning(f"Microphone recalibration failed, using defaults: {e}")
            self.recognizer.energy_threshold = 300
    
    def set_energy_threshold(self, threshold: int):
        """Set energy threshold for voice detection"""
        self.recognizer.energy_threshold = threshold
        logger.info(f"Energy threshold set to {threshold}")
    
    def get_microphone_info(self) -> dict:
        """Get microphone information"""
        if not self.microphone:
            return {"available": False, "mode": "fallback"}
        
        try:
            return {
                "available": True,
                "mode": "fallback",
                "device_index": getattr(self.microphone, 'device_index', 'default'),
                "energy_threshold": self.recognizer.energy_threshold,
                "dynamic_energy": self.recognizer.dynamic_energy_threshold
            }
        except Exception as e:
            logger.error(f"Error getting microphone info: {e}")
            return {"available": True, "mode": "fallback", "error": str(e)}