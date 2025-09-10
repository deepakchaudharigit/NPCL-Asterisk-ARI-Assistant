"""
Centralized Security Manager
Coordinates all security components and provides unified security interface
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import logging

from .auth_manager import AuthManager, User
from .rate_limiter import RateLimiter, RateLimit, RateLimitResult
from .input_validator import SecurityValidator, ValidationResult, SecurityThreat
from .audit_logger import AuditLogger
from .encryption import EncryptionManager

logger = logging.getLogger(__name__)

@dataclass
class SecurityContext:
    """Security context for requests"""
    user: Optional[User] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

@dataclass
class SecurityResult:
    """Result of security check"""
    allowed: bool
    user: Optional[User] = None
    rate_limit_result: Optional[RateLimitResult] = None
    validation_result: Optional[ValidationResult] = None
    threats_detected: List[SecurityThreat] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.threats_detected is None:
            self.threats_detected = []

class SecurityManager:
    """Centralized security manager"""
    
    def __init__(self, 
                 auth_manager: AuthManager,
                 rate_limiter: RateLimiter,
                 input_validator: SecurityValidator = None,
                 audit_logger: AuditLogger = None,
                 encryption_manager: EncryptionManager = None):
        self.auth_manager = auth_manager
        self.rate_limiter = rate_limiter
        self.input_validator = input_validator or SecurityValidator()
        self.audit_logger = audit_logger or AuditLogger()
        self.encryption_manager = encryption_manager or EncryptionManager()
        
        # Security configuration
        self.default_rate_limits = {
            'api_calls': RateLimit(requests=1000, window=3600),  # 1000/hour
            'auth_attempts': RateLimit(requests=5, window=300),   # 5/5min
            'voice_sessions': RateLimit(requests=10, window=3600), # 10/hour
            'file_uploads': RateLimit(requests=20, window=3600),   # 20/hour
        }
        
        self.security_policies = {
            'require_auth': True,
            'require_encryption': True,
            'log_all_requests': True,
            'block_suspicious_ips': True,
            'validate_all_inputs': True,
        }
        
        # Threat tracking
        self.threat_scores: Dict[str, float] = {}
        self.blocked_ips: set = set()
        self.suspicious_patterns: Dict[str, int] = {}
    
    async def authenticate_request(self, credentials: Dict[str, Any],
                                 context: SecurityContext) -> SecurityResult:
        """Authenticate a request with comprehensive security checks"""
        try:
            # Log authentication attempt
            await self.audit_logger.log_auth_attempt(
                context.ip_address, credentials.get('username'), context.timestamp
            )
            
            # Check rate limit for authentication attempts
            rate_limit_key = f"auth:{context.ip_address}"
            rate_result = await self.rate_limiter.is_allowed(
                rate_limit_key, self.default_rate_limits['auth_attempts']
            )
            
            if not rate_result.allowed:
                await self.audit_logger.log_security_event(
                    'rate_limit_exceeded', context.ip_address, 
                    {'endpoint': 'auth', 'remaining': rate_result.remaining}
                )
                return SecurityResult(
                    allowed=False,
                    rate_limit_result=rate_result,
                    error_message="Rate limit exceeded for authentication"
                )
            
            # Validate input credentials
            validation_result = self.input_validator.validate_with_context(
                credentials, {
                    'ip_address': context.ip_address,
                    'user_agent': context.user_agent
                }
            )
            
            if not validation_result.is_valid:
                await self.audit_logger.log_security_event(
                    'invalid_credentials', context.ip_address,
                    {'threats': validation_result.threats, 'errors': validation_result.errors}
                )
                return SecurityResult(
                    allowed=False,
                    validation_result=validation_result,
                    threats_detected=validation_result.threats or [],
                    error_message="Invalid credentials format"
                )
            
            # Authenticate user
            user = await self.auth_manager.authenticate(credentials)
            
            if user:
                await self.audit_logger.log_successful_auth(
                    user.user_id, context.ip_address, context.timestamp
                )
                return SecurityResult(
                    allowed=True,
                    user=user,
                    rate_limit_result=rate_result,
                    validation_result=validation_result
                )
            else:
                await self.audit_logger.log_failed_auth(
                    credentials.get('username'), context.ip_address, context.timestamp
                )
                return SecurityResult(
                    allowed=False,
                    rate_limit_result=rate_result,
                    error_message="Authentication failed"
                )
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            await self.audit_logger.log_security_event(
                'auth_error', context.ip_address, {'error': str(e)}
            )
            return SecurityResult(
                allowed=False,
                error_message="Authentication system error"
            )
    
    async def authorize_request(self, user: User, resource: str, action: str,
                              context: SecurityContext) -> SecurityResult:
        """Authorize a request with security checks"""
        try:
            # Check if user is authorized
            authorized = await self.auth_manager.authorize(user, resource, action)
            
            if not authorized:
                await self.audit_logger.log_authorization_failure(
                    user.user_id, resource, action, context.ip_address
                )
                return SecurityResult(
                    allowed=False,
                    user=user,
                    error_message=f"Not authorized for {action} on {resource}"
                )
            
            # Check rate limits for API calls
            rate_limit_key = f"api:{user.user_id}:{resource}"
            rate_result = await self.rate_limiter.is_allowed(
                rate_limit_key, self.default_rate_limits['api_calls']
            )
            
            if not rate_result.allowed:
                await self.audit_logger.log_security_event(
                    'rate_limit_exceeded', context.ip_address,
                    {'user_id': user.user_id, 'resource': resource}
                )
                return SecurityResult(
                    allowed=False,
                    user=user,
                    rate_limit_result=rate_result,
                    error_message="Rate limit exceeded"
                )
            
            await self.audit_logger.log_successful_authorization(
                user.user_id, resource, action, context.ip_address
            )
            
            return SecurityResult(
                allowed=True,
                user=user,
                rate_limit_result=rate_result
            )
            
        except Exception as e:
            logger.error(f"Authorization error: {e}")
            return SecurityResult(
                allowed=False,
                user=user,
                error_message="Authorization system error"
            )
    
    async def validate_request_data(self, data: Any, endpoint: str,
                                  context: SecurityContext) -> SecurityResult:
        """Validate request data for security threats"""
        try:
            # Validate input data
            if isinstance(data, dict):
                validation_result = self.input_validator.validate_api_request(data, endpoint)
            else:
                validation_result = self.input_validator.validate_with_context(
                    data, {
                        'ip_address': context.ip_address,
                        'user_agent': context.user_agent,
                        'user_id': context.user.user_id if context.user else None
                    }
                )
            
            if not validation_result.is_valid:
                await self.audit_logger.log_security_event(
                    'input_validation_failed', context.ip_address,
                    {
                        'endpoint': endpoint,
                        'threats': validation_result.threats,
                        'errors': validation_result.errors,
                        'user_id': context.user.user_id if context.user else None
                    }
                )
                
                # Update threat score for IP
                await self._update_threat_score(context.ip_address, validation_result.threats)
            
            return SecurityResult(
                allowed=validation_result.is_valid,
                validation_result=validation_result,
                threats_detected=validation_result.threats or []
            )
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return SecurityResult(
                allowed=False,
                error_message="Validation system error"
            )
    
    async def check_voice_session_security(self, audio_data: bytes,
                                         context: SecurityContext) -> SecurityResult:
        """Security checks specific to voice sessions"""
        try:
            # Check rate limit for voice sessions
            rate_limit_key = f"voice:{context.user.user_id if context.user else context.ip_address}"
            rate_result = await self.rate_limiter.is_allowed(
                rate_limit_key, self.default_rate_limits['voice_sessions']
            )
            
            if not rate_result.allowed:
                return SecurityResult(
                    allowed=False,
                    rate_limit_result=rate_result,
                    error_message="Voice session rate limit exceeded"
                )
            
            # Validate audio data
            validation_result = self.input_validator.validate_audio_data(audio_data)
            
            if not validation_result.is_valid:
                await self.audit_logger.log_security_event(
                    'invalid_audio_data', context.ip_address,
                    {
                        'errors': validation_result.errors,
                        'user_id': context.user.user_id if context.user else None
                    }
                )
                return SecurityResult(
                    allowed=False,
                    validation_result=validation_result,
                    error_message="Invalid audio data"
                )
            
            # Log voice session start
            await self.audit_logger.log_voice_session(
                context.user.user_id if context.user else 'anonymous',
                context.ip_address,
                len(audio_data)
            )
            
            return SecurityResult(
                allowed=True,
                rate_limit_result=rate_result,
                validation_result=validation_result
            )
            
        except Exception as e:
            logger.error(f"Voice session security error: {e}")
            return SecurityResult(
                allowed=False,
                error_message="Voice session security check failed"
            )
    
    async def encrypt_sensitive_data(self, data: Any) -> str:
        """Encrypt sensitive data"""
        return await self.encryption_manager.encrypt(data)
    
    async def decrypt_sensitive_data(self, encrypted_data: str) -> Any:
        """Decrypt sensitive data"""
        return await self.encryption_manager.decrypt(encrypted_data)
    
    async def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP address is blocked"""
        return ip_address in self.blocked_ips
    
    async def block_ip(self, ip_address: str, reason: str = None):
        """Block an IP address"""
        self.blocked_ips.add(ip_address)
        await self.audit_logger.log_security_event(
            'ip_blocked', ip_address, {'reason': reason}
        )
    
    async def unblock_ip(self, ip_address: str):
        """Unblock an IP address"""
        self.blocked_ips.discard(ip_address)
        await self.audit_logger.log_security_event(
            'ip_unblocked', ip_address, {}
        )
    
    async def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics and statistics"""
        return {
            'blocked_ips_count': len(self.blocked_ips),
            'threat_scores': dict(list(self.threat_scores.items())[:10]),  # Top 10
            'suspicious_patterns': dict(list(self.suspicious_patterns.items())[:10]),
            'audit_stats': await self.audit_logger.get_statistics(),
            'timestamp': time.time()
        }
    
    async def _update_threat_score(self, ip_address: str, threats: List[SecurityThreat]):
        """Update threat score for IP address"""
        if not threats:
            return
        
        current_score = self.threat_scores.get(ip_address, 0.0)
        
        # Increase threat score based on threat types
        threat_weights = {
            SecurityThreat.XSS: 0.3,
            SecurityThreat.SQL_INJECTION: 0.4,
            SecurityThreat.COMMAND_INJECTION: 0.5,
            SecurityThreat.PATH_TRAVERSAL: 0.3,
            SecurityThreat.SCRIPT_INJECTION: 0.4,
            SecurityThreat.MALICIOUS_FILE: 0.6,
            SecurityThreat.SUSPICIOUS_PATTERN: 0.2
        }
        
        for threat in threats:
            current_score += threat_weights.get(threat, 0.1)
        
        self.threat_scores[ip_address] = min(current_score, 1.0)
        
        # Auto-block if threat score is too high
        if current_score >= 0.8:
            await self.block_ip(ip_address, f"High threat score: {current_score}")
    
    async def cleanup_old_data(self, max_age_hours: int = 24):
        """Clean up old security data"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        # Clean up threat scores
        expired_ips = [
            ip for ip, score in self.threat_scores.items()
            if score < 0.1  # Low threat scores
        ]
        
        for ip in expired_ips:
            del self.threat_scores[ip]
        
        # Clean up audit logs
        await self.audit_logger.cleanup_old_logs(max_age_hours)
        
        logger.info(f"Cleaned up {len(expired_ips)} old threat scores")

