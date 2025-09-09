"""
Comprehensive error handling system for the Voice Assistant.
Provides consistent error handling, logging, and recovery mechanisms.
"""

import logging
import traceback
import functools
import asyncio
from typing import Any, Callable, Dict, Optional, Type, Union, List
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from .constants import ErrorCodes, StatusCodes


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for errors."""
    component: str
    operation: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorInfo:
    """Structured error information."""
    code: ErrorCodes
    message: str
    severity: ErrorSeverity
    context: ErrorContext
    timestamp: datetime = field(default_factory=datetime.utcnow)
    stack_trace: Optional[str] = None
    recovery_suggestions: List[str] = field(default_factory=list)


class VoiceAssistantException(Exception):
    """Base exception for Voice Assistant application."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCodes = ErrorCodes.UNKNOWN_ERROR,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        recovery_suggestions: Optional[List[str]] = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.severity = severity
        self.context = context or ErrorContext("unknown", "unknown")
        self.recovery_suggestions = recovery_suggestions or []
        self.timestamp = datetime.utcnow()


class ConfigurationError(VoiceAssistantException):
    """Configuration-related errors."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message,
            ErrorCodes.CONFIGURATION_ERROR,
            ErrorSeverity.HIGH,
            context,
            [
                "Check configuration file syntax",
                "Verify environment variables",
                "Ensure all required settings are provided"
            ]
        )


class NetworkError(VoiceAssistantException):
    """Network-related errors."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message,
            ErrorCodes.CONNECTION_ERROR,
            ErrorSeverity.MEDIUM,
            context,
            [
                "Check internet connection",
                "Verify API endpoints",
                "Check firewall settings"
            ]
        )


class AudioProcessingError(VoiceAssistantException):
    """Audio processing errors."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message,
            ErrorCodes.AUDIO_PROCESSING_ERROR,
            ErrorSeverity.MEDIUM,
            context,
            [
                "Check audio device connections",
                "Verify audio format compatibility",
                "Ensure sufficient system resources"
            ]
        )


class AIServiceError(VoiceAssistantException):
    """AI service related errors."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message,
            ErrorCodes.AI_API_ERROR,
            ErrorSeverity.MEDIUM,
            context,
            [
                "Check API key validity",
                "Verify quota limits",
                "Check service status"
            ]
        )


class SecurityError(VoiceAssistantException):
    """Security-related errors."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message,
            ErrorCodes.AUTHENTICATION_ERROR,
            ErrorSeverity.HIGH,
            context,
            [
                "Verify authentication credentials",
                "Check API key permissions",
                "Review security settings"
            ]
        )


class ErrorHandler:
    """Centralized error handling and logging."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_counts: Dict[str, int] = {}
        self.error_history: List[ErrorInfo] = []
        self.max_history_size = 1000
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        severity: Optional[ErrorSeverity] = None
    ) -> ErrorInfo:
        """Handle and log an error."""
        
        # Determine error info
        if isinstance(error, VoiceAssistantException):
            error_info = ErrorInfo(
                code=error.error_code,
                message=str(error),
                severity=severity or error.severity,
                context=context or error.context,
                stack_trace=traceback.format_exc(),
                recovery_suggestions=error.recovery_suggestions
            )
        else:
            error_info = ErrorInfo(
                code=ErrorCodes.UNKNOWN_ERROR,
                message=str(error),
                severity=severity or ErrorSeverity.MEDIUM,
                context=context or ErrorContext("unknown", "unknown"),
                stack_trace=traceback.format_exc(),
                recovery_suggestions=["Check logs for more details", "Contact support if issue persists"]
            )
        
        # Log the error
        self._log_error(error_info)
        
        # Track error statistics
        self._track_error(error_info)
        
        # Store in history
        self._store_error(error_info)
        
        return error_info
    
    def _log_error(self, error_info: ErrorInfo):
        """Log error with appropriate level."""
        log_message = (
            f"[{error_info.code.value}] {error_info.message} "
            f"| Component: {error_info.context.component} "
            f"| Operation: {error_info.context.operation}"
        )
        
        if error_info.context.session_id:
            log_message += f" | Session: {error_info.context.session_id}"
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, extra={"error_info": error_info})
        elif error_info.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, extra={"error_info": error_info})
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message, extra={"error_info": error_info})
        else:
            self.logger.info(log_message, extra={"error_info": error_info})
    
    def _track_error(self, error_info: ErrorInfo):
        """Track error statistics."""
        error_key = f"{error_info.code.value}:{error_info.context.component}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
    
    def _store_error(self, error_info: ErrorInfo):
        """Store error in history."""
        self.error_history.append(error_info)
        
        # Maintain history size limit
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics."""
        return {
            "total_errors": len(self.error_history),
            "error_counts": self.error_counts.copy(),
            "recent_errors": [
                {
                    "code": err.code.value,
                    "message": err.message,
                    "severity": err.severity.value,
                    "timestamp": err.timestamp.isoformat(),
                    "component": err.context.component
                }
                for err in self.error_history[-10:]
            ]
        }


def error_handler(
    error_code: ErrorCodes = ErrorCodes.UNKNOWN_ERROR,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    component: str = "unknown",
    operation: str = "unknown",
    recovery_suggestions: Optional[List[str]] = None
):
    """Decorator for automatic error handling."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = ErrorContext(component=component, operation=operation)
                handler = ErrorHandler()
                error_info = handler.handle_error(e, context, severity)
                
                # Re-raise as VoiceAssistantException if not already
                if not isinstance(e, VoiceAssistantException):
                    raise VoiceAssistantException(
                        str(e),
                        error_code,
                        severity,
                        context,
                        recovery_suggestions
                    ) from e
                raise
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                context = ErrorContext(component=component, operation=operation)
                handler = ErrorHandler()
                error_info = handler.handle_error(e, context, severity)
                
                # Re-raise as VoiceAssistantException if not already
                if not isinstance(e, VoiceAssistantException):
                    raise VoiceAssistantException(
                        str(e),
                        error_code,
                        severity,
                        context,
                        recovery_suggestions
                    ) from e
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Decorator for retrying operations on specific errors."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (backoff_factor ** attempt)
                        await asyncio.sleep(wait_time)
                        continue
                    break
            
            # All retries exhausted
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        import time
                        wait_time = delay * (backoff_factor ** attempt)
                        time.sleep(wait_time)
                        continue
                    break
            
            # All retries exhausted
            raise last_exception
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class CircuitBreaker:
    """Circuit breaker pattern for handling cascading failures."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise VoiceAssistantException(
                        "Circuit breaker is OPEN",
                        ErrorCodes.CONNECTION_ERROR,
                        ErrorSeverity.HIGH
                    )
            
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise VoiceAssistantException(
                        "Circuit breaker is OPEN",
                        ErrorCodes.CONNECTION_ERROR,
                        ErrorSeverity.HIGH
                    )
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        
        return (datetime.utcnow() - self.last_failure_time).total_seconds() > self.recovery_timeout
    
    def _on_success(self):
        """Handle successful operation."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


# Global error handler instance
global_error_handler = ErrorHandler()


def handle_error(
    error: Exception,
    context: Optional[ErrorContext] = None,
    severity: Optional[ErrorSeverity] = None
) -> ErrorInfo:
    """Global error handling function."""
    return global_error_handler.handle_error(error, context, severity)


def get_error_statistics() -> Dict[str, Any]:
    """Get global error statistics."""
    return global_error_handler.get_error_statistics()