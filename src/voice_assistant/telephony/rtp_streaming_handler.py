"""
Direct RTP Streaming Handler for Asterisk integration.
Provides direct RTP streaming capabilities for real-time audio processing.
"""

import asyncio
import logging
import socket
import struct
import time
from typing import Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass
import threading
from concurrent.futures import ThreadPoolExecutor

from ..audio.advanced_audio_processor import audio_processor
from ..utils.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)


@dataclass
class RTPConfig:
    """RTP streaming configuration"""
    payload_type: int = 0  # PCMU
    sample_rate: int = 16000  # 16kHz
    channels: int = 1  # Mono
    frame_size: int = 320  # 20ms at 16kHz
    buffer_size: int = 1600  # 100ms buffer
    max_packet_size: int = 1500  # MTU consideration


@dataclass
class RTPPacket:
    """RTP packet structure"""
    version: int = 2
    padding: bool = False
    extension: bool = False
    cc: int = 0  # CSRC count
    marker: bool = False
    payload_type: int = 0
    sequence_number: int = 0
    timestamp: int = 0
    ssrc: int = 0
    payload: bytes = b''


class RTPStreamHandler:
    """Handles RTP streaming for a single channel"""
    
    def __init__(self, channel_id: str, config: RTPConfig):
        self.channel_id = channel_id
        self.config = config
        
        # RTP state
        self.sequence_number = 0
        self.timestamp = 0
        self.ssrc = hash(channel_id) & 0xFFFFFFFF  # Generate SSRC from channel ID
        
        # Streaming state
        self.is_streaming = False
        self.input_socket: Optional[socket.socket] = None
        self.output_socket: Optional[socket.socket] = None
        self.input_address: Optional[Tuple[str, int]] = None
        self.output_address: Optional[Tuple[str, int]] = None
        
        # Buffers
        self.input_buffer = bytearray()
        self.output_buffer = bytearray()
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.input_task: Optional[asyncio.Task] = None
        self.output_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self.audio_received_callback: Optional[Callable] = None
        self.audio_sent_callback: Optional[Callable] = None
        
        # Statistics
        self.packets_sent = 0
        self.packets_received = 0
        self.bytes_sent = 0
        self.bytes_received = 0
        self.last_activity = time.time()
        
        logger.info(f"RTP Stream Handler created for channel {channel_id}")
    
    async def start_streaming(self, input_port: int, output_address: Tuple[str, int]) -> Dict[str, Any]:
        """
        Start RTP streaming.
        
        Args:
            input_port: Local port to listen for incoming RTP
            output_address: Remote address to send RTP packets
            
        Returns:
            Streaming interface with read/write functions
        """
        try:
            self.output_address = output_address
            
            # Create input socket (for receiving from Asterisk)
            self.input_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.input_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.input_socket.bind(('0.0.0.0', input_port))
            self.input_socket.setblocking(False)
            
            # Create output socket (for sending to Asterisk)
            self.output_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.output_socket.setblocking(False)
            
            self.is_streaming = True
            
            # Start streaming tasks
            self.input_task = asyncio.create_task(self._input_stream_handler())
            self.output_task = asyncio.create_task(self._output_stream_handler())
            
            logger.info(f"RTP streaming started for channel {self.channel_id}")
            logger.info(f"Listening on port {input_port}, sending to {output_address}")
            
            # Return streaming interface
            return {
                "read": self._read_audio,
                "write": self._write_audio,
                "get_stats": self._get_streaming_stats,
                "stop": self.stop_streaming
            }
            
        except Exception as e:
            logger.error(f"Error starting RTP streaming: {e}")
            await self.stop_streaming()
            raise
    
    async def stop_streaming(self):
        """Stop RTP streaming"""
        try:
            self.is_streaming = False
            
            # Cancel tasks
            if self.input_task:
                self.input_task.cancel()
                try:
                    await self.input_task
                except asyncio.CancelledError:
                    pass
            
            if self.output_task:
                self.output_task.cancel()
                try:
                    await self.output_task
                except asyncio.CancelledError:
                    pass
            
            # Close sockets
            if self.input_socket:
                self.input_socket.close()
                self.input_socket = None
            
            if self.output_socket:
                self.output_socket.close()
                self.output_socket = None
            
            # Shutdown executor
            self.executor.shutdown(wait=False)
            
            logger.info(f"RTP streaming stopped for channel {self.channel_id}")
            
        except Exception as e:
            logger.error(f"Error stopping RTP streaming: {e}")
    
    async def _input_stream_handler(self):
        """Handle incoming RTP packets"""
        try:
            while self.is_streaming:
                try:
                    # Receive RTP packet
                    data, addr = await asyncio.get_event_loop().run_in_executor(
                        self.executor, self.input_socket.recvfrom, self.config.max_packet_size
                    )
                    
                    if data:
                        await self._process_incoming_rtp(data, addr)
                    
                except socket.error:
                    # No data available, continue
                    await asyncio.sleep(0.001)  # Small delay to prevent busy waiting
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in input stream handler: {e}")
    
    async def _output_stream_handler(self):
        """Handle outgoing RTP packets"""
        try:
            while self.is_streaming:
                if len(self.output_buffer) >= self.config.frame_size * 2:  # 16-bit samples
                    # Extract frame from buffer
                    frame_data = bytes(self.output_buffer[:self.config.frame_size * 2])
                    del self.output_buffer[:self.config.frame_size * 2]
                    
                    # Send RTP packet
                    await self._send_rtp_packet(frame_data)
                else:
                    await asyncio.sleep(0.01)  # Wait for more data
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in output stream handler: {e}")
    
    async def _process_incoming_rtp(self, data: bytes, addr: Tuple[str, int]):
        """Process incoming RTP packet"""
        try:
            # Parse RTP header
            rtp_packet = self._parse_rtp_packet(data)
            
            if rtp_packet and rtp_packet.payload:
                # Add to input buffer
                self.input_buffer.extend(rtp_packet.payload)
                
                # Update statistics
                self.packets_received += 1
                self.bytes_received += len(data)
                self.last_activity = time.time()
                
                # Record performance metrics
                performance_monitor.record_audio_packet("received", len(data))
                
                # Trigger callback if set
                if self.audio_received_callback:
                    await self.audio_received_callback(rtp_packet.payload)
                
        except Exception as e:
            logger.error(f"Error processing incoming RTP: {e}")
    
    async def _send_rtp_packet(self, payload: bytes):
        """Send RTP packet"""
        try:
            if not self.output_address or not self.output_socket:
                return
            
            # Create RTP packet
            rtp_packet = RTPPacket(
                payload_type=self.config.payload_type,
                sequence_number=self.sequence_number,
                timestamp=self.timestamp,
                ssrc=self.ssrc,
                payload=payload
            )
            
            # Serialize packet
            packet_data = self._serialize_rtp_packet(rtp_packet)
            
            # Send packet
            await asyncio.get_event_loop().run_in_executor(
                self.executor, 
                self.output_socket.sendto, 
                packet_data, 
                self.output_address
            )
            
            # Update state
            self.sequence_number = (self.sequence_number + 1) & 0xFFFF
            self.timestamp += self.config.frame_size
            
            # Update statistics
            self.packets_sent += 1
            self.bytes_sent += len(packet_data)
            self.last_activity = time.time()
            
            # Record performance metrics
            performance_monitor.record_audio_packet("sent", len(packet_data))
            
            # Trigger callback if set
            if self.audio_sent_callback:
                await self.audio_sent_callback(payload)
                
        except Exception as e:
            logger.error(f"Error sending RTP packet: {e}")
    
    def _parse_rtp_packet(self, data: bytes) -> Optional[RTPPacket]:
        """Parse RTP packet from bytes"""
        try:
            if len(data) < 12:  # Minimum RTP header size
                return None
            
            # Parse fixed header
            byte0, byte1 = struct.unpack('!BB', data[:2])
            
            version = (byte0 >> 6) & 0x3
            padding = bool((byte0 >> 5) & 0x1)
            extension = bool((byte0 >> 4) & 0x1)
            cc = byte0 & 0xF
            
            marker = bool((byte1 >> 7) & 0x1)
            payload_type = byte1 & 0x7F
            
            sequence_number, timestamp, ssrc = struct.unpack('!HII', data[2:12])
            
            # Calculate header size
            header_size = 12 + (cc * 4)
            
            if extension:
                if len(data) < header_size + 4:
                    return None
                ext_length = struct.unpack('!H', data[header_size + 2:header_size + 4])[0]
                header_size += 4 + (ext_length * 4)
            
            # Extract payload
            payload = data[header_size:]
            
            return RTPPacket(
                version=version,
                padding=padding,
                extension=extension,
                cc=cc,
                marker=marker,
                payload_type=payload_type,
                sequence_number=sequence_number,
                timestamp=timestamp,
                ssrc=ssrc,
                payload=payload
            )
            
        except Exception as e:
            logger.error(f"Error parsing RTP packet: {e}")
            return None
    
    def _serialize_rtp_packet(self, packet: RTPPacket) -> bytes:
        """Serialize RTP packet to bytes"""
        try:
            # Build header
            byte0 = (packet.version << 6) | (int(packet.padding) << 5) | \
                   (int(packet.extension) << 4) | packet.cc
            byte1 = (int(packet.marker) << 7) | packet.payload_type
            
            header = struct.pack('!BBHII', 
                               byte0, byte1, 
                               packet.sequence_number, 
                               packet.timestamp, 
                               packet.ssrc)
            
            return header + packet.payload
            
        except Exception as e:
            logger.error(f"Error serializing RTP packet: {e}")
            return b''
    
    async def _read_audio(self) -> Optional[bytes]:
        """Read audio data from input buffer"""
        if len(self.input_buffer) >= self.config.frame_size * 2:
            # Extract frame
            frame_data = bytes(self.input_buffer[:self.config.frame_size * 2])
            del self.input_buffer[:self.config.frame_size * 2]
            return frame_data
        return None
    
    async def _write_audio(self, audio_data: bytes):
        """Write audio data to output buffer"""
        # Process audio if needed
        processed_audio = audio_processor.resample_pcm_24khz_to_16khz(audio_data)
        
        # Add to output buffer
        self.output_buffer.extend(processed_audio)
    
    def _get_streaming_stats(self) -> Dict[str, Any]:
        """Get streaming statistics"""
        uptime = time.time() - (self.last_activity - 60)  # Approximate uptime
        
        return {
            "channel_id": self.channel_id,
            "is_streaming": self.is_streaming,
            "packets_sent": self.packets_sent,
            "packets_received": self.packets_received,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "input_buffer_size": len(self.input_buffer),
            "output_buffer_size": len(self.output_buffer),
            "last_activity": self.last_activity,
            "uptime": uptime,
            "packet_rate": (self.packets_sent + self.packets_received) / max(1, uptime)
        }
    
    def set_audio_callbacks(self, received_callback: Callable = None, sent_callback: Callable = None):
        """Set audio event callbacks"""
        self.audio_received_callback = received_callback
        self.audio_sent_callback = sent_callback


