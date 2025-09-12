"""
Complete security integration for production deployment.
Implements authentication, authorization, rate limiting, and security headers.
"""

import logging
import time
import hashlib
import secrets
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..utils.dependency_manager import safe_import
from ..utils.error_handler import get_error_handler, ErrorSeverity
from config.production_settings import get_production_settings

# Optional imports
jwt = safe_import("jwt", "PyJWT", required=False)
redis = safe_import("redis", "redis", required=False)

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security levels for different endpoints"""
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    ADMIN = "admin"
    SYSTEM = "system"


@dataclass
class RateLimitRule:
    """Rate limiting rule definition"""
    requests_per_minute: int
    burst_limit: int
    window_minutes: int = 1


@dataclass
class SecurityConfig:
    """Security configuration"""
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    api_key_header: str = "X-API-Key"
    rate_limit_header: str = "X-RateLimit-Limit"
    enable_cors: bool = True
    cors_origins: List[str] = None
    allowed_hosts: List[str] = None
    enable_security_headers: bool = True


class SecurityManager:
    """Comprehensive security management system"""
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        self.settings = get_production_settings()
        self.config = config or self._create_default_config()
        self.error_handler = get_error_handler()
        
        # Rate limiting storage
        self.rate_limit_storage = {}
        self.redis_client = None
        
        # API keys storage (in production, use database)
        self.api_keys = {}
        
        # JWT settings
        self.jwt_secret = self.config.jwt_secret_key
        self.jwt_algorithm = self.config.jwt_algorithm
        
        # Security rules
        self.rate_limit_rules = {
            SecurityLevel.PUBLIC: RateLimitRule(200, 50),
            SecurityLevel.AUTHENTICATED: RateLimitRule(1000, 100),
            SecurityLevel.ADMIN: RateLimitRule(2000, 200),
            SecurityLevel.SYSTEM: RateLimitRule(5000, 500)
        }
        
        # Initialize Redis if available
        self._init_redis()
        
        # Load API keys
        self._load_api_keys()
        
        logger.info("Security manager initialized")
    
    def _create_default_config(self) -> SecurityConfig:
        """Create default security configuration"""
        return SecurityConfig(
            jwt_secret_key=secrets.token_urlsafe(32),
            cors_origins=self.settings.get_security_config().get("cors_origins", ["*"]),
            allowed_hosts=self.settings.get_security_config().get("allowed_hosts", ["*"]),
            enable_security_headers=self.settings.enable_security_headers
        )
    
    def _init_redis(self):
        """Initialize Redis connection for rate limiting"""
        if not redis or not self.settings.enable_redis:
            logger.info("Redis not available - using in-memory rate limiting")
            return
        
        try:
            self.redis_client = redis.Redis.from_url(
                self.settings.redis_url,
                decode_responses=True,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connected for rate limiting")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None
    
    def _load_api_keys(self):
        """Load API keys (in production, load from secure storage)"""
        # Default API keys for development/testing
        self.api_keys = {
            "npcl-admin-key": {
                "name": "NPCL Admin",
                "level": SecurityLevel.ADMIN,
                "created": datetime.now(),
                "last_used": None,
                "usage_count": 0
            },
            "npcl-system-key": {
                "name": "NPCL System",
                "level": SecurityLevel.SYSTEM,
                "created": datetime.now(),
                "last_used": None,
                "usage_count": 0
            }
        }
        
        # In production, load from environment or secure storage
        if hasattr(self.settings, 'api_keys') and self.settings.api_keys:
            self.api_keys.update(self.settings.api_keys)
    
    def create_jwt_token(self, user_id: str, permissions: List[str] = None) -> str:
        """Create JWT token for user"""
        if not jwt:
            raise ImportError("PyJWT is required for JWT token creation. Install with: pip install PyJWT")
        
        payload = {
            "user_id": user_id,
            "permissions": permissions or [],
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=self.config.jwt_expiration_hours),
            "iss": "npcl-voice-assistant"
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        if not jwt:
            raise ImportError("PyJWT is required for JWT token verification. Install with: pip install PyJWT")
        
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def verify_api_key(self, api_key: str) -> Dict[str, Any]:
        """Verify API key and return key info"""
        if api_key not in self.api_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        key_info = self.api_keys[api_key]
        
        # Update usage statistics
        key_info["last_used"] = datetime.now()
        key_info["usage_count"] += 1
        
        return key_info
    
    def check_rate_limit(self, identifier: str, rule: RateLimitRule) -> bool:
        """Check if request is within rate limit"""
        current_time = time.time()
        window_start = current_time - (rule.window_minutes * 60)
        
        if self.redis_client:
            return self._check_rate_limit_redis(identifier, rule, current_time, window_start)
        else:
            return self._check_rate_limit_memory(identifier, rule, current_time, window_start)
    
    def _check_rate_limit_redis(self, identifier: str, rule: RateLimitRule, 
                               current_time: float, window_start: float) -> bool:
        """Check rate limit using Redis"""
        try:
            pipe = self.redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(identifier, 0, window_start)
            
            # Count current requests
            pipe.zcard(identifier)
            
            # Add current request
            pipe.zadd(identifier, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(identifier, rule.window_minutes * 60)
            
            results = pipe.execute()
            current_count = results[1]
            
            return current_count < rule.requests_per_minute
            
        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}")
            # Fallback to memory-based rate limiting
            return self._check_rate_limit_memory(identifier, rule, current_time, window_start)
    
    def _check_rate_limit_memory(self, identifier: str, rule: RateLimitRule,
                                current_time: float, window_start: float) -> bool:
        """Check rate limit using in-memory storage"""
        if identifier not in self.rate_limit_storage:
            self.rate_limit_storage[identifier] = []
        
        requests = self.rate_limit_storage[identifier]
        
        # Remove old requests
        requests[:] = [req_time for req_time in requests if req_time > window_start]
        
        # Check limit
        if len(requests) >= rule.requests_per_minute:
            return False
        
        # Add current request
        requests.append(current_time)
        
        return True
    
    def get_client_identifier(self, request: Request) -> str:
        """Get unique identifier for client (IP + User-Agent hash)"""
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "")
        
        # Create hash of IP + User-Agent for privacy
        identifier_string = f"{client_ip}:{user_agent}"
        return hashlib.sha256(identifier_string.encode()).hexdigest()[:16]
    
    def sanitize_input(self, input_data: str, max_length: int = 1000) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not input_data:
            return ""
        
        # Truncate to max length
        sanitized = input_data[:max_length]
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\r', '\n']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # Remove SQL injection patterns
        sql_patterns = [
            'DROP TABLE', 'DELETE FROM', 'INSERT INTO', 'UPDATE SET',
            'UNION SELECT', 'OR 1=1', 'AND 1=1', '--', '/*', '*/'
        ]
        
        sanitized_upper = sanitized.upper()
        for pattern in sql_patterns:
            if pattern in sanitized_upper:
                # Log potential attack
                self.error_handler.handle_error(
                    Exception(f"Potential SQL injection attempt: {pattern}"),
                    {"input": input_data[:100], "pattern": pattern},
                    severity=ErrorSeverity.HIGH
                )
                # Remove the pattern
                sanitized = sanitized.replace(pattern.lower(), '')
                sanitized = sanitized.replace(pattern.upper(), '')
        
        return sanitized.strip()


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for FastAPI"""
    
    def __init__(self, app, security_manager: SecurityManager):
        super().__init__(app)
        self.security_manager = security_manager
        self.settings = get_production_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through security middleware"""
        
        # Add security headers
        response = await call_next(request)
        
        if self.security_manager.config.enable_security_headers:
            self._add_security_headers(response)
        
        return response
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }
        
        for header, value in headers.items():
            response.headers[header] = value


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app, security_manager: SecurityManager):
        super().__init__(app)
        self.security_manager = security_manager
        self.settings = get_production_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to requests"""
        
        if not self.settings.enable_rate_limiting:
            return await call_next(request)
        
        # Get client identifier
        client_id = self.security_manager.get_client_identifier(request)
        
        # Determine security level based on endpoint
        security_level = self._get_endpoint_security_level(request.url.path)
        
        # Get rate limit rule
        rule = self.security_manager.rate_limit_rules[security_level]
        
        # Check rate limit
        if not self.security_manager.check_rate_limit(client_id, rule):
            # Log rate limit violation
            self.security_manager.error_handler.handle_error(
                Exception("Rate limit exceeded"),
                {
                    "client_id": client_id,
                    "endpoint": request.url.path,
                    "method": request.method,
                    "security_level": security_level.value
                },
                severity=ErrorSeverity.MEDIUM
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "Retry-After": str(rule.window_minutes * 60),
                    "X-RateLimit-Limit": str(rule.requests_per_minute),
                    "X-RateLimit-Window": str(rule.window_minutes)
                }
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(rule.requests_per_minute)
        response.headers["X-RateLimit-Window"] = str(rule.window_minutes)
        
        return response
    
    def _get_endpoint_security_level(self, path: str) -> SecurityLevel:
        """Determine security level for endpoint"""
        if path.startswith("/admin"):
            return SecurityLevel.ADMIN
        elif path.startswith("/system"):
            return SecurityLevel.SYSTEM
        elif path in ["/health", "/metrics", "/docs", "/openapi.json"]:
            return SecurityLevel.PUBLIC
        else:
            return SecurityLevel.AUTHENTICATED


