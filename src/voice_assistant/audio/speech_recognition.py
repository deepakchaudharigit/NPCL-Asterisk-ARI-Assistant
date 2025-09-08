"""
Speech recognition module using Google Speech Recognition
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


class SpeechRecognizer:
    """Speech recognition handler"""
    
    def __init__(self):
        """Initialize speech recognizer"""
        self.settings = get_settings()
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self._setup_microphone()
    
    def _setup_microphone(self):
        """Setup and calibrate microphone"""
        try:
            self.microphone = sr.Microphone()
            logger.info("Microphone detected successfully")
            
            # Calibrate for ambient noise
            logger.info("Calibrating microphone for ambient noise...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            logger.info("Microphone calibration completed")
            
        except Exception as e:
            logger.error(f"Microphone setup failed: {e}")
            raise
    
    def listen_for_speech(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Listen for speech input
        
        Returns:
            Tuple of (success, recognized_text, error_message)
        """
        if not self.microphone:
            return False, None, "Microphone not available"
        
        try:
            logger.debug("Listening for speech...")
            
            with self.microphone as source:
                # Listen with timeout and phrase limit
                audio = self.recognizer.listen(
                    source, 
                    timeout=self.settings.listen_timeout,
                    phrase_time_limit=self.settings.phrase_time_limit
                )
            
            logger.debug("Processing speech...")
            
            # Recognize speech using Google Speech Recognition
            text = self.recognizer.recognize_google(audio)
            logger.info(f"Speech recognized: {text}")
            
            return True, text, None
            
        except sr.WaitTimeoutError:
            error_msg = f"No speech detected in {self.settings.listen_timeout} seconds"
            logger.warning(error_msg)
            return False, None, error_msg
            
        except sr.UnknownValueError:
            error_msg = "Could not understand the speech clearly"
            logger.warning(error_msg)
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
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            logger.info("Microphone recalibration completed")
        except Exception as e:
            logger.error(f"Microphone recalibration failed: {e}")
    
    def set_energy_threshold(self, threshold: int):
        """Set energy threshold for voice detection"""
        self.recognizer.energy_threshold = threshold
        logger.info(f"Energy threshold set to {threshold}")
    
    def get_microphone_info(self) -> dict:
        """Get microphone information"""
        if not self.microphone:
            return {"available": False}
        
        try:
            mic_list = sr.Microphone.list_microphone_names()
            return {
                "available": True,
                "device_index": self.microphone.device_index,
                "available_devices": mic_list,
                "energy_threshold": self.recognizer.energy_threshold
            }
        except Exception as e:
            logger.error(f"Error getting microphone info: {e}")
            return {"available": True, "error": str(e)}