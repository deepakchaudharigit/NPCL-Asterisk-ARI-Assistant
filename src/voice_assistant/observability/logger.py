"""
Structured Logging with Correlation IDs and Context
Enhanced logging for observability and debugging
"""

import json
import time
import logging
import sys
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import threading
from pathlib import Path

class LogLevel(Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class LogContext:
    """Log context for correlation"""
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    component: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        return {k: v for k, v in asdict(self).items() if v is not None}

class StructuredLogger:
    """Structured logger with context and correlation support"""
    
    def __init__(self, name: str, 
                 level: LogLevel = LogLevel.INFO,
                 output_file: Optional[str] = None,
                 enable_console: bool = True,
                 json_format: bool = True):
        self.name = name
        self.level = level
        self.output_file = output_file
        self.enable_console = enable_console
        self.json_format = json_format
        
        # Context storage
        self._local = threading.local()
        
        # Setup loggers
        self.logger = self._setup_logger()
        
        # Statistics
        self.stats = {
            'logs_written': 0,
            'errors_logged': 0,
            'warnings_logged': 0
        }
    
    def _setup_logger(self) -> logging.Logger:
        """Setup the underlying logger"""
        logger = logging.getLogger(self.name)
        logger.setLevel(getattr(logging, self.level.value))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Console handler
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(self._get_formatter())
            logger.addHandler(console_handler)
        
        # File handler
        if self.output_file:
            file_path = Path(self.output_file)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(self.output_file)
            file_handler.setFormatter(self._get_formatter())
            logger.addHandler(file_handler)
        
        return logger
    
    def _get_formatter(self) -> logging.Formatter:
        """Get log formatter"""
        if self.json_format:
            return JsonFormatter()
        else:
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
    
    def set_context(self, context: LogContext):
        """Set logging context for current thread"""
        self._local.context = context
    
    def get_context(self) -> LogContext:
        """Get current logging context"""
        return getattr(self._local, 'context', LogContext())
    
    def clear_context(self):
        """Clear logging context"""
        self._local.context = LogContext()
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log(LogLevel.WARNING, message, **kwargs)
        self.stats['warnings_logged'] += 1
    
    def error(self, message: str, exception: Exception = None, **kwargs):
        """Log error message"""
        if exception:
            kwargs['exception'] = {
                'type': type(exception).__name__,
                'message': str(exception),
                'traceback': self._format_exception(exception)
            }
        
        self._log(LogLevel.ERROR, message, **kwargs)
        self.stats['errors_logged'] += 1
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log(LogLevel.CRITICAL, message, **kwargs)
    
    def _log(self, level: LogLevel, message: str, **kwargs):
        """Internal logging method"""
        # Get current context
        context = self.get_context()
        
        # Create log record
        log_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level.value,
            'logger': self.name,
            'message': message,
            **context.to_dict(),
            **kwargs
        }
        
        # Log using underlying logger
        log_level = getattr(logging, level.value)
        
        if self.json_format:
            self.logger.log(log_level, json.dumps(log_record, default=str))
        else:
            # Format for text logging
            context_str = self._format_context(context)
            full_message = f"{context_str}{message}"
            if kwargs:
                full_message += f" {json.dumps(kwargs, default=str)}"
            
            self.logger.log(log_level, full_message)
        
        self.stats['logs_written'] += 1
    
    def _format_context(self, context: LogContext) -> str:
        """Format context for text logging"""
        parts = []
        
        if context.trace_id:
            parts.append(f"trace_id={context.trace_id[:8]}")
        if context.span_id:
            parts.append(f"span_id={context.span_id[:8]}")
        if context.user_id:
            parts.append(f"user_id={context.user_id}")
        if context.session_id:
            parts.append(f"session_id={context.session_id[:8]}")
        if context.component:
            parts.append(f"component={context.component}")
        
        return f"[{', '.join(parts)}] " if parts else ""
    
    def _format_exception(self, exception: Exception) -> str:
        """Format exception for logging"""
        import traceback
        return traceback.format_exception(type(exception), exception, exception.__traceback__)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get logging statistics"""
        return {
            **self.stats,
            'logger_name': self.name,
            'level': self.level.value,
            'timestamp': time.time()
        }

class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        # The message should already be JSON if using StructuredLogger
        try:
            # Try to parse as JSON first
            json.loads(record.getMessage())
            return record.getMessage()
        except json.JSONDecodeError:
            # Fallback to creating JSON structure
            log_data = {
                'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            
            if record.exc_info:
                log_data['exception'] = self.formatException(record.exc_info)
            
            return json.dumps(log_data, default=str)

class LogAggregator:
    """Aggregates logs for analysis and alerting"""
    
    def __init__(self, buffer_size: int = 1000):
        self.buffer_size = buffer_size
        self.log_buffer: List[Dict[str, Any]] = []
        self.error_patterns: Dict[str, int] = {}
        self.warning_patterns: Dict[str, int] = {}
        self._lock = threading.Lock()
    
    def add_log(self, log_record: Dict[str, Any]):
        """Add log record to aggregator"""
        with self._lock:
            self.log_buffer.append(log_record)
            
            # Track error patterns
            if log_record.get('level') == 'ERROR':
                message = log_record.get('message', '')
                pattern = self._extract_pattern(message)
                self.error_patterns[pattern] = self.error_patterns.get(pattern, 0) + 1
            
            elif log_record.get('level') == 'WARNING':
                message = log_record.get('message', '')
                pattern = self._extract_pattern(message)
                self.warning_patterns[pattern] = self.warning_patterns.get(pattern, 0) + 1
            
            # Maintain buffer size
            if len(self.log_buffer) > self.buffer_size:
                self.log_buffer = self.log_buffer[-self.buffer_size:]
    
    def get_error_summary(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get summary of most common errors"""
        with self._lock:
            sorted_errors = sorted(
                self.error_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            return [
                {'pattern': pattern, 'count': count}
                for pattern, count in sorted_errors[:limit]
            ]
    
    def get_recent_logs(self, level: Optional[str] = None, 
                       limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent logs, optionally filtered by level"""
        with self._lock:
            logs = self.log_buffer.copy()
        
        if level:
            logs = [log for log in logs if log.get('level') == level]
        
        return logs[-limit:]
    
    def _extract_pattern(self, message: str) -> str:
        """Extract pattern from log message for grouping"""
        # Simple pattern extraction - replace numbers and IDs with placeholders
        import re
        
        # Replace UUIDs
        pattern = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', 
                        '<UUID>', message)
        
        # Replace numbers
        pattern = re.sub(r'\b\d+\b', '<NUMBER>', pattern)
        
        # Replace IP addresses
        pattern = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '<IP>', pattern)
        
        return pattern

class CorrelationLogger:
    """Logger that automatically includes correlation IDs"""
    
    def __init__(self, base_logger: StructuredLogger):
        self.base_logger = base_logger
    
    def with_trace(self, trace_id: str, span_id: str = None):
        """Create logger with trace context"""
        context = self.base_logger.get_context()
        context.trace_id = trace_id
        if span_id:
            context.span_id = span_id
        
        self.base_logger.set_context(context)
        return self
    
    def with_user(self, user_id: str):
        """Create logger with user context"""
        context = self.base_logger.get_context()
        context.user_id = user_id
        self.base_logger.set_context(context)
        return self
    
    def with_session(self, session_id: str):
        """Create logger with session context"""
        context = self.base_logger.get_context()
        context.session_id = session_id
        self.base_logger.set_context(context)
        return self
    
    def with_component(self, component: str):
        """Create logger with component context"""
        context = self.base_logger.get_context()
        context.component = component
        self.base_logger.set_context(context)
        return self
    
    def __getattr__(self, name):
        """Delegate to base logger"""
        return getattr(self.base_logger, name)

# Global logger registry
_loggers: Dict[str, StructuredLogger] = {}
_aggregator: Optional[LogAggregator] = None

def get_logger(name: str, **kwargs) -> StructuredLogger:
    """Get or create a structured logger"""
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name, **kwargs)
    return _loggers[name]

def get_correlation_logger(name: str, **kwargs) -> CorrelationLogger:
    """Get correlation logger"""
    base_logger = get_logger(name, **kwargs)
    return CorrelationLogger(base_logger)

def setup_log_aggregation(buffer_size: int = 1000):
    """Setup global log aggregation"""
    global _aggregator
    _aggregator = LogAggregator(buffer_size)
    
    # Hook into all existing loggers
    for logger in _loggers.values():
        _hook_logger_to_aggregator(logger)

def _hook_logger_to_aggregator(logger: StructuredLogger):
    """Hook logger to send logs to aggregator"""
    original_log = logger._log
    
    def hooked_log(level, message, **kwargs):
        result = original_log(level, message, **kwargs)
        
        if _aggregator:
            context = logger.get_context()
            log_record = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': level.value,
                'logger': logger.name,
                'message': message,
                **context.to_dict(),
                **kwargs
            }
            _aggregator.add_log(log_record)
        
        return result
    
    logger._log = hooked_log

def get_log_aggregator() -> Optional[LogAggregator]:
    """Get global log aggregator"""
    return _aggregator