class RTPStreamingManager:
    """Manages multiple RTP streams"""
    
    def __init__(self):
        self.streams: Dict[str, RTPStreamHandler] = {}
        self.config = RTPConfig()
        self.port_allocator = 20000  # Starting port for RTP streams
        
        logger.info("RTP Streaming Manager initialized")
    
    async def start_rtp_streaming(self, channel_id: str, rtp_source: str) -> Dict[str, Any]:
        """
        Start RTP streaming for a channel.
        
        Args:
            channel_id: Channel identifier
            rtp_source: RTP source information (format: "host:port")
            
        Returns:
            Streaming interface
        """
        try:
            # Parse RTP source
            if ':' in rtp_source:
                host, port = rtp_source.split(':')
                output_address = (host, int(port))
            else:
                output_address = (rtp_source, 5004)  # Default RTP port
            
            # Allocate local port
            local_port = self._allocate_port()
            
            # Create stream handler
            stream_handler = RTPStreamHandler(channel_id, self.config)
            
            # Start streaming
            streaming_interface = await stream_handler.start_streaming(local_port, output_address)
            
            # Store stream
            self.streams[channel_id] = stream_handler
            
            logger.info(f"RTP streaming started for channel {channel_id}")
            return streaming_interface
            
        except Exception as e:
            logger.error(f"Error starting RTP streaming for channel {channel_id}: {e}")
            raise
    
    async def stop_rtp_streaming(self, channel_id: str):
        """Stop RTP streaming for a channel"""
        if channel_id in self.streams:
            await self.streams[channel_id].stop_streaming()
            del self.streams[channel_id]
            logger.info(f"RTP streaming stopped for channel {channel_id}")
    
    async def stop_all_streams(self):
        """Stop all RTP streams"""
        for channel_id in list(self.streams.keys()):
            await self.stop_rtp_streaming(channel_id)
    
    def get_stream(self, channel_id: str) -> Optional[RTPStreamHandler]:
        """Get stream handler for channel"""
        return self.streams.get(channel_id)
    
    def get_all_streams(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all streams"""
        return {
            channel_id: stream._get_streaming_stats() 
            for channel_id, stream in self.streams.items()
        }
    
    def _allocate_port(self) -> int:
        """Allocate a new port for RTP streaming"""
        port = self.port_allocator
        self.port_allocator += 2  # RTP uses even ports, RTCP uses odd
        return port


# Global instance
rtp_streaming_manager = RTPStreamingManager()