# Authentication dependencies
security = HTTPBearer()


def get_security_manager() -> SecurityManager:
    """Get security manager instance"""
    return SecurityManager()


def authenticate_jwt(credentials: HTTPAuthorizationCredentials = Depends(security),
                    security_manager: SecurityManager = Depends(get_security_manager)) -> Dict[str, Any]:
    """Authenticate using JWT token"""
    return security_manager.verify_jwt_token(credentials.credentials)


def authenticate_api_key(request: Request,
                        security_manager: SecurityManager = Depends(get_security_manager)) -> Dict[str, Any]:
    """Authenticate using API key"""
    api_key = request.headers.get(security_manager.config.api_key_header)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    return security_manager.verify_api_key(api_key)


def require_admin(auth_data: Dict[str, Any] = Depends(authenticate_api_key)) -> Dict[str, Any]:
    """Require admin level access"""
    if auth_data.get("level") != SecurityLevel.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return auth_data


def require_system(auth_data: Dict[str, Any] = Depends(authenticate_api_key)) -> Dict[str, Any]:
    """Require system level access"""
    if auth_data.get("level") not in [SecurityLevel.ADMIN, SecurityLevel.SYSTEM]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System access required"
        )
    return auth_data


def add_security_to_app(app: FastAPI, security_manager: Optional[SecurityManager] = None):
    """Add comprehensive security to FastAPI application"""
    
    if security_manager is None:
        security_manager = SecurityManager()
    
    settings = get_production_settings()
    security_config = settings.get_security_config()
    
    # Add CORS middleware
    if security_config.get("enable_cors", True):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=security_config.get("cors_origins", ["*"]),
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
        )
    
    # Add trusted host middleware
    if security_config.get("allowed_hosts"):
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=security_config["allowed_hosts"]
        )
    
    # Add custom security middleware
    app.add_middleware(SecurityMiddleware, security_manager=security_manager)
    
    # Add rate limiting middleware
    if settings.enable_rate_limiting:
        app.add_middleware(RateLimitMiddleware, security_manager=security_manager)
    
    # Add security endpoints
    @app.post("/auth/token")
    async def create_token(user_id: str, permissions: List[str] = None):
        """Create JWT token"""
        token = security_manager.create_jwt_token(user_id, permissions)
        return {"access_token": token, "token_type": "bearer"}
    
    @app.get("/auth/verify")
    async def verify_token(auth_data: Dict[str, Any] = Depends(authenticate_jwt)):
        """Verify JWT token"""
        return {"valid": True, "user_id": auth_data["user_id"]}
    
    @app.get("/security/status")
    async def security_status(auth_data: Dict[str, Any] = Depends(require_admin)):
        """Get security system status"""
        return {
            "rate_limiting_enabled": settings.enable_rate_limiting,
            "security_headers_enabled": security_manager.config.enable_security_headers,
            "cors_enabled": security_config.get("enable_cors", True),
            "api_keys_count": len(security_manager.api_keys),
            "redis_available": security_manager.redis_client is not None
        }
    
    logger.info("Security integration completed")
    
    return security_manager