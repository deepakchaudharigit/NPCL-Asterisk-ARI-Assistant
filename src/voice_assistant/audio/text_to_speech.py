"""
Text-to-speech module using Google Text-to-Speech (gTTS)
"""

import logging
import os
import tempfile
from typing import Optional
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings

logger = logging.getLogger(__name__)


class TextToSpeech:
    """Text-to-speech handler using Google TTS"""
    
    def __init__(self):
        """Initialize TTS engine"""
        self.settings = get_settings()
        self.temp_files = []  # Track temp files for cleanup
        
        # Ensure temp directory exists
        os.makedirs(self.settings.temp_audio_dir, exist_ok=True)
        
        logger.info("Text-to-Speech engine initialized with gTTS")
    
    def speak(self, text: str, save_to_file: Optional[str] = None) -> bool:
        """
        Convert text to speech and play it
        
        Args:
            text: Text to convert to speech
            save_to_file: Optional path to save audio file
            
        Returns:
            True if successful, False otherwise
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for TTS")
            return False
        
        try:
            logger.debug(f"Converting text to speech: {text[:50]}...")
            
            # Create TTS object
            tts = gTTS(
                text=text.strip(),
                lang=self.settings.voice_language,
                slow=False
            )
            
            # Determine output file
            if save_to_file:
                output_file = save_to_file
            else:
                # Create temporary file
                temp_fd, output_file = tempfile.mkstemp(
                    suffix='.mp3',
                    dir=self.settings.temp_audio_dir
                )
                os.close(temp_fd)  # Close file descriptor
                self.temp_files.append(output_file)
            
            # Save TTS to file
            tts.save(output_file)
            logger.debug(f"TTS saved to: {output_file}")
            
            # Load and play audio
            audio = AudioSegment.from_file(output_file)
            
            # Adjust volume if needed
            if self.settings.voice_volume != 1.0:
                # Convert volume (0.0-1.0) to dB adjustment
                db_change = 20 * (self.settings.voice_volume - 1.0)
                audio = audio + db_change
            
            # Play audio
            play(audio)
            
            # Clean up temporary file if not saving
            if not save_to_file and output_file in self.temp_files:
                try:
                    os.unlink(output_file)
                    self.temp_files.remove(output_file)
                except Exception as e:
                    logger.warning(f"Could not delete temp file {output_file}: {e}")
            
            logger.info("Text-to-speech completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Text-to-speech failed: {e}")
            return False
    
    def create_audio_file(self, text: str, output_path: str) -> bool:
        """
        Create audio file from text without playing
        
        Args:
            text: Text to convert
            output_path: Path to save audio file
            
        Returns:
            True if successful, False otherwise
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for audio file creation")
            return False
        
        try:
            logger.debug(f"Creating audio file: {output_path}")
            
            # Create TTS object
            tts = gTTS(
                text=text.strip(),
                lang=self.settings.voice_language,
                slow=False
            )
            
            # Save to file
            tts.save(output_path)
            
            logger.info(f"Audio file created successfully: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Audio file creation failed: {e}")
            return False
    
    def test_tts(self) -> bool:
        """Test TTS functionality"""
        try:
            test_text = "This is a test of the text-to-speech system."
            return self.speak(test_text)
        except Exception as e:
            logger.error(f"TTS test failed: {e}")
            return False
    
    def cleanup_temp_files(self):
        """Clean up temporary audio files"""
        for temp_file in self.temp_files[:]:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                self.temp_files.remove(temp_file)
                logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Could not clean up temp file {temp_file}: {e}")
    
    def get_supported_languages(self) -> list:
        """Get list of supported languages"""
        # Common gTTS supported languages
        return [
            'en',    # English
            'en-us', # English (US)
            'en-uk', # English (UK)
            'en-au', # English (Australia)
            'en-in', # English (India)
            'es',    # Spanish
            'fr',    # French
            'de',    # German
            'it',    # Italian
            'pt',    # Portuguese
            'ru',    # Russian
            'ja',    # Japanese
            'ko',    # Korean
            'zh',    # Chinese
            'hi',    # Hindi
        ]
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        self.cleanup_temp_files()