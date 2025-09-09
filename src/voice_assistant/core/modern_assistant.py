"""
Modern Voice Assistant with Gemini Live API
Real-time voice conversation with interruption support and dialogue flow
"""

import asyncio
import logging
import time
import threading
from typing import Optional, Dict, Any, Callable
from enum import Enum
from pathlib import Path

from ..ai.gemini_live_client import GeminiLiveClient, GeminiLiveConfig
from ..audio.realtime_audio_processor import RealTimeAudioProcessor, AudioConfig
from ..audio.microphone_stream import LiveAudioStreamer, MicrophoneConfig
from ..audio.audio_player import LiveAPIAudioHandler
from ..audio.speech_recognition import SpeechRecognizer
from ..audio.text_to_speech import TextToSpeech
from ..utils.simple_indicators import get_simple_audio_indicator

import sys
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings

logger = logging.getLogger(__name__)


class ModernAssistantState(Enum):
    """Modern assistant state enumeration"""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    ERROR = "error"
    CONNECTING = "connecting"
    CONNECTED = "connected"


class ModernVoiceAssistant:
    """Modern voice assistant with Gemini Live API and real-time capabilities"""
    
    def __init__(self, 
                 on_state_change: Optional[Callable[[ModernAssistantState], None]] = None,
                 on_user_speech: Optional[Callable[[str], None]] = None,
                 on_assistant_response: Optional[Callable[[str], None]] = None,
                 on_audio_response: Optional[Callable[[bytes], None]] = None):
        """
        Initialize modern voice assistant
        
        Args:
            on_state_change: Callback for state changes
            on_user_speech: Callback for user speech events
            on_assistant_response: Callback for assistant text response events
            on_audio_response: Callback for assistant audio response events
        """
        self.settings = get_settings()
        
        # Initialize components
        self.gemini_live = GeminiLiveClient(
            api_key=self.settings.google_api_key,
            config=GeminiLiveConfig(
                model=self.settings.gemini_live_model,
                voice=self.settings.gemini_voice
            )
        )
        
        self.audio_processor = RealTimeAudioProcessor(
            config=AudioConfig(
                sample_rate=self.settings.audio_sample_rate,
                chunk_size=self.settings.audio_chunk_size,
                buffer_size=self.settings.audio_buffer_size
            )
        )
        
        # Live audio streaming
        self.live_audio_streamer = LiveAudioStreamer(
            self.gemini_live,
            config=MicrophoneConfig(
                sample_rate=self.settings.audio_sample_rate,
                chunk_size=self.settings.audio_chunk_size
            )
        )
        
        # Live audio player
        self.live_audio_handler = LiveAPIAudioHandler(
            sample_rate=self.settings.audio_sample_rate
        )
        
        # Fallback components for when Live API is not available
        self.speech_recognizer = SpeechRecognizer()
        self.tts = TextToSpeech()
        
        # State management
        self.state = ModernAssistantState.IDLE
        self.is_running = False
        self.conversation_count = 0
        self.is_live_mode = False
        
        # Callbacks
        self.on_state_change = on_state_change
        self.on_user_speech = on_user_speech
        self.on_assistant_response = on_assistant_response
        self.on_audio_response = on_audio_response
        
        # Audio state
        self.is_user_speaking = False
        self.is_assistant_speaking = False
        self.current_audio_response = bytearray()
        
        # Event loop for async operations
        self.loop = None
        self.loop_thread = None
        
        # Statistics
        self.stats = {
            "conversations": 0,
            "successful_recognitions": 0,
            "failed_recognitions": 0,
            "ai_responses": 0,
            "ai_failures": 0,
            "interruptions": 0,
            "start_time": None,
            "live_mode_enabled": False
        }
        
        logger.info(f"Modern Voice Assistant '{self.settings.assistant_name}' initialized")
    
    def _set_state(self, new_state: ModernAssistantState):
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
        Start the modern voice assistant
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running:
            logger.warning("Assistant is already running")
            return True
        
        try:
            logger.info("Starting modern voice assistant...")
            
            # Start event loop in separate thread
            self._start_event_loop()
            
            # Try to connect to Gemini Live API
            self._set_state(ModernAssistantState.CONNECTING)
            
            if self._connect_to_live_api():
                self.is_live_mode = True
                self.stats["live_mode_enabled"] = True
                
                # Start live audio components
                if (self.live_audio_streamer.start_streaming(self.loop) and 
                    self.live_audio_handler.start()):
                    self._set_state(ModernAssistantState.CONNECTED)
                    logger.info("Connected to Gemini Live API - Real-time mode enabled")
                else:
                    logger.warning("Failed to start audio streaming, falling back to traditional mode")
                    self.is_live_mode = False
                    self._set_state(ModernAssistantState.IDLE)
            else:
                self.is_live_mode = False
                self._set_state(ModernAssistantState.IDLE)
                logger.info("Using fallback mode - Traditional speech recognition")
            
            # Test components
            if not self._test_components():
                return False
            
            # Welcome message
            welcome_message = self._get_welcome_message()
            
            if self.is_live_mode:
                # In Live mode, send welcome as a conversation starter to get native voice
                logger.info("Sending welcome message to Live API for native voice")
                self._send_welcome_to_live_api(welcome_message)
            else:
                # Traditional mode - use local TTS
                self._speak_response(welcome_message)
            
            self.is_running = True
            self.stats["start_time"] = time.time()
            self._set_state(ModernAssistantState.IDLE)
            
            logger.info("Modern voice assistant started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start assistant: {e}")
            self._set_state(ModernAssistantState.ERROR)
            return False
    
    def stop(self):
        """Stop the modern voice assistant"""
        if not self.is_running:
            return
        
        logger.info("Stopping modern voice assistant...")
        
        # Farewell message
        farewell = self._get_farewell_message()
        self._speak_response(farewell)
        
        self.is_running = False
        
        # Stop live audio components
        if self.is_live_mode:
            self.live_audio_streamer.stop_streaming()
            self.live_audio_handler.stop()
            self._disconnect_from_live_api()
        
        # Stop event loop
        self._stop_event_loop()
        
        # Cleanup
        self.tts.cleanup_temp_files()
        
        # Log statistics
        self._log_session_stats()
        
        self._set_state(ModernAssistantState.IDLE)
        logger.info("Modern voice assistant stopped")
    
    def process_conversation_turn(self) -> bool:
        """
        Process one conversation turn
        
        Returns:
            True to continue, False to stop
        """
        if not self.is_running:
            return False
        
        try:
            if self.is_live_mode:
                return self._process_live_conversation_turn()
            else:
                return self._process_traditional_conversation_turn()
                
        except KeyboardInterrupt:
            logger.info("Conversation interrupted by user")
            return False
        except Exception as e:
            logger.error(f"Error in conversation turn: {e}")
            self._set_state(ModernAssistantState.ERROR)
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
    
    def _start_event_loop(self):
        """Start asyncio event loop in separate thread"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()
        
        # Wait for loop to be ready
        while self.loop is None:
            time.sleep(0.01)
        
        logger.debug("Event loop started")
    
    def _stop_event_loop(self):
        """Stop asyncio event loop"""
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        if self.loop_thread and self.loop_thread.is_alive():
            self.loop_thread.join(timeout=2.0)
        
        logger.debug("Event loop stopped")
    
    def _connect_to_live_api(self) -> bool:
        """Connect to Gemini Live API"""
        try:
            logger.info("Attempting to connect to Gemini Live API...")
            
            # Setup event handlers first
            self._setup_live_api_handlers()
            
            # Run connection in event loop
            future = asyncio.run_coroutine_threadsafe(
                self.gemini_live.connect(), self.loop
            )
            connected = future.result(timeout=15.0)  # Increased timeout
            
            if connected:
                logger.info("Live API WebSocket connected")
                
                # Start conversation session
                future = asyncio.run_coroutine_threadsafe(
                    self.gemini_live.start_conversation(), self.loop
                )
                session_id = future.result(timeout=5.0)
                logger.info(f"Started Live API session: {session_id}")
                
                return True
            else:
                logger.warning("Live API connection failed")
                return False
            
        except asyncio.TimeoutError:
            logger.error("Live API connection timeout - API may not be available")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Live API: {e}")
            logger.debug("Full error details:", exc_info=True)
            return False
    
    def _disconnect_from_live_api(self):
        """Disconnect from Gemini Live API"""
        try:
            if self.loop and self.loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self.gemini_live.disconnect(), self.loop
                )
                future.result(timeout=5.0)
            
            logger.info("Disconnected from Live API")
            
        except Exception as e:
            logger.error(f"Error disconnecting from Live API: {e}")
    
    def _setup_live_api_handlers(self):
        """Setup event handlers for Gemini Live API"""
        
        # Setup complete handler
        async def handle_setup_complete(event_data):
            logger.info("Live API setup completed successfully")
            self._set_state(ModernAssistantState.CONNECTED)
        
        # Audio response handler
        async def handle_audio_response(event_data):
            audio_data = event_data.get("audio_data", b"")
            if audio_data:
                # Start or update audio indicator
                audio_indicator = get_simple_audio_indicator()
                if len(self.current_audio_response) == 0:  # First chunk
                    audio_indicator.start_audio_response()
                else:
                    audio_indicator.update_audio_response(len(audio_data))
                
                self.current_audio_response.extend(audio_data)
                
                # Play audio through Live API audio handler
                self.live_audio_handler.handle_audio_response(audio_data)
                
                # Also trigger callback for UI updates
                if self.on_audio_response:
                    try:
                        self.on_audio_response(audio_data)
                    except Exception as e:
                        logger.error(f"Audio response callback error: {e}")
        
        # Audio response done handler
        async def handle_audio_response_done(event_data):
            if self.current_audio_response:
                # Stop audio indicator
                audio_indicator = get_simple_audio_indicator()
                audio_indicator.stop_audio_response()
                
                self.current_audio_response.clear()
                self.is_assistant_speaking = False
                self._set_state(ModernAssistantState.IDLE)
        
        # Interruption handler
        async def handle_interrupted(event_data):
            logger.info("Response interrupted by user")
            self.live_audio_handler.clear_audio_buffer()  # Clear audio buffer
            self.stats["interruptions"] += 1
            self.is_assistant_speaking = False
            self._set_state(ModernAssistantState.INTERRUPTED)
        
        # Error handler
        async def handle_error(event_data):
            error_info = event_data.get("error", {})
            logger.error(f"Live API error: {error_info}")
            self._set_state(ModernAssistantState.ERROR)
        
        # Register handlers
        self.gemini_live.register_event_handler("setup_complete", handle_setup_complete)
        self.gemini_live.register_event_handler("audio_response", handle_audio_response)
        self.gemini_live.register_event_handler("audio_response_done", handle_audio_response_done)
        self.gemini_live.register_event_handler("interrupted", handle_interrupted)
        self.gemini_live.register_event_handler("error", handle_error)
        
        logger.debug("Live API event handlers setup complete")
    
    def _send_text_to_live_api(self, text: str):
        """Send text to Live API for native voice synthesis"""
        try:
            if not self.is_live_mode or not self.loop:
                raise RuntimeError("Live API not available")
            
            # Send text message to Live API for voice synthesis
            future = asyncio.run_coroutine_threadsafe(
                self._send_text_message_to_live_api(text), self.loop
            )
            future.result(timeout=2.0)
            logger.debug(f"Text sent to Live API: {text[:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to send text to Live API: {e}")
            raise
    
    async def _send_text_message_to_live_api(self, text: str):
        """Send text message to Live API (async)"""
        try:
            # Create client content message with text
            message = {
                "clientContent": {
                    "turns": [{
                        "role": "user",
                        "parts": [{
                            "text": text
                        }]
                    }],
                    "turnComplete": True
                }
            }
            
            await self.gemini_live._send_event(message)
            logger.debug("Text message sent to Live API")
            
        except Exception as e:
            logger.error(f"Error sending text message to Live API: {e}")
            raise
    
    def _send_welcome_to_live_api(self, welcome_message: str):
        """Send welcome message to Live API to get native voice response"""
        try:
            if not self.is_live_mode or not self.loop:
                logger.warning("Live API not available, using traditional TTS")
                self._speak_response(welcome_message)
                return
            
            # Send a system prompt that will make the assistant say the welcome message
            system_prompt = f"Please say this exact welcome message in a friendly voice: '{welcome_message}'"
            
            future = asyncio.run_coroutine_threadsafe(
                self._send_system_message_to_live_api(system_prompt), self.loop
            )
            future.result(timeout=3.0)
            logger.info("Welcome message sent to Live API")
            
        except Exception as e:
            logger.error(f"Failed to send welcome to Live API: {e}")
            # Fallback to traditional TTS
            logger.info("Falling back to traditional TTS for welcome message")
            self._speak_response(welcome_message)
    
    async def _send_system_message_to_live_api(self, message: str):
        """Send system message to Live API (async)"""
        try:
            # Create client content message
            content = {
                "clientContent": {
                    "turns": [{
                        "role": "user",
                        "parts": [{
                            "text": message
                        }]
                    }],
                    "turnComplete": True
                }
            }
            
            await self.gemini_live._send_event(content)
            logger.debug("System message sent to Live API")
            
        except Exception as e:
            logger.error(f"Error sending system message to Live API: {e}")
            raise
    
    def _process_live_conversation_turn(self) -> bool:
        """Process conversation turn using Live API"""
        try:
            # In Live API mode, audio is continuously streamed
            # We just need to wait for user interaction or check for exit commands
            self._set_state(ModernAssistantState.LISTENING)
            
            # Wait for a short period to allow Live API to process
            time.sleep(0.1)
            
            # Check if user wants to exit (we can still accept text commands)
            try:
                # Non-blocking check for keyboard input
                import select
                import sys
                
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    user_input = sys.stdin.readline().strip()
                    if self._is_exit_command(user_input):
                        return False
            except:
                # select not available on Windows, use alternative
                pass
            
            return True
            
        except Exception as e:
            logger.error(f"Error in live conversation turn: {e}")
            return True
    
    def _process_traditional_conversation_turn(self) -> bool:
        """Process conversation turn using traditional speech recognition"""
        try:
            # Listen for user input
            self._set_state(ModernAssistantState.LISTENING)
            success, user_text, error = self._listen_for_input()
            
            if not success:
                self._handle_listening_error(error)
                return True
            
            # Check for exit commands
            if self._is_exit_command(user_text):
                return False
            
            return self._process_traditional_conversation_turn_with_text(user_text)
            
        except Exception as e:
            logger.error(f"Error in traditional conversation turn: {e}")
            return True
    
    def _process_traditional_conversation_turn_with_text(self, user_text: str) -> bool:
        """Process conversation turn with given text"""
        try:
            # Process user input
            self._set_state(ModernAssistantState.PROCESSING)
            
            # Use basic Gemini client for fallback
            from ..ai.gemini_client import GeminiClient
            gemini_client = GeminiClient()
            response = gemini_client.generate_response(user_text)
            
            # Speak response
            self._set_state(ModernAssistantState.SPEAKING)
            self._speak_response(response)
            
            self.conversation_count += 1
            self.stats["conversations"] += 1
            self.stats["ai_responses"] += 1
            self._set_state(ModernAssistantState.IDLE)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing conversation: {e}")
            self.stats["ai_failures"] += 1
            return True
    
    def _test_components(self) -> bool:
        """Test all components"""
        logger.info("Testing components...")
        
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
    
    def _speak_response(self, response: str):
        """Speak the assistant's response"""
        logger.info(f"Assistant: {response}")
        
        if self.on_assistant_response:
            try:
                self.on_assistant_response(response)
            except Exception as e:
                logger.error(f"Assistant response callback error: {e}")
        
        # Choose audio output method based on mode
        if self.is_live_mode:
            # In Live API mode, send text to Live API for native voice synthesis
            try:
                self._send_text_to_live_api(response)
            except Exception as e:
                logger.error(f"Live API TTS failed, falling back to traditional: {e}")
                # Fallback to traditional TTS
                if not self.tts.speak(response):
                    logger.warning("Both Live API and traditional TTS failed")
        else:
            # Traditional mode - use local TTS
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
        if self.is_live_mode:
            return f"Hello! I'm {self.settings.assistant_name}, your modern voice assistant powered by Gemini Live API with real-time conversation and interruption support. I'm ready to have a natural conversation with you. What would you like to talk about?"
        else:
            return f"Hello! I'm {self.settings.assistant_name}, your voice assistant. I'm running in traditional mode today. How can I help you?"
    
    def _get_farewell_message(self) -> str:
        """Get farewell message"""
        return "Goodbye! It was great having a conversation with you. Have a wonderful day!"
    
    def _log_session_stats(self):
        """Log session statistics"""
        if self.stats["start_time"]:
            duration = time.time() - self.stats["start_time"]
            logger.info(f"Session Statistics:")
            logger.info(f"  Duration: {duration:.1f} seconds")
            logger.info(f"  Live Mode: {self.stats['live_mode_enabled']}")
            logger.info(f"  Conversations: {self.stats['conversations']}")
            logger.info(f"  Successful recognitions: {self.stats['successful_recognitions']}")
            logger.info(f"  Failed recognitions: {self.stats['failed_recognitions']}")
            logger.info(f"  AI responses: {self.stats['ai_responses']}")
            logger.info(f"  AI failures: {self.stats['ai_failures']}")
            logger.info(f"  Interruptions: {self.stats['interruptions']}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        stats = self.stats.copy()
        if stats["start_time"]:
            stats["duration"] = time.time() - stats["start_time"]
        stats["is_live_mode"] = self.is_live_mode
        stats["current_state"] = self.state.value
        return stats
    
    def reset_conversation(self):
        """Reset conversation history"""
        if self.is_live_mode:
            # Reset Live API session
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.gemini_live.clear_audio_buffer(), self.loop
                )
                future.result(timeout=2.0)
            except Exception as e:
                logger.error(f"Error resetting Live API session: {e}")
        else:
            # Reset traditional client
            from ..ai.gemini_client import GeminiClient
            gemini_client = GeminiClient()
            gemini_client.reset_conversation()
        
        self.conversation_count = 0
        logger.info("Conversation reset")
    
    def interrupt_response(self):
        """Interrupt current assistant response"""
        if self.is_live_mode and self.is_assistant_speaking:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.gemini_live.cancel_response(), self.loop
                )
                future.result(timeout=1.0)
                self.stats["interruptions"] += 1
                self._set_state(ModernAssistantState.INTERRUPTED)
                logger.info("Response interrupted")
            except Exception as e:
                logger.error(f"Error interrupting response: {e}")
    
    def get_live_api_status(self) -> Dict[str, Any]:
        """Get Live API connection status"""
        if self.is_live_mode:
            return self.gemini_live.get_connection_status()
        else:
            return {"is_connected": False, "mode": "traditional"}