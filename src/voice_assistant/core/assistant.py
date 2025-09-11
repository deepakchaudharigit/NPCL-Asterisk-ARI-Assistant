"""
Main Voice Assistant class
"""

import logging
import time
from typing import Optional, Dict, Any, Callable
from enum import Enum

from ..ai.gemini_client import GeminiClient
from ..audio.speech_recognition import SpeechRecognizer
from ..audio.text_to_speech import TextToSpeech
from ..utils.logger import setup_logger

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings

logger = logging.getLogger(__name__)


class AssistantState(Enum):
    """Assistant state enumeration"""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


class VoiceAssistant:
    """Main voice assistant class"""
    
    def __init__(self, 
                 on_state_change: Optional[Callable[[AssistantState], None]] = None,
                 on_user_speech: Optional[Callable[[str], None]] = None,
                 on_assistant_response: Optional[Callable[[str], None]] = None):
        """
        Initialize voice assistant
        
        Args:
            on_state_change: Callback for state changes
            on_user_speech: Callback for user speech events
            on_assistant_response: Callback for assistant response events
        """
        self.settings = get_settings()
        
        # Setup logging
        setup_logger()
        
        # Initialize components
        self.gemini_client = GeminiClient()
        self.speech_recognizer = SpeechRecognizer()
        self.tts = TextToSpeech()
        
        # State management
        self.state = AssistantState.IDLE
        self.is_running = False
        self.conversation_count = 0
        
        # Callbacks
        self.on_state_change = on_state_change
        self.on_user_speech = on_user_speech
        self.on_assistant_response = on_assistant_response
        
        # Statistics
        self.stats = {
            "conversations": 0,
            "successful_recognitions": 0,
            "failed_recognitions": 0,
            "ai_responses": 0,
            "ai_failures": 0,
            "start_time": None
        }
        
        logger.info(f"Voice Assistant '{self.settings.assistant_name}' initialized")
    
    def _set_state(self, new_state: AssistantState):
        """Set assistant state and trigger callback"""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            logger.debug(f"State changed: {old_state.value} -> {new_state.value}")
            
            if self.on_state_change:
                try:
                    self.on_state_change(new_state)
                except Exception as e:
                    logger.error(f"State change callback error: {e}")
    
    def start(self) -> bool:
        """
        Start the voice assistant
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running:
            logger.warning("Assistant is already running")
            return True
        
        try:
            logger.info("Starting voice assistant...")
            
            # Test components
            if not self._test_components():
                return False
            
            # Welcome message
            welcome_message = self._get_welcome_message()
            self._speak_response(welcome_message)
            
            self.is_running = True
            self.stats["start_time"] = time.time()
            self._set_state(AssistantState.IDLE)
            
            logger.info("Voice assistant started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start assistant: {e}")
            self._set_state(AssistantState.ERROR)
            return False
    
    def stop(self):
        """Stop the voice assistant"""
        if not self.is_running:
            return
        
        logger.info("Stopping voice assistant...")
        
        # Farewell message
        farewell = self._get_farewell_message()
        self._speak_response(farewell)
        
        self.is_running = False
        self._set_state(AssistantState.IDLE)
        
        # Cleanup
        self.tts.cleanup_temp_files()
        
        # Log statistics
        self._log_session_stats()
        
        logger.info("Voice assistant stopped")
    
    def process_conversation_turn(self) -> bool:
        """
        Process one conversation turn
        
        Returns:
            True to continue, False to stop
        """
        if not self.is_running:
            return False
        
        try:
            # Listen for user input
            self._set_state(AssistantState.LISTENING)
            success, user_text, error = self._listen_for_input()
            
            if not success:
                self._handle_listening_error(error)
                return True  # Continue listening
            
            # Check for exit commands
            if self._is_exit_command(user_text):
                return False  # Stop conversation
            
            # Process user input
            self._set_state(AssistantState.PROCESSING)
            response = self._process_user_input(user_text)
            
            # Speak response
            self._set_state(AssistantState.SPEAKING)
            self._speak_response(response)
            
            self.conversation_count += 1
            self.stats["conversations"] += 1
            self._set_state(AssistantState.IDLE)
            
            return True  # Continue conversation
            
        except KeyboardInterrupt:
            logger.info("Conversation interrupted by user")
            return False
        except Exception as e:
            logger.error(f"Error in conversation turn: {e}")
            self._set_state(AssistantState.ERROR)
            return True  # Try to continue
    
    def run_conversation_loop(self):
        """Run the main conversation loop"""
        if not self.start():
            return
        
        try:
            logger.info("Starting conversation loop")
            
            while self.is_running:
                if not self.process_conversation_turn():
                    break
                    
        except KeyboardInterrupt:
            logger.info("Conversation loop interrupted")
        finally:
            self.stop()
    
    def _test_components(self) -> bool:
        """Test all components"""
        logger.info("Testing components...")
        
        # Test Gemini connection
        if not self.gemini_client.test_connection():
            logger.error("Gemini API connection test failed")
            return False
        
        # Test microphone
        if not self.speech_recognizer.is_microphone_available():
            logger.error("Microphone not available")
            return False
        
        # Test TTS
        if not self.tts.test_tts():
            logger.warning("TTS test failed, continuing with text-only mode")
        
        logger.info("Component tests completed")
        return True
    
    def _listen_for_input(self) -> tuple:
        """Listen for user speech input"""
        logger.debug(f"[Turn {self.conversation_count + 1}] Listening for speech...")
        
        success, text, error = self.speech_recognizer.listen_for_speech()
        
        if success:
            self.stats["successful_recognitions"] += 1
            logger.info(f"User said: {text}")
            
            if self.on_user_speech:
                try:
                    self.on_user_speech(text)
                except Exception as e:
                    logger.error(f"User speech callback error: {e}")
        else:
            self.stats["failed_recognitions"] += 1
        
        return success, text, error
    
    def _process_user_input(self, user_text: str) -> str:
        """Process user input and generate response"""
        logger.debug("Processing user input with Gemini...")
        
        try:
            response = self.gemini_client.generate_response(user_text)
            self.stats["ai_responses"] += 1
            return response
        except Exception as e:
            self.stats["ai_failures"] += 1
            logger.error(f"Failed to process user input: {e}")
            return "I'm sorry, I'm having trouble processing your request right now. Could you try again?"
    
    def _speak_response(self, response: str):
        """Speak the assistant's response"""
        logger.info(f"Assistant: {response}")
        
        if self.on_assistant_response:
            try:
                self.on_assistant_response(response)
            except Exception as e:
                logger.error(f"Assistant response callback error: {e}")
        
        # Speak the response
        if not self.tts.speak(response):
            logger.warning("TTS failed, response shown as text only")
    
    def _handle_listening_error(self, error: str):
        """Handle listening errors"""
        if "timeout" in error.lower():
            logger.debug("Listening timeout - continuing")
        elif "understand" in error.lower():
            response = "I didn't understand that clearly. Could you please repeat?"
            self._speak_response(response)
        else:
            logger.warning(f"Listening error: {error}")
    
    def _is_exit_command(self, text: str) -> bool:
        """Check if text contains exit command"""
        exit_words = ['quit', 'exit', 'goodbye', 'bye', 'stop', 'end']
        return any(word in text.lower() for word in exit_words)
    
    def _get_welcome_message(self) -> str:
        """Get welcome message"""
        return f"Hello! I'm {self.settings.assistant_name}, your voice assistant powered by Gemini 1.5 Flash. I'm ready to help you with any questions or tasks. What would you like to talk about?"
    
    def _get_farewell_message(self) -> str:
        """Get farewell message"""
        return "Goodbye! It was great talking with you. Have a wonderful day!"
    
    def _log_session_stats(self):
        """Log session statistics"""
        if self.stats["start_time"]:
            duration = time.time() - self.stats["start_time"]
            logger.info(f"Session Statistics:")
            logger.info(f"  Duration: {duration:.1f} seconds")
            logger.info(f"  Conversations: {self.stats['conversations']}")
            logger.info(f"  Successful recognitions: {self.stats['successful_recognitions']}")
            logger.info(f"  Failed recognitions: {self.stats['failed_recognitions']}")
            logger.info(f"  AI responses: {self.stats['ai_responses']}")
            logger.info(f"  AI failures: {self.stats['ai_failures']}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        stats = self.stats.copy()
        if stats["start_time"]:
            stats["duration"] = time.time() - stats["start_time"]
        return stats
    
    def reset_conversation(self):
        """Reset conversation history"""
        self.gemini_client.reset_conversation()
        self.conversation_count = 0
        logger.info("Conversation reset")