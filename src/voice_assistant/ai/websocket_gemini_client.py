"""
WebSocket Gemini Client for real-time audio processing.
Integrates all the missing components into a unified WebSocket client.
"""

import asyncio
import json
import base64
import time
import websockets
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

from config.settings import get_settings
from ..audio.advanced_audio_processor import audio_processor
from ..utils.performance_monitor import performance_monitor
from ..utils.optimized_logger import LoggerFactory
from ..ai.function_calling import function_call_handler, function_registry
from ..ai.npcl_prompts import npcl_customer_service
from ..tools.weather_tool import weather_tool
from ..telephony.rtp_streaming_handler import rtp_streaming_manager

logger = logging.getLogger(__name__)
optimized_logger = LoggerFactory.get_logger("websocket_gemini")


@dataclass
class WebSocketGeminiConfig:
    """Configuration for WebSocket Gemini client"""
    model: str = "models/gemini-1.5-flash"  # Updated to use 1.5 Flash
    voice: str = "Kore"
    language_code: str = "en-IN"
    temperature: float = 0.2
    max_output_tokens: int = 256
    enable_performance_logging: bool = True


class WebSocketGeminiClient:
    """WebSocket-based Gemini client with all missing features integrated"""
    
    def __init__(self, channel_id: str, rtp_source: str):
        self.channel_id = channel_id
        self.rtp_source = rtp_source
        self.settings = get_settings()
        self.config = WebSocketGeminiConfig()
        
        # WebSocket connection
        self.ws: Optional[websockets.WebSocketServerProtocol] = None
        self.running = False
        self.setup_complete = False
        
        # Audio and streaming
        self.stream_handler: Optional[Dict[str, Any]] = None
        
        # Performance tracking
        self.audio_sent_time: Optional[float] = None
        self.call_start_time: Optional[float] = None
        self.audio_received_logged = False
        self.audio_packets_sent = 0
        self.audio_packets_received = 0
        self.total_latency = 0.0
        self.latency_measurements = 0
        
        # Register weather tool
        if weather_tool not in function_registry.functions.values():
            function_registry.register_function(weather_tool)
        
        optimized_logger.log_client(f"WebSocket Gemini client initialized for channel {channel_id}")
    
    async def start_gemini_websocket(self):
        """Start WebSocket connection to Google Gemini real-time API"""
        optimized_logger.log_client(f"Attempting to start Gemini WebSocket for channel {self.channel_id}")
        
        # Start performance monitoring
        operation_id = performance_monitor.start_operation("gemini_websocket_connect", f"connect_{self.channel_id}")
        
        try:
            ws_url = f"{self.settings.gemini_live_api_endpoint}?key={self.settings.google_api_key}"
            
            self.ws = await websockets.connect(ws_url)
            self.call_start_time = time.time()
            
            performance_monitor.end_operation(operation_id, "gemini_websocket_connect", True)
            optimized_logger.log_client(f"Gemini WebSocket connection established for channel {self.channel_id}")
            
            # Setup session with NPCL-specific configuration
            await self._setup_npcl_session()
            
            # Handle WebSocket messages
            await self.handle_websocket_messages()
            
        except websockets.exceptions.ConnectionClosed:
            optimized_logger.log_client(f"Gemini WebSocket closed for channel {self.channel_id}")
            performance_monitor.end_operation(operation_id, "gemini_websocket_connect", False)
        except Exception as e:
            optimized_logger.log_client(f"Gemini WebSocket error for channel {self.channel_id}: {str(e)}", "error")
            performance_monitor.end_operation(operation_id, "gemini_websocket_connect", False)
            performance_monitor.record_error("websocket_connection")
        finally:
            await self.cleanup()
    
    async def _setup_npcl_session(self):
        """Setup session with NPCL-specific configuration"""
        try:
            # Get NPCL system instruction
            system_instruction = npcl_customer_service.get_system_instruction()
            
            # Get function definitions
            function_definitions = function_registry.get_all_definitions()
            
            setup_message = {
                "setup": {
                    "model": self.config.model,
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "temperature": self.config.temperature,
                        "maxOutputTokens": self.config.max_output_tokens,
                        "speechConfig": {
                            "languageCode": self.config.language_code,
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {"voiceName": self.config.voice}
                            },
                        },
                    },
                    "system_instruction": {"parts": [{"text": system_instruction}]},
                    "tools": [{"functionDeclarations": function_definitions}] if function_definitions else [],
                }
            }
            
            await self.ws.send(json.dumps(setup_message))
            optimized_logger.log_client(f"NPCL session initialized for channel {self.channel_id}")
            
        except Exception as e:
            logger.error(f"Error setting up NPCL session: {e}")
            raise
    
    async def send_trigger_message(self):
        """Send trigger message to start NPCL conversation"""
        try:
            await asyncio.sleep(0.001)  # Minimal pause
            
            # Use NPCL welcome message
            welcome_message = npcl_customer_service.get_welcome_message()
            
            trigger_message = {
                "clientContent": {
                    "turns": [{"role": "user", "parts": [{"text": welcome_message}]}],
                    "turnComplete": True,
                }
            }
            
            await self.ws.send(json.dumps(trigger_message))
            optimized_logger.log_client(f"NPCL trigger message sent for channel {self.channel_id}")
            
        except Exception as e:
            logger.error(f"Error sending trigger for channel {self.channel_id}: {e}")
    
    async def handle_websocket_messages(self):
        """Handle WebSocket messages with timeout"""
        try:
            async for message in self.ws:
                try:
                    response = json.loads(message)
                    
                    # Handle setup completion
                    if "setupComplete" in response:
                        optimized_logger.log_server(f"Setup complete for channel {self.channel_id}")
                        self.setup_complete = True
                        await self.send_trigger_message()
                        continue
                    
                    # Handle server content
                    if response.get("serverContent"):
                        await self.handle_server_content(response["serverContent"])
                    
                    # Handle errors
                    elif response.get("error"):
                        error_msg = response["error"].get("message", "Unknown")
                        optimized_logger.log_server(f"Error for channel {self.channel_id}: {error_msg}", "error")
                        performance_monitor.record_error("gemini_api")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error for channel {self.channel_id}: {e}")
                    performance_monitor.record_error("json_decode")
                except Exception as e:
                    logger.error(f"Message handling error for channel {self.channel_id}: {e}")
                    performance_monitor.record_error("message_handling")
                    
        except Exception as e:
            logger.error(f"WebSocket error for channel {self.channel_id}: {e}")
            performance_monitor.record_error("websocket")
    
    async def handle_server_content(self, server_content: Dict[str, Any]):
        """Handle server content messages"""
        if server_content.get("modelTurn"):
            model_turn = server_content["modelTurn"]
            
            if model_turn.get("parts"):
                for part in model_turn["parts"]:
                    
                    # Handle audio responses
                    if part.get("inlineData") and "audio/pcm" in part["inlineData"].get("mimeType", ""):
                        await self.handle_audio_response(part["inlineData"])
                    
                    # Handle function calls
                    elif part.get("functionCall"):
                        await self.handle_function_call(part["functionCall"])
    
    async def handle_audio_response(self, inline_data: Dict[str, Any]):
        """Handle audio response from Gemini with performance optimization"""
        if not self.audio_received_logged:
            optimized_logger.log_server(f"Audio reception started for channel {self.channel_id}")
            self.audio_received_logged = True
        
        pcm_chunk = base64.b64decode(inline_data["data"])
        self.audio_packets_received += 1
        
        # Optimized logging - only log every 10th packet
        optimized_logger.log_audio_packet(
            self.channel_id, "received", len(pcm_chunk), self.audio_packets_received
        )
        
        # Process and stream audio to Asterisk
        if self.stream_handler:
            try:
                # Resample and send to Asterisk
                pcm_16khz = audio_processor.resample_pcm_24khz_to_16khz(pcm_chunk)
                await self.stream_handler["write"](pcm_16khz)
                
                # Record performance metrics
                performance_monitor.record_audio_packet("sent", len(pcm_16khz))
                
            except Exception as audio_error:
                logger.error(f"Audio processing error for channel {self.channel_id}: {audio_error}")
                performance_monitor.record_error("audio_processing")
        else:
            logger.error(f"No StreamHandler for channel {self.channel_id}")
    
    async def handle_function_call(self, func_call: Dict[str, Any]):
        """Handle function calls with integrated function calling system"""
        operation_id = performance_monitor.start_operation("function_call", f"call_{self.channel_id}")
        
        try:
            optimized_logger.log_server(f"Function call for channel {self.channel_id}: {func_call.get('name')}")
            
            # Use the integrated function call handler
            response = await function_call_handler.handle_function_call(func_call)
            
            # Send function response
            func_response = {
                "clientContent": {
                    "turns": [
                        {
                            "role": "user",
                            "parts": [response]
                        }
                    ],
                    "turnComplete": True,
                }
            }
            
            await self.ws.send(json.dumps(func_response))
            performance_monitor.end_operation(operation_id, "function_call", True)
            optimized_logger.log_server(f"Function response sent for {func_call.get('name')}")
            
        except Exception as e:
            logger.error(f"Error handling function call: {e}")
            performance_monitor.end_operation(operation_id, "function_call", False)
            performance_monitor.record_error("function_call")
    
    async def send_audio_to_gemini(self, pcm_buffer: bytes):
        """Send audio to Gemini with all optimizations"""
        # Performance and validation checks
        if not self.ws or not self.running or not self.setup_complete:
            return
        
        operation_id = performance_monitor.start_operation("audio_processing", f"audio_{self.channel_id}")
        
        try:
            # Quick silence check for optimization
            if audio_processor.quick_silence_check(pcm_buffer):
                performance_monitor.end_operation(operation_id, "audio_processing", True)
                return
            
            # Normalize audio
            normalized_buffer, rms = audio_processor.normalize_audio(pcm_buffer)
            
            # Base64 encoding
            base64_audio = base64.b64encode(normalized_buffer).decode("utf-8")
            
            # Create Gemini message
            gemini_message = {
                "realtimeInput": {
                    "mediaChunks": [{
                        "mimeType": "audio/pcm;rate=16000",
                        "data": base64_audio,
                    }]
                }
            }
            
            # Send to WebSocket
            await self.ws.send(json.dumps(gemini_message))
            
            # Update performance metrics
            self.audio_sent_time = time.time()
            self.audio_packets_sent += 1
            
            performance_monitor.end_operation(operation_id, "audio_processing", True)
            performance_monitor.record_audio_packet("sent", len(normalized_buffer))
            
            # Optimized logging
            optimized_logger.log_audio_packet(
                self.channel_id, "sent", len(normalized_buffer), self.audio_packets_sent
            )
            
        except websockets.exceptions.ConnectionClosed:
            logger.error(f"WebSocket connection closed for channel {self.channel_id}")
            self.running = False
            performance_monitor.end_operation(operation_id, "audio_processing", False)
        except Exception as e:
            logger.error(f"Error in send_audio_to_gemini for channel {self.channel_id}: {e}")
            performance_monitor.end_operation(operation_id, "audio_processing", False)
            performance_monitor.record_error("audio_send")
    
    async def start_rtp_streaming_handler(self, rtp_handler):
        """Start RTP streaming to Asterisk"""
        self.stream_handler = await rtp_handler.start_rtp_streaming(
            self.channel_id, self.rtp_source
        )
        optimized_logger.log_client(f"RTP streaming started for channel {self.channel_id}")
        return self.stream_handler
    
    async def run(self, rtp_handler):
        """Main run method with integrated features"""
        self.running = True
        
        # Record session start
        performance_monitor.record_session_event("start")
        
        try:
            # Start RTP streaming
            await self.start_rtp_streaming_handler(rtp_handler)
            
            # Start WebSocket connection
            await self.start_gemini_websocket()
            
        except Exception as e:
            logger.error(f"Error in WebSocket client for channel {self.channel_id}: {e}")
            performance_monitor.record_error("client_run")
        finally:
            await self.cleanup()
    
    async def add_audio_from_user(self, pcm_buffer: bytes):
        """Add audio from user and send to Gemini"""
        if not self.running or not self.setup_complete:
            return
        
        try:
            await self.send_audio_to_gemini(pcm_buffer)
        except Exception as e:
            logger.error(f"Error in add_audio_from_user for channel {self.channel_id}: {e}")
            performance_monitor.record_error("user_audio")
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            self.running = False
            
            if self.ws:
                await self.ws.close()
                self.ws = None
            
            # Record session end
            session_duration = time.time() - (self.call_start_time or time.time())
            performance_monitor.record_session_event("end", session_duration)
            
            optimized_logger.log_client(f"WebSocket client cleanup completed for channel {self.channel_id}")
            
        except Exception as e:
            logger.error(f"Error during cleanup for channel {self.channel_id}: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        uptime = time.time() - (self.call_start_time or time.time())
        
        return {
            "channel_id": self.channel_id,
            "uptime": uptime,
            "audio_packets_sent": self.audio_packets_sent,
            "audio_packets_received": self.audio_packets_received,
            "running": self.running,
            "setup_complete": self.setup_complete,
            "audio_processor_stats": audio_processor.get_audio_stats(),
            "performance_metrics": performance_monitor.get_current_metrics()
        }