class SecurityMiddleware:
    """Middleware for applying security checks to requests"""
    
    def __init__(self, security_manager: SecurityManager):
        self.security_manager = security_manager
    
    async def process_request(self, request_data: Dict[str, Any],
                            endpoint: str, context: SecurityContext) -> SecurityResult:
        """Process request through all security checks"""
        
        # Check if IP is blocked
        if context.ip_address and await self.security_manager.is_ip_blocked(context.ip_address):
            return SecurityResult(
                allowed=False,
                error_message="IP address is blocked"
            )
        
        # Validate request data
        validation_result = await self.security_manager.validate_request_data(
            request_data, endpoint, context
        )
        
        if not validation_result.allowed:
            return validation_result
        
        # If authentication is required
        if 'auth' in request_data:
            auth_result = await self.security_manager.authenticate_request(
                request_data['auth'], context
            )
            
            if not auth_result.allowed:
                return auth_result
            
            context.user = auth_result.user
        
        # Authorization check (if user is authenticated)
        if context.user:
            # Extract resource and action from endpoint
            resource, action = self._parse_endpoint(endpoint)
            auth_result = await self.security_manager.authorize_request(
                context.user, resource, action, context
            )
            
            if not auth_result.allowed:
                return auth_result
        
        return SecurityResult(allowed=True, user=context.user)
    
    def _parse_endpoint(self, endpoint: str) -> Tuple[str, str]:
        """Parse endpoint to extract resource and action"""
        # Simple parsing - in production, use more sophisticated routing
        parts = endpoint.strip('/').split('/')
        
        if len(parts) >= 2:
            resource = parts[1]  # e.g., 'calls', 'sessions'
            action = 'read'  # Default action
            
            # Determine action based on HTTP method or endpoint pattern
            if 'create' in endpoint or 'post' in endpoint.lower():
                action = 'create'
            elif 'update' in endpoint or 'put' in endpoint.lower():
                action = 'update'
            elif 'delete' in endpoint:
                action = 'delete'
            
            return resource, action
        
        return 'unknown', 'read'