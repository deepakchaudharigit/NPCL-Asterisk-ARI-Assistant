"""
Standardized error handling framework for consistent error management across the application.
Provides logging, recovery strategies, and error reporting capabilities.
"""

import logging
import traceback
import time
import uuid
from typing import Any, Dict, Optional, Callable, Type, Union, List
from functools import wraps
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    NETWORK = "network"
    AUDIO = "audio"
    AI = "ai"
    TELEPHONY = "telephony"
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    SECURITY = "security"
    PERFORMANCE = "performance"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Comprehensive error information"""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    exception_type: str = ""
    message: str = ""
    traceback: str = ""
    category: ErrorCategory = ErrorCategory.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    context: Dict[str, Any] = field(default_factory=dict)
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_strategy: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp.isoformat(),
            "exception_type": self.exception_type,
            "message": self.message,
            "traceback": self.traceback,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context,
            "recovery_attempted": self.recovery_attempted,
            "recovery_successful": self.recovery_successful,
            "recovery_strategy": self.recovery_strategy
        }


class ErrorHandler:
    """Centralized error handling system"""
    
    def __init__(self):
        self.error_history: List[ErrorInfo] = []
        self.max_history_size = 1000
        self.recovery_strategies: Dict[Type[Exception], Callable] = {}
        self.error_callbacks: List[Callable[[ErrorInfo], None]] = []
        
        # Error statistics
        self.stats = {
            "total_errors": 0,
            "errors_by_category": {cat.value: 0 for cat in ErrorCategory},
            "errors_by_severity": {sev.value: 0 for sev in ErrorSeverity},
            "recovery_attempts": 0,
            "successful_recoveries": 0
        }
        
        # Register default recovery strategies
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """Register default recovery strategies"""
        
        def network_retry_strategy(error_info: ErrorInfo) -> bool:
            """Retry strategy for network errors"""
            try:
                # Simple retry logic - could be enhanced
                time.sleep(1)
                return True
            except Exception:
                return False
        
        def audio_fallback_strategy(error_info: ErrorInfo) -> bool:
            """Fallback strategy for audio errors"""
            try:
                # Could implement audio format fallback, etc.
                logger.warning("Audio error - using fallback processing")
                return True
            except Exception:
                return False
        
        # Register strategies
        self.register_recovery_strategy(ConnectionError, network_retry_strategy)
        self.register_recovery_strategy(TimeoutError, network_retry_strategy)
    
    def register_recovery_strategy(self, exception_type: Type[Exception], 
                                 strategy: Callable[[ErrorInfo], bool]):
        """Register a recovery strategy for specific exception type"""
        self.recovery_strategies[exception_type] = strategy
        logger.debug(f"Registered recovery strategy for {exception_type.__name__}")
    
    def register_error_callback(self, callback: Callable[[ErrorInfo], None]):
        """Register callback to be called when errors occur"""
        self.error_callbacks.append(callback)
    
    def handle_error(self, exception: Exception, context: Optional[Dict[str, Any]] = None,
                    category: Optional[ErrorCategory] = None, 
                    severity: Optional[ErrorSeverity] = None,
                    attempt_recovery: bool = True) -> ErrorInfo:
        """
        Handle an error with comprehensive logging and optional recovery
        
        Args:
            exception: The exception that occurred
            context: Additional context information
            category: Error category (auto-detected if not provided)
            severity: Error severity (auto-detected if not provided)
            attempt_recovery: Whether to attempt automatic recovery
            
        Returns:
            ErrorInfo object with details about the error
        """
        # Create error info
        error_info = ErrorInfo(
            exception_type=type(exception).__name__,
            message=str(exception),
            traceback=traceback.format_exc(),
            context=context or {},
            category=category or self._categorize_error(exception),
            severity=severity or self._assess_severity(exception)
        )
        
        # Update statistics
        self.stats["total_errors"] += 1
        self.stats["errors_by_category"][error_info.category.value] += 1
        self.stats["errors_by_severity"][error_info.severity.value] += 1
        
        # Log the error
        self._log_error(error_info)
        
        # Attempt recovery if enabled
        if attempt_recovery:
            self._attempt_recovery(error_info)
        
        # Store in history
        self._store_error(error_info)
        
        # Trigger callbacks
        self._trigger_callbacks(error_info)
        
        return error_info
    
    def _categorize_error(self, exception: Exception) -> ErrorCategory:
        """Automatically categorize error based on exception type and message"""
        exception_type = type(exception).__name__
        message = str(exception).lower()
        
        # Network-related errors
        if any(keyword in exception_type.lower() for keyword in 
               ['connection', 'timeout', 'network', 'socket', 'http']):
            return ErrorCategory.NETWORK
        
        if any(keyword in message for keyword in 
               ['connection', 'timeout', 'network', 'socket', 'refused']):
            return ErrorCategory.NETWORK
        
        # Audio-related errors
        if any(keyword in message for keyword in 
               ['audio', 'sound', 'microphone', 'speaker', 'wav', 'mp3']):
            return ErrorCategory.AUDIO
        
        # AI-related errors
        if any(keyword in message for keyword in 
               ['gemini', 'ai', 'model', 'generation', 'quota', 'api key']):
            return ErrorCategory.AI
        
        # Telephony-related errors
        if any(keyword in message for keyword in 
               ['asterisk', 'ari', 'channel', 'call', 'sip', 'rtp']):
            return ErrorCategory.TELEPHONY
        
        # Configuration errors
        if any(keyword in exception_type.lower() for keyword in 
               ['validation', 'config', 'setting']):
            return ErrorCategory.CONFIGURATION
        
        # Security errors
        if any(keyword in message for keyword in 
               ['auth', 'permission', 'security', 'token', 'unauthorized']):
            return ErrorCategory.SECURITY
        
        # Performance errors
        if any(keyword in message for keyword in 
               ['memory', 'cpu', 'performance', 'slow', 'latency']):
            return ErrorCategory.PERFORMANCE
        
        return ErrorCategory.UNKNOWN
    
    def _assess_severity(self, exception: Exception) -> ErrorSeverity:
        """Automatically assess error severity"""
        exception_type = type(exception).__name__
        message = str(exception).lower()
        
        # Critical errors
        critical_indicators = [
            'system', 'critical', 'fatal', 'crash', 'corruption',
            'security', 'unauthorized', 'breach'
        ]
        if any(indicator in message for indicator in critical_indicators):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        high_indicators = [
            'failed to start', 'cannot connect', 'service unavailable',
            'quota exceeded', 'authentication failed'
        ]
        if any(indicator in message for indicator in high_indicators):
            return ErrorSeverity.HIGH
        
        # Low severity errors
        low_indicators = [
            'warning', 'deprecated', 'fallback', 'retry'
        ]
        if any(indicator in message for indicator in low_indicators):
            return ErrorSeverity.LOW
        
        # Default to medium
        return ErrorSeverity.MEDIUM
    
    def _log_error(self, error_info: ErrorInfo):
        """Log error with appropriate level based on severity"""
        log_message = f"[{error_info.error_id}] {error_info.exception_type}: {error_info.message}"
        
        if error_info.context:
            log_message += f" | Context: {json.dumps(error_info.context, default=str)}"
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
            logger.critical(f"Traceback: {error_info.traceback}")
        elif error_info.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
            logger.debug(f"Traceback: {error_info.traceback}")
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:  # LOW
            logger.info(log_message)
    
    def _attempt_recovery(self, error_info: ErrorInfo):
        """Attempt automatic error recovery"""
        error_info.recovery_attempted = True
        self.stats["recovery_attempts"] += 1
        
        # Find recovery strategy
        exception_type = None
        for exc_type in self.recovery_strategies:
            if exc_type.__name__ == error_info.exception_type:
                exception_type = exc_type
                break
        
        if exception_type and exception_type in self.recovery_strategies:
            strategy = self.recovery_strategies[exception_type]
            error_info.recovery_strategy = strategy.__name__
            
            try:
                success = strategy(error_info)
                error_info.recovery_successful = success
                
                if success:
                    self.stats["successful_recoveries"] += 1
                    logger.info(f"Successfully recovered from error {error_info.error_id}")
                else:
                    logger.warning(f"Recovery failed for error {error_info.error_id}")
                    
            except Exception as recovery_error:
                logger.error(f"Recovery strategy failed: {recovery_error}")
                error_info.recovery_successful = False
    
    def _store_error(self, error_info: ErrorInfo):
        """Store error in history with size limit"""
        self.error_history.append(error_info)
        
        # Maintain history size limit
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
    
    def _trigger_callbacks(self, error_info: ErrorInfo):
        """Trigger registered error callbacks"""
        for callback in self.error_callbacks:
            try:
                callback(error_info)
            except Exception as callback_error:
                logger.error(f"Error in error callback: {callback_error}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        recent_errors = [e for e in self.error_history 
                        if (datetime.now() - e.timestamp).total_seconds() < 3600]  # Last hour
        
        return {
            **self.stats,
            "recent_errors_count": len(recent_errors),
            "recovery_success_rate": (
                self.stats["successful_recoveries"] / self.stats["recovery_attempts"] * 100
                if self.stats["recovery_attempts"] > 0 else 0
            ),
            "error_history_size": len(self.error_history)
        }
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors"""
        recent = sorted(self.error_history, key=lambda e: e.timestamp, reverse=True)[:limit]
        return [error.to_dict() for error in recent]
    
    def clear_error_history(self):
        """Clear error history"""
        self.error_history.clear()
        logger.info("Error history cleared")


