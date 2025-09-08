"""
Audio utility functions
"""

import logging
import os
from typing import Optional, Tuple
from pydub import AudioSegment
from config.settings import get_settings

logger = logging.getLogger(__name__)


class AudioUtils:
    """Utility functions for audio processing"""
    
    def __init__(self):
        """Initialize audio utilities"""
        self.settings = get_settings()
    
    @staticmethod
    def convert_audio_format(input_path: str, output_path: str, 
                           target_format: str = "wav") -> bool:
        """
        Convert audio file to different format
        
        Args:
            input_path: Path to input audio file
            output_path: Path for output audio file
            target_format: Target audio format (wav, mp3, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            audio = AudioSegment.from_file(input_path)
            audio.export(output_path, format=target_format)
            logger.info(f"Audio converted: {input_path} -> {output_path}")
            return True
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            return False
    
    @staticmethod
    def adjust_audio_volume(input_path: str, output_path: str, 
                          volume_change_db: float) -> bool:
        """
        Adjust audio volume
        
        Args:
            input_path: Path to input audio file
            output_path: Path for output audio file
            volume_change_db: Volume change in decibels (positive = louder)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            audio = AudioSegment.from_file(input_path)
            adjusted_audio = audio + volume_change_db
            adjusted_audio.export(output_path)
            logger.info(f"Audio volume adjusted by {volume_change_db}dB")
            return True
        except Exception as e:
            logger.error(f"Audio volume adjustment failed: {e}")
            return False
    
    @staticmethod
    def get_audio_duration(file_path: str) -> Optional[float]:
        """
        Get audio file duration in seconds
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Duration in seconds, or None if failed
        """
        try:
            audio = AudioSegment.from_file(file_path)
            duration = len(audio) / 1000.0  # Convert ms to seconds
            logger.debug(f"Audio duration: {duration}s for {file_path}")
            return duration
        except Exception as e:
            logger.error(f"Could not get audio duration: {e}")
            return None
    
    @staticmethod
    def trim_audio(input_path: str, output_path: str, 
                   start_time: float, end_time: float) -> bool:
        """
        Trim audio file
        
        Args:
            input_path: Path to input audio file
            output_path: Path for output audio file
            start_time: Start time in seconds
            end_time: End time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            audio = AudioSegment.from_file(input_path)
            start_ms = int(start_time * 1000)
            end_ms = int(end_time * 1000)
            trimmed_audio = audio[start_ms:end_ms]
            trimmed_audio.export(output_path)
            logger.info(f"Audio trimmed: {start_time}s-{end_time}s")
            return True
        except Exception as e:
            logger.error(f"Audio trimming failed: {e}")
            return False
    
    @staticmethod
    def normalize_audio(input_path: str, output_path: str, 
                       target_dBFS: float = -20.0) -> bool:
        """
        Normalize audio to target dBFS level
        
        Args:
            input_path: Path to input audio file
            output_path: Path for output audio file
            target_dBFS: Target dBFS level
            
        Returns:
            True if successful, False otherwise
        """
        try:
            audio = AudioSegment.from_file(input_path)
            change_in_dBFS = target_dBFS - audio.dBFS
            normalized_audio = audio.apply_gain(change_in_dBFS)
            normalized_audio.export(output_path)
            logger.info(f"Audio normalized to {target_dBFS} dBFS")
            return True
        except Exception as e:
            logger.error(f"Audio normalization failed: {e}")
            return False
    
    @staticmethod
    def concatenate_audio_files(file_paths: list, output_path: str) -> bool:
        """
        Concatenate multiple audio files
        
        Args:
            file_paths: List of paths to audio files
            output_path: Path for output audio file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not file_paths:
                logger.warning("No audio files provided for concatenation")
                return False
            
            combined = AudioSegment.empty()
            for file_path in file_paths:
                if os.path.exists(file_path):
                    audio = AudioSegment.from_file(file_path)
                    combined += audio
                else:
                    logger.warning(f"Audio file not found: {file_path}")
            
            combined.export(output_path)
            logger.info(f"Audio files concatenated: {len(file_paths)} files")
            return True
        except Exception as e:
            logger.error(f"Audio concatenation failed: {e}")
            return False
    
    def ensure_audio_directories(self):
        """Ensure audio directories exist"""
        try:
            os.makedirs(self.settings.sounds_dir, exist_ok=True)
            os.makedirs(self.settings.temp_audio_dir, exist_ok=True)
            logger.debug("Audio directories ensured")
        except Exception as e:
            logger.error(f"Could not create audio directories: {e}")
    
    @staticmethod
    def get_audio_info(file_path: str) -> Optional[dict]:
        """
        Get audio file information
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary with audio info, or None if failed
        """
        try:
            audio = AudioSegment.from_file(file_path)
            info = {
                "duration_seconds": len(audio) / 1000.0,
                "frame_rate": audio.frame_rate,
                "channels": audio.channels,
                "sample_width": audio.sample_width,
                "dBFS": audio.dBFS,
                "max_dBFS": audio.max_dBFS,
                "file_size_bytes": os.path.getsize(file_path)
            }
            logger.debug(f"Audio info retrieved for {file_path}")
            return info
        except Exception as e:
            logger.error(f"Could not get audio info: {e}")
            return None