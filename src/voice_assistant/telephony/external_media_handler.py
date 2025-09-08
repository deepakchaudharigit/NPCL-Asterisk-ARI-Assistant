"""
External Media Handler for Asterisk ARI bidirectional audio streaming.
Handles real-time audio communication between Asterisk and Gemini Live API
using the externalMedia feature for low-latency audio processing.
"""

import asyncio
import logging
import json
import time
import uuid
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
from typing import TYPE_CHECKING

# Compatibility shim across websockets versions
try:
    # websockets 14 asyncio namespace (preferred)
    from websockets.asyncio.server import ServerConnection as WSProto  # type: ignore
except Exception:
    try:
        # websockets >= 12 / 13 (fallback)
        from websockets.server import WebSocketServerProtocol as WSProto
    except Exception:
        # very old fallback
        from websockets import WebSocketServerProtocol as WSProto  # type: ignore

from ..audio.realtime_audio_processor import (
    RealTimeAudioProcessor, AudioConfig, AudioFormat
)
from ..ai.gemini_live_client import GeminiLiveClient
from ..core.session_manager import SessionManager, SessionState

logger = logging.getLogger(__name__)


@dataclass
class ExternalMediaConfig:
    """Configuration for external media handling"""
    format: str = "slin16"  # Audio format (slin16 for 16-bit signed linear)
    rate: int = 16000  # Sample rate in Hz
    direction: str = "both"  # "in", "out", or "both"
    connection_timeout: int = 30  # Connection timeout in seconds
    audio_chunk_size: int = 320  # Audio chunk size in samples (20ms at 16kHz)
    buffer_size: int = 1600  # Buffer size in samples (100ms at 16kHz)


