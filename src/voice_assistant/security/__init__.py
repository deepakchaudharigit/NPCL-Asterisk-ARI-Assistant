"""
Security module for Voice Assistant
Provides authentication, authorization, rate limiting, and input validation
"""

# Import modules with graceful fallback
try:
    from .auth_manager import AuthManager, JWTAuthManager
except ImportError:
    AuthManager = None
    JWTAuthManager = None

try:
    from .rate_limiter import RateLimiter, TokenBucketRateLimiter
except ImportError:
    RateLimiter = None
    TokenBucketRateLimiter = None

try:
    from .input_validator import InputValidator, SecurityValidator
except ImportError:
    InputValidator = None
    SecurityValidator = None

try:
    from .security_manager import SecurityManager
except ImportError:
    SecurityManager = None

try:
    from .encryption import EncryptionManager
except ImportError:
    EncryptionManager = None

try:
    from .audit_logger import AuditLogger
except ImportError:
    AuditLogger = None

try:
    from .security_integration import add_security_to_app
except ImportError:
    add_security_to_app = None

__all__ = [
    'AuthManager',
    'JWTAuthManager', 
    'RateLimiter',
    'TokenBucketRateLimiter',
    'InputValidator',
    'SecurityValidator',
    'SecurityManager',
    'EncryptionManager',
    'AuditLogger',
    'add_security_to_app'
]