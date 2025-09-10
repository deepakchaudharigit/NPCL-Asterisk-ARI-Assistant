"""
Optimized Logging System for Voice Assistant.
Provides performance-optimized logging with reduced overhead for real-time applications.
"""

import logging
import time
import threading
from typing import Dict, Any, Optional
from collections import deque
from datetime import datetime
import sys
import os

# Global configuration
ENABLE_PERFORMANCE_LOGGING = os.getenv("ENABLE_PERFORMANCE_LOGGING", "false").lower() == "true"
LOG_BUFFER_SIZE = 1000
LOG_FLUSH_INTERVAL = 5.0  # seconds


class OptimizedLogger:
    """Performance-optimized logger with buffering and reduced overhead"""
    
    def __init__(self, name: str, enable_performance_logging: bool = ENABLE_PERFORMANCE_LOGGING):
        self.name = name
        self.enable_performance_logging = enable_performance_logging
        self.logger = logging.getLogger(name)
        
        # Performance tracking
        self.log_counts = {"debug": 0, "info": 0, "warning": 0, "error": 0}
        self.last_log_time = {}
        self.suppressed_logs = {}
        
        # Buffering for high-frequency logs
        self.log_buffer = deque(maxlen=LOG_BUFFER_SIZE)
        self.buffer_lock = threading.Lock()
        
        # Rate limiting
        self.rate_limits = {
            "audio_packet": 1.0,  # Log audio packets max once per second
            "performance": 5.0,   # Log performance max once per 5 seconds
            "websocket": 0.5,     # Log websocket events max twice per second
        }
    
    def log_client(self, msg: str, level: str = "info"):
        """Client logging - optimized for performance"""
        if not self.enable_performance_logging and level == "debug":
            return
        
        formatted_msg = f"[Client] {msg}"
        self._log_with_optimization(formatted_msg, level, "client")
    
    def log_server(self, msg: str, level: str = "info"):
        """Server logging - optimized for performance"""
        if not self.enable_performance_logging and level == "debug":
            return
        
        formatted_msg = f"[Server] {msg}"
        self._log_with_optimization(formatted_msg, level, "server")
    
    def log_audio_packet(self, channel_id: str, direction: str, size: int, packet_num: int):
        """Optimized logging for audio packets with rate limiting"""
        if not self._should_log_rate_limited("audio_packet"):
            return
        
        # Only log every 10th packet to reduce spam
        if packet_num % 10 != 0:
            return
        
        msg = f"Audio {direction} for channel {channel_id} | Size: {size/1024:.1f} KB | Packet: #{packet_num}"
        self.log_client(msg, "debug")
    
    def log_performance_metric(self, metric_name: str, value: Any, channel_id: str = None):
        """Optimized performance metric logging"""
        if not self._should_log_rate_limited("performance"):
            return
        
        channel_info = f" | Channel: {channel_id}" if channel_id else ""
        msg = f"Performance - {metric_name}: {value}{channel_info}"
        self.log_server(msg, "debug")
    
    def log_websocket_event(self, event_type: str, channel_id: str = None, details: str = None):
        """Optimized WebSocket event logging"""
        if not self._should_log_rate_limited("websocket"):
            return
        
        channel_info = f" | Channel: {channel_id}" if channel_id else ""
        details_info = f" | {details}" if details else ""
        msg = f"WebSocket {event_type}{channel_info}{details_info}"
        self.log_client(msg, "info")
    
    def log_error_with_context(self, error: Exception, context: Dict[str, Any]):
        """Enhanced error logging with context"""
        context_str = " | ".join([f"{k}: {v}" for k, v in context.items()])
        msg = f"Error: {str(error)} | Context: {context_str}"
        self.logger.error(msg, exc_info=True)
        self.log_counts["error"] += 1
    
    def log_session_event(self, event_type: str, session_id: str, channel_id: str = None, 
                         duration: float = None):
        """Optimized session event logging"""
        channel_info = f" | Channel: {channel_id}" if channel_id else ""
        duration_info = f" | Duration: {duration:.2f}s" if duration else ""
        msg = f"Session {event_type} - {session_id}{channel_info}{duration_info}"
        self.log_server(msg, "info")
    
    def _log_with_optimization(self, msg: str, level: str, category: str):
        """Internal optimized logging method"""
        current_time = time.time()
        
        # Update log counts
        if level in self.log_counts:
            self.log_counts[level] += 1
        
        # Check for duplicate suppression
        msg_hash = hash(msg)
        if msg_hash in self.suppressed_logs:
            self.suppressed_logs[msg_hash]["count"] += 1
            self.suppressed_logs[msg_hash]["last_seen"] = current_time
            return
        
        # Log the message
        log_method = getattr(self.logger, level, self.logger.info)
        log_method(msg)
        
        # Track for duplicate suppression
        self.suppressed_logs[msg_hash] = {
            "count": 1,
            "first_seen": current_time,
            "last_seen": current_time,
            "message": msg
        }
        
        # Clean old suppressed logs periodically
        if len(self.suppressed_logs) > 100:
            self._clean_suppressed_logs(current_time)
    
    def _should_log_rate_limited(self, category: str) -> bool:
        """Check if logging should proceed based on rate limits"""
        if category not in self.rate_limits:
            return True
        
        current_time = time.time()
        last_time = self.last_log_time.get(category, 0)
        
        if current_time - last_time >= self.rate_limits[category]:
            self.last_log_time[category] = current_time
            return True
        
        return False
    
    def _clean_suppressed_logs(self, current_time: float):
        """Clean old suppressed log entries"""
        cutoff_time = current_time - 300  # 5 minutes
        
        to_remove = []
        for msg_hash, info in self.suppressed_logs.items():
            if info["last_seen"] < cutoff_time:
                to_remove.append(msg_hash)
        
        for msg_hash in to_remove:
            del self.suppressed_logs[msg_hash]
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        total_logs = sum(self.log_counts.values())
        suppressed_count = sum(info["count"] - 1 for info in self.suppressed_logs.values())
        
        return {
            "total_logs": total_logs,
            "log_counts": self.log_counts.copy(),
            "suppressed_logs": suppressed_count,
            "unique_messages": len(self.suppressed_logs),
            "performance_logging_enabled": self.enable_performance_logging,
            "rate_limits": self.rate_limits.copy()
        }
    
    def flush_logs(self):
        """Force flush any buffered logs"""
        # In this implementation, we're not using buffering for simplicity
        # But this method is here for future enhancement
        pass
    
    def set_performance_logging(self, enabled: bool):
        """Enable or disable performance logging"""
        self.enable_performance_logging = enabled
        self.logger.info(f"Performance logging {'enabled' if enabled else 'disabled'}")