class ExternalMediaConnection:
    """Manages a single external media WebSocket connection"""
    
    def __init__(self, channel_id: str, config: ExternalMediaConfig):
        self.channel_id = channel_id
        self.config = config
        self.connection_id = str(uuid.uuid4())
        
        # WebSocket connection
        self.websocket: Optional[WSProto] = None
        self.is_connected = False
        self.connection_task: Optional[asyncio.Task] = None
        
        # Audio processing
        self.audio_processor = RealTimeAudioProcessor(
            AudioConfig(
                sample_rate=config.rate,
                format=AudioFormat.SLIN16,
                chunk_size=config.audio_chunk_size
            )
        )
        
        # State tracking
        self.bytes_received = 0
        self.bytes_sent = 0
        self.packets_received = 0
        self.packets_sent = 0
        self.last_activity = time.time()
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {
            "audio_received": [],
            "audio_sent": [],
            "connection_established": [],
            "connection_lost": [],
            "error": []
        }
        
        logger.info(f"Created external media connection {self.connection_id} for channel {channel_id}")
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler"""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)
    
    async def start_connection(self, websocket: WSProto):
        """Start handling external media connection"""
        try:
            self.websocket = websocket
            self.is_connected = True
            self.last_activity = time.time()
            
            # Start audio processing
            await self.audio_processor.start_processing()
            
            # Start connection handler
            self.connection_task = asyncio.create_task(self._connection_handler())
            
            # Trigger connection established event
            await self._trigger_event_handlers("connection_established", {
                "connection_id": self.connection_id,
                "channel_id": self.channel_id
            })
            
            logger.info(f"Started external media connection for channel {self.channel_id}")
            
        except Exception as e:
            logger.error(f"Error starting external media connection: {e}")
            await self.stop_connection()
            raise
    
    async def stop_connection(self):
        """Stop external media connection"""
        try:
            self.is_connected = False
            
            # Stop audio processing
            await self.audio_processor.stop_processing()
            
            # Cancel connection task
            task = self.connection_task
            if isinstance(task, asyncio.Task):
                if not task.done():
                    task.cancel()
                    from contextlib import suppress
                    with suppress(asyncio.CancelledError):
                        await task
            
            # Close WebSocket
            if self.websocket and not self.websocket.closed:
                await self.websocket.close()
            
            # Trigger connection lost event
            await self._trigger_event_handlers("connection_lost", {
                "connection_id": self.connection_id,
                "channel_id": self.channel_id,
                "stats": self.get_connection_stats()
            })
            
            logger.info(f"Stopped external media connection for channel {self.channel_id}")
            
        except Exception as e:
            logger.error(f"Error stopping external media connection: {e}")
    
    async def send_audio(self, audio_data: bytes) -> bool:
        """Send audio data to Asterisk"""
        if not self.is_connected or not self.websocket:
            return False
        
        try:
            # Process audio for output
            processed_audio = await self.audio_processor.prepare_output_audio(audio_data)
            
            # Send to Asterisk via WebSocket
            await self.websocket.send(processed_audio)
            
            # Update statistics
            self.bytes_sent += len(processed_audio)
            self.packets_sent += 1
            self.last_activity = time.time()
            
            # Trigger audio sent event
            await self._trigger_event_handlers("audio_sent", {
                "connection_id": self.connection_id,
                "channel_id": self.channel_id,
                "audio_size": len(processed_audio)
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
            return False
    
    async def _connection_handler(self):
        """Handle WebSocket connection and incoming audio"""
        try:
            while self.is_connected and self.websocket:
                try:
                    # Receive audio data from Asterisk
                    audio_data = await self.websocket.recv()
                    
                    if isinstance(audio_data, bytes):
                        await self._handle_incoming_audio(audio_data)
                    else:
                        logger.warning(f"Received non-binary data: {type(audio_data)}")
                    
                except ConnectionClosed:
                    logger.info(f"External media connection closed for channel {self.channel_id}")
                    break
                except WebSocketException as e:
                    logger.error(f"WebSocket error in external media: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error in external media connection handler: {e}")
        finally:
            await self.stop_connection()
    
    async def _handle_incoming_audio(self, audio_data: bytes):
        """Handle incoming audio data from Asterisk"""
        try:
            # Update statistics
            self.bytes_received += len(audio_data)
            self.packets_received += 1
            self.last_activity = time.time()
            
            # Process audio
            result = await self.audio_processor.process_input_audio(audio_data)
            
            # Trigger audio received event
            await self._trigger_event_handlers("audio_received", {
                "connection_id": self.connection_id,
                "channel_id": self.channel_id,
                "audio_data": audio_data,
                "processing_result": result
            })
            
        except Exception as e:
            logger.error(f"Error handling incoming audio: {e}")
            await self._trigger_event_handlers("error", {
                "connection_id": self.connection_id,
                "error": str(e)
            })
    
    async def _trigger_event_handlers(self, event_type: str, event_data: Dict[str, Any]):
        """Trigger registered event handlers"""
        handlers = self.event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        uptime = time.time() - (self.last_activity - 60)  # Approximate uptime
        
        return {
            "connection_id": self.connection_id,
            "channel_id": self.channel_id,
            "is_connected": self.is_connected,
            "uptime": uptime,
            "bytes_received": self.bytes_received,
            "bytes_sent": self.bytes_sent,
            "packets_received": self.packets_received,
            "packets_sent": self.packets_sent,
            "last_activity": self.last_activity,
            "audio_stats": self.audio_processor.get_audio_stats()
        }


class ExternalMediaHandler:
    """Handles multiple external media connections and integrates with Gemini Live"""
    
    def __init__(self, session_manager: SessionManager, gemini_client: GeminiLiveClient):
        self.session_manager = session_manager
        self.gemini_client = gemini_client
        
        # Connection management
        self.connections: Dict[str, ExternalMediaConnection] = {}  # channel_id -> connection
        self.config = ExternalMediaConfig()
        
        # WebSocket server
        self.server: Optional[websockets.WebSocketServer] = None
        self.server_host = "0.0.0.0"
        self.server_port = 8090
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {
            "connection_established": [],
            "connection_lost": [],
            "audio_processed": [],
            "error": []
        }
        
        logger.info("External Media Handler initialized")
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler"""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)
    
    async def start_server(self, host: str = None, port: int = None) -> bool:
        """Start external media WebSocket server"""
        try:
            self.server_host = host or self.server_host
            self.server_port = port or self.server_port
            
            self.server = await websockets.serve(
                self._handle_new_connection,
                self.server_host,
                self.server_port,
                ping_interval=30,
                ping_timeout=10
            )
            
            logger.info(f"External media server started on {self.server_host}:{self.server_port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start external media server: {e}")
            return False
    
    async def stop_server(self):
        """Stop external media WebSocket server"""
        try:
            # Close all connections
            for connection in list(self.connections.values()):
                await connection.stop_connection()
            
            self.connections.clear()
            
            # Stop server
            if self.server:
                self.server.close()
                await self.server.wait_closed()
                self.server = None
            
            logger.info("External media server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping external media server: {e}")
    
    async def _handle_new_connection(self, websocket, path):
        """Handle new external media WebSocket connection"""
        try:
            # Extract channel ID from path (e.g., /external_media/channel_id)
            path_parts = path.strip("/").split("/")
            if len(path_parts) < 2:
                logger.error(f"Invalid external media path: {path}")
                await websocket.close(code=1002, reason="Invalid path")
                return
            
            channel_id = path_parts[1]
            
            # Check if session exists
            session = self.session_manager.get_session_by_channel(channel_id)
            if not session:
                logger.error(f"No session found for channel: {channel_id}")
                await websocket.close(code=1002, reason="No session found")
                return
            
            # Create external media connection
            connection = ExternalMediaConnection(channel_id, self.config)
            
            # Register event handlers for this connection
            connection.register_event_handler("audio_received", self._handle_audio_from_asterisk)
            connection.register_event_handler("connection_established", self._handle_connection_established)
            connection.register_event_handler("connection_lost", self._handle_connection_lost)
            connection.register_event_handler("error", self._handle_connection_error)
            
            # Store connection
            self.connections[channel_id] = connection
            
            # Start connection
            await connection.start_connection(websocket)
            
        except Exception as e:
            logger.error(f"Error handling new external media connection: {e}")
            try:
                await websocket.close(code=1011, reason="Internal error")
            except:
                pass
    
    async def _handle_audio_from_asterisk(self, event_data: Dict[str, Any]):
        """Handle audio received from Asterisk"""
        try:
            channel_id = event_data["channel_id"]
            audio_data = event_data["audio_data"]
            
            # Get session
            session = self.session_manager.get_session_by_channel(channel_id)
            if not session:
                return
            
            # Update session audio state
            await self.session_manager.update_session_audio_state(
                session.session_id,
                audio_buffer_size=len(audio_data)
            )
            
            # Send audio to Gemini Live API
            if self.gemini_client.is_connected:
                await self.gemini_client.send_audio_chunk(audio_data)
            
            # Trigger audio processed event
            await self._trigger_event_handlers("audio_processed", {
                "channel_id": channel_id,
                "session_id": session.session_id,
                "audio_size": len(audio_data),
                "direction": "from_asterisk"
            })
            
        except Exception as e:
            logger.error(f"Error handling audio from Asterisk: {e}")
    
    async def _handle_connection_established(self, event_data: Dict[str, Any]):
        """Handle external media connection established"""
        try:
            channel_id = event_data["channel_id"]
            
            # Update session state
            session = self.session_manager.get_session_by_channel(channel_id)
            if session:
                await self.session_manager.update_session_state(
                    session.session_id, 
                    SessionState.ACTIVE
                )
            
            # Trigger event
            await self._trigger_event_handlers("connection_established", event_data)
            
            logger.info(f"External media connection established for channel {channel_id}")
            
        except Exception as e:
            logger.error(f"Error handling connection established: {e}")
    
    async def _handle_connection_lost(self, event_data: Dict[str, Any]):
        """Handle external media connection lost"""
        try:
            channel_id = event_data["channel_id"]
            
            # Remove connection
            if channel_id in self.connections:
                del self.connections[channel_id]
            
            # Update session state
            session = self.session_manager.get_session_by_channel(channel_id)
            if session:
                await self.session_manager.end_session(session.session_id)
            
            # Trigger event
            await self._trigger_event_handlers("connection_lost", event_data)
            
            logger.info(f"External media connection lost for channel {channel_id}")
            
        except Exception as e:
            logger.error(f"Error handling connection lost: {e}")
    
    async def _handle_connection_error(self, event_data: Dict[str, Any]):
        """Handle external media connection error"""
        try:
            connection_id = event_data["connection_id"]
            error = event_data["error"]
            
            logger.error(f"External media connection error [{connection_id}]: {error}")
            
            # Trigger error event
            await self._trigger_event_handlers("error", event_data)
            
        except Exception as e:
            logger.error(f"Error handling connection error: {e}")
    
    async def send_audio_to_channel(self, channel_id: str, audio_data: bytes) -> bool:
        """Send audio data to specific channel"""
        try:
            connection = self.connections.get(channel_id)
            if not connection:
                logger.warning(f"No external media connection for channel {channel_id}")
                return False
            
            success = await connection.send_audio(audio_data)
            
            if success:
                # Trigger audio processed event
                await self._trigger_event_handlers("audio_processed", {
                    "channel_id": channel_id,
                    "audio_size": len(audio_data),
                    "direction": "to_asterisk"
                })
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending audio to channel {channel_id}: {e}")
            return False
    
    async def _trigger_event_handlers(self, event_type: str, event_data: Dict[str, Any]):
        """Trigger registered event handlers"""
        handlers = self.event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
    
    def get_connection_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get connection information for channel"""
        connection = self.connections.get(channel_id)
        return connection.get_connection_stats() if connection else None
    
    def get_all_connections(self) -> Dict[str, Dict[str, Any]]:
        """Get information for all connections"""
        return {
            channel_id: connection.get_connection_stats()
            for channel_id, connection in self.connections.items()
        }
    
    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        return {
            "server_running": self.server is not None,
            "server_host": self.server_host,
            "server_port": self.server_port,
            "active_connections": len(self.connections),
            "connections": list(self.connections.keys()),
            "config": {
                "format": self.config.format,
                "rate": self.config.rate,
                "direction": self.config.direction,
                "chunk_size": self.config.audio_chunk_size,
                "buffer_size": self.config.buffer_size
            }
        }