# Global error handler instance
_error_handler = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def handle_errors(logger_instance: logging.Logger, 
                 category: Optional[ErrorCategory] = None,
                 severity: Optional[ErrorSeverity] = None,
                 attempt_recovery: bool = True,
                 reraise: bool = False):
    """
    Decorator for automatic error handling
    
    Args:
        logger_instance: Logger to use for error logging
        category: Error category override
        severity: Error severity override
        attempt_recovery: Whether to attempt recovery
        reraise: Whether to reraise the exception after handling
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler = get_error_handler()
                
                # Add function context
                context = {
                    "function": func.__name__,
                    "module": func.__module__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                }
                
                error_info = error_handler.handle_error(
                    e, context, category, severity, attempt_recovery
                )
                
                if reraise:
                    raise
                
                # Return None or appropriate default for failed operations
                return None
                
        return wrapper
    return decorator


def log_and_handle_error(exception: Exception, 
                        context: Optional[Dict[str, Any]] = None,
                        category: Optional[ErrorCategory] = None,
                        severity: Optional[ErrorSeverity] = None) -> ErrorInfo:
    """
    Convenience function for manual error handling
    
    Args:
        exception: The exception to handle
        context: Additional context
        category: Error category
        severity: Error severity
        
    Returns:
        ErrorInfo object
    """
    return get_error_handler().handle_error(exception, context, category, severity)