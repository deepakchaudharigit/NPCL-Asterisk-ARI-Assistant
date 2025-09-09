"""
UI Indicators for Voice Assistant
Provides visual feedback for audio processing and other operations
"""

import sys
import time
import threading
from typing import Optional


class SpinningIndicator:
    """Spinning circle indicator for ongoing operations"""
    
    def __init__(self, message: str = "Processing", spinner_chars: str = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
        self.message = message
        self.spinner_chars = spinner_chars
        self.is_spinning = False
        self.thread: Optional[threading.Thread] = None
        self.current_char_index = 0
    
    def start(self):
        """Start the spinning indicator"""
        if self.is_spinning:
            return
        
        self.is_spinning = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the spinning indicator"""
        if not self.is_spinning:
            return
        
        self.is_spinning = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.1)
        
        # Clear the line
        sys.stdout.write('\r' + ' ' * (len(self.message) + 10) + '\r')
        sys.stdout.flush()
    
    def _spin(self):
        """Internal spinning loop"""
        while self.is_spinning:
            char = self.spinner_chars[self.current_char_index]
            sys.stdout.write(f'\r{char} {self.message}...')
            sys.stdout.flush()
            
            self.current_char_index = (self.current_char_index + 1) % len(self.spinner_chars)
            time.sleep(0.1)


class AudioResponseIndicator:
    """Special indicator for audio responses"""
    
    def __init__(self):
        self.spinner = None
        self.bytes_received = 0
        self.start_time = None
    
    def start_audio_response(self):
        """Start indicating audio response"""
        self.bytes_received = 0
        self.start_time = time.time()
        self.spinner = SpinningIndicator("🔊 Playing Live API voice")
        self.spinner.start()
    
    def update_audio_response(self, bytes_count: int):
        """Update with new audio bytes"""
        self.bytes_received += bytes_count
        # Update the spinner message with bytes info
        if self.spinner:
            self.spinner.stop()
            elapsed = time.time() - self.start_time if self.start_time else 0
            self.spinner = SpinningIndicator(f"🔊 Playing Live API voice ({self.bytes_received:,} bytes, {elapsed:.1f}s)")
            self.spinner.start()
    
    def stop_audio_response(self):
        """Stop the audio response indicator"""
        if self.spinner:
            self.spinner.stop()
            
            # Show completion message
            elapsed = time.time() - self.start_time if self.start_time else 0
            print(f"✅ Audio response completed ({self.bytes_received:,} bytes, {elapsed:.1f}s)")
            
            self.spinner = None
            self.bytes_received = 0
            self.start_time = None


class SimpleSpinner:
    """Simple one-line spinner for quick operations"""
    
    @staticmethod
    def show_for_duration(message: str, duration: float):
        """Show spinner for a specific duration"""
        spinner = SpinningIndicator(message)
        spinner.start()
        time.sleep(duration)
        spinner.stop()
    
    @staticmethod
    def context_manager(message: str):
        """Use as context manager"""
        return SpinnerContext(message)


class SpinnerContext:
    """Context manager for spinner"""
    
    def __init__(self, message: str):
        self.spinner = SpinningIndicator(message)
    
    def __enter__(self):
        self.spinner.start()
        return self.spinner
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.spinner.stop()


# Global audio indicator instance
_audio_indicator = AudioResponseIndicator()


def get_audio_indicator() -> AudioResponseIndicator:
    """Get the global audio response indicator"""
    return _audio_indicator


def show_spinner(message: str, duration: float = None):
    """Show a spinner with message"""
    if duration:
        SimpleSpinner.show_for_duration(message, duration)
    else:
        return SimpleSpinner.context_manager(message)


# Example usage:
# with show_spinner("Connecting to Live API"):
#     # do something
#     pass
#
# indicator = get_audio_indicator()
# indicator.start_audio_response()
# indicator.update_audio_response(1920)
# indicator.stop_audio_response()