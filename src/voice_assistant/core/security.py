"""
Security utilities and input validation for the Voice Assistant.
Provides comprehensive security measures and input sanitization.
"""

import re
import hashlib
import secrets
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from .constants import ErrorCodes
from .error_handling import SecurityError, ErrorContext


logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 10
    window_size: int = 60  # seconds


@dataclass
class SecurityConfig:
    """Security configuration."""
    max_input_length: int = 10000
    allowed_audio_formats: List[str] = field(default_factory=lambda: ["wav", "mp3", "pcm", "slin16"])
    max_audio_duration: int = 300  # seconds
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    enable_rate_limiting: bool = True
    enable_input_sanitization: bool = True
    enable_audit_logging: bool = True


class InputValidator:
    """Comprehensive input validation."""
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        self.logger = logging.getLogger(f"{__name__}.InputValidator")
    
    def validate_text_input(self, text: str, context: str = "general") -> str:
        """Validate and sanitize text input."""
        if not isinstance(text, str):
            raise SecurityError(
                "Input must be a string",
                ErrorContext("security", "validate_text_input", additional_data={"context": context})
            )
        
        # Check length
        if len(text) > self.config.max_input_length:
            raise SecurityError(
                f"Input too long: {len(text)} > {self.config.max_input_length}",
                ErrorContext("security", "validate_text_input", additional_data={"context": context})
            )
        
        # Remove null bytes and control characters
        sanitized = text.replace('\x00', '').replace('\r', '').replace('\n', ' ')
        
        # Remove potentially dangerous patterns
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',  # JavaScript URLs
            r'data:',  # Data URLs
            r'vbscript:',  # VBScript URLs
        ]
        
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        
        # Limit consecutive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        self.logger.debug(f"Validated text input for context: {context}")
        return sanitized
    
    def validate_audio_data(self, audio_data: bytes, format_hint: str = "unknown") -> bytes:
        """Validate audio data."""
        if not isinstance(audio_data, bytes):
            raise SecurityError(
                "Audio data must be bytes",
                ErrorContext("security", "validate_audio_data", additional_data={"format": format_hint})
            )
        
        # Check size
        if len(audio_data) > self.config.max_file_size:
            raise SecurityError(
                f"Audio data too large: {len(audio_data)} > {self.config.max_file_size}",
                ErrorContext("security", "validate_audio_data", additional_data={"format": format_hint})
            )
        
        # Basic format validation
        if format_hint and format_hint not in self.config.allowed_audio_formats:
            raise SecurityError(
                f"Audio format not allowed: {format_hint}",
                ErrorContext("security", "validate_audio_data", additional_data={"format": format_hint})
            )
        
        # Check for empty data
        if len(audio_data) == 0:
            raise SecurityError(
                "Audio data is empty",
                ErrorContext("security", "validate_audio_data", additional_data={"format": format_hint})
            )
        
        self.logger.debug(f"Validated audio data: {len(audio_data)} bytes, format: {format_hint}")
        return audio_data
    
    def validate_api_key(self, api_key: str) -> str:
        """Validate API key format."""
        if not isinstance(api_key, str):
            raise SecurityError(
                "API key must be a string",
                ErrorContext("security", "validate_api_key")
            )
        
        # Remove whitespace
        api_key = api_key.strip()
        
        # Check for placeholder values
        placeholder_values = [
            "your-api-key-here",
            "your-google-api-key-here",
            "placeholder",
            "test",
            "demo"
        ]
        
        if api_key.lower() in placeholder_values:
            raise SecurityError(
                "API key appears to be a placeholder",
                ErrorContext("security", "validate_api_key")
            )
        
        # Check minimum length
        if len(api_key) < 10:
            raise SecurityError(
                "API key too short",
                ErrorContext("security", "validate_api_key")
            )
        
        # Check for suspicious patterns
        if api_key.count(' ') > 2:  # Too many spaces
            raise SecurityError(
                "API key format invalid",
                ErrorContext("security", "validate_api_key")
            )
        
        self.logger.debug("API key validation passed")
        return api_key
    
    def validate_session_id(self, session_id: str) -> str:
        """Validate session ID format."""
        if not isinstance(session_id, str):
            raise SecurityError(
                "Session ID must be a string",
                ErrorContext("security", "validate_session_id")
            )
        
        # Check format (alphanumeric, hyphens, underscores only)
        if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
            raise SecurityError(
                "Session ID contains invalid characters",
                ErrorContext("security", "validate_session_id")
            )
        
        # Check length
        if not (8 <= len(session_id) <= 128):
            raise SecurityError(
                f"Session ID length invalid: {len(session_id)}",
                ErrorContext("security", "validate_session_id")
            )
        
        return session_id
    
    def validate_file_path(self, file_path: str, allowed_dirs: Optional[List[str]] = None) -> str:
        """Validate file path for security."""
        if not isinstance(file_path, str):
            raise SecurityError(
                "File path must be a string",
                ErrorContext("security", "validate_file_path")
            )
        
        # Normalize path
        import os
        normalized_path = os.path.normpath(file_path)
        
        # Check for path traversal
        if '..' in normalized_path or normalized_path.startswith('/'):
            raise SecurityError(
                "Path traversal detected",
                ErrorContext("security", "validate_file_path", additional_data={"path": file_path})
            )
        
        # Check allowed directories
        if allowed_dirs:
            allowed = any(normalized_path.startswith(allowed_dir) for allowed_dir in allowed_dirs)
            if not allowed:
                raise SecurityError(
                    "File path not in allowed directories",
                    ErrorContext("security", "validate_file_path", additional_data={"path": file_path})
                )
        
        return normalized_path