class LoggerFactory:
    """Factory for creating optimized loggers"""
    
    _loggers: Dict[str, OptimizedLogger] = {}
    _lock = threading.Lock()
    
    @classmethod
    def get_logger(cls, name: str, enable_performance_logging: bool = None) -> OptimizedLogger:
        """Get or create an optimized logger"""
        with cls._lock:
            if name not in cls._loggers:
                if enable_performance_logging is None:
                    enable_performance_logging = ENABLE_PERFORMANCE_LOGGING
                
                cls._loggers[name] = OptimizedLogger(name, enable_performance_logging)
            
            return cls._loggers[name]
    
    @classmethod
    def set_global_performance_logging(cls, enabled: bool):
        """Set performance logging for all existing loggers"""
        global ENABLE_PERFORMANCE_LOGGING
        ENABLE_PERFORMANCE_LOGGING = enabled
        
        with cls._lock:
            for logger in cls._loggers.values():
                logger.set_performance_logging(enabled)
    
    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all loggers"""
        with cls._lock:
            return {name: logger.get_log_stats() for name, logger in cls._loggers.items()}


# Convenience functions for backward compatibility
def log_client(msg: str, logger_name: str = "voice_assistant"):
    """Client logging - optimized"""
    logger = LoggerFactory.get_logger(logger_name)
    logger.log_client(msg)


def log_server(msg: str, logger_name: str = "voice_assistant"):
    """Server logging - optimized"""
    logger = LoggerFactory.get_logger(logger_name)
    logger.log_server(msg)


def log_audio_packet(channel_id: str, direction: str, size: int, packet_num: int, 
                    logger_name: str = "voice_assistant"):
    """Optimized audio packet logging"""
    logger = LoggerFactory.get_logger(logger_name)
    logger.log_audio_packet(channel_id, direction, size, packet_num)


def log_performance_metric(metric_name: str, value: Any, channel_id: str = None,
                          logger_name: str = "voice_assistant"):
    """Optimized performance metric logging"""
    logger = LoggerFactory.get_logger(logger_name)
    logger.log_performance_metric(metric_name, value, channel_id)


# Global logger instance for easy access
optimized_logger = LoggerFactory.get_logger("voice_assistant")