"""
Simple UI Indicators for Voice Assistant
Clean, minimal visual feedback without spam
"""

import sys
import time
import threading
from typing import Optional


class SimpleSpinner:
    """Simple spinning indicator without frequent updates"""
    
    def __init__(self, message: str = "Processing"):
        self.message = message
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
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
            time.sleep(0.15)  # Slightly slower for less distraction


class SimpleAudioIndicator:
    """Simple audio indicator without spam"""
    
    def __init__(self):
        self.spinner = None
        self.start_time = None
        self.is_active = False
    
    def start_audio_response(self):
        """Start indicating audio response"""
        if self.is_active:
            return
            
        self.start_time = time.time()
        self.is_active = True
        self.spinner = SimpleSpinner("🔊 Playing Live API voice")
        self.spinner.start()
    
    def update_audio_response(self, bytes_count: int):
        """Update with new audio bytes (ignored to avoid spam)"""
        # Do nothing - we don't want to update constantly
        pass
    
    def stop_audio_response(self):
        """Stop the audio response indicator"""
        if not self.is_active:
            return
            
        if self.spinner:
            self.spinner.stop()
            
        # Show simple completion message
        elapsed = time.time() - self.start_time if self.start_time else 0
        print(f"✅ Audio completed ({elapsed:.1f}s)")
        
        self.spinner = None
        self.start_time = None
        self.is_active = False


# Global simple audio indicator instance
_simple_audio_indicator = SimpleAudioIndicator()


def get_simple_audio_indicator() -> SimpleAudioIndicator:
    """Get the global simple audio response indicator"""
    return _simple_audio_indicator