class RateLimiter:
    """Rate limiting implementation."""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.logger = logging.getLogger(f"{__name__}.RateLimiter")
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed under rate limits."""
        current_time = time.time()
        
        # Clean old requests
        self._cleanup_old_requests(identifier, current_time)
        
        # Get current request count
        request_times = self.requests[identifier]
        
        # Check burst limit
        recent_requests = [t for t in request_times if current_time - t < 60]  # Last minute
        if len(recent_requests) >= self.config.burst_limit:
            self.logger.warning(f"Burst limit exceeded for {identifier}")
            return False
        
        # Check per-minute limit
        minute_requests = [t for t in request_times if current_time - t < 60]
        if len(minute_requests) >= self.config.requests_per_minute:
            self.logger.warning(f"Per-minute limit exceeded for {identifier}")
            return False
        
        # Check per-hour limit
        hour_requests = [t for t in request_times if current_time - t < 3600]
        if len(hour_requests) >= self.config.requests_per_hour:
            self.logger.warning(f"Per-hour limit exceeded for {identifier}")
            return False
        
        # Record this request
        self.requests[identifier].append(current_time)
        return True
    
    def _cleanup_old_requests(self, identifier: str, current_time: float):
        """Remove old request records."""
        cutoff_time = current_time - 3600  # Keep last hour
        self.requests[identifier] = [
            t for t in self.requests[identifier] if t > cutoff_time
        ]
    
    def get_stats(self, identifier: str) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        current_time = time.time()
        request_times = self.requests.get(identifier, [])
        
        minute_count = len([t for t in request_times if current_time - t < 60])
        hour_count = len([t for t in request_times if current_time - t < 3600])
        
        return {
            "requests_last_minute": minute_count,
            "requests_last_hour": hour_count,
            "minute_limit": self.config.requests_per_minute,
            "hour_limit": self.config.requests_per_hour,
            "minute_remaining": max(0, self.config.requests_per_minute - minute_count),
            "hour_remaining": max(0, self.config.requests_per_hour - hour_count)
        }


class AuditLogger:
    """Security audit logging."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.AuditLogger")
    
    def log_security_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "INFO"
    ):
        """Log security-related events."""
        audit_data = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "session_id": session_id,
            "details": details or {},
            "severity": severity
        }
        
        log_message = f"SECURITY_EVENT: {event_type}"
        if user_id:
            log_message += f" | User: {user_id}"
        if session_id:
            log_message += f" | Session: {session_id}"
        
        if severity == "CRITICAL":
            self.logger.critical(log_message, extra=audit_data)
        elif severity == "HIGH":
            self.logger.error(log_message, extra=audit_data)
        elif severity == "MEDIUM":
            self.logger.warning(log_message, extra=audit_data)
        else:
            self.logger.info(log_message, extra=audit_data)
    
    def log_authentication_attempt(
        self,
        success: bool,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log authentication attempts."""
        self.log_security_event(
            "authentication_attempt",
            user_id=user_id,
            details={
                "success": success,
                "ip_address": ip_address,
                **(details or {})
            },
            severity="HIGH" if not success else "INFO"
        )
    
    def log_rate_limit_violation(
        self,
        identifier: str,
        limit_type: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log rate limit violations."""
        self.log_security_event(
            "rate_limit_violation",
            details={
                "identifier": identifier,
                "limit_type": limit_type,
                **(details or {})
            },
            severity="MEDIUM"
        )
    
    def log_input_validation_failure(
        self,
        input_type: str,
        reason: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Log input validation failures."""
        self.log_security_event(
            "input_validation_failure",
            user_id=user_id,
            session_id=session_id,
            details={
                "input_type": input_type,
                "reason": reason
            },
            severity="MEDIUM"
        )


class SecurityManager:
    """Main security management class."""
    
    def __init__(
        self,
        security_config: Optional[SecurityConfig] = None,
        rate_limit_config: Optional[RateLimitConfig] = None
    ):
        self.security_config = security_config or SecurityConfig()
        self.rate_limit_config = rate_limit_config or RateLimitConfig()
        
        self.validator = InputValidator(self.security_config)
        self.rate_limiter = RateLimiter(self.rate_limit_config) if self.security_config.enable_rate_limiting else None
        self.audit_logger = AuditLogger() if self.security_config.enable_audit_logging else None
        
        self.logger = logging.getLogger(f"{__name__}.SecurityManager")
    
    def validate_and_sanitize_input(
        self,
        input_data: Any,
        input_type: str,
        context: str = "general",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Any:
        """Validate and sanitize input with comprehensive security checks."""
        try:
            if input_type == "text":
                return self.validator.validate_text_input(input_data, context)
            elif input_type == "audio":
                return self.validator.validate_audio_data(input_data, context)
            elif input_type == "api_key":
                return self.validator.validate_api_key(input_data)
            elif input_type == "session_id":
                return self.validator.validate_session_id(input_data)
            elif input_type == "file_path":
                return self.validator.validate_file_path(input_data)
            else:
                raise SecurityError(
                    f"Unknown input type: {input_type}",
                    ErrorContext("security", "validate_input")
                )
        
        except SecurityError as e:
            if self.audit_logger:
                self.audit_logger.log_input_validation_failure(
                    input_type, str(e), user_id, session_id
                )
            raise
    
    def check_rate_limit(
        self,
        identifier: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """Check rate limits for an identifier."""
        if not self.rate_limiter:
            return True
        
        allowed = self.rate_limiter.is_allowed(identifier)
        
        if not allowed and self.audit_logger:
            self.audit_logger.log_rate_limit_violation(
                identifier,
                "general",
                {"user_id": user_id, "session_id": session_id}
            )
        
        return allowed
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate a cryptographically secure token."""
        return secrets.token_urlsafe(length)
    
    def hash_sensitive_data(self, data: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash sensitive data with salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        
        hash_obj = hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000)
        return hash_obj.hex(), salt
    
    def verify_hash(self, data: str, hash_value: str, salt: str) -> bool:
        """Verify hashed data."""
        computed_hash, _ = self.hash_sensitive_data(data, salt)
        return secrets.compare_digest(computed_hash, hash_value)
    
    def get_security_headers(self) -> Dict[str, str]:
        """Get recommended security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }


# Global security manager instance
global_security_manager = SecurityManager()


def validate_input(
    input_data: Any,
    input_type: str,
    context: str = "general",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> Any:
    """Global input validation function."""
    return global_security_manager.validate_and_sanitize_input(
        input_data, input_type, context, user_id, session_id
    )


def check_rate_limit(
    identifier: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> bool:
    """Global rate limiting function."""
    return global_security_manager.check_rate_limit(identifier, user_id, session_id)