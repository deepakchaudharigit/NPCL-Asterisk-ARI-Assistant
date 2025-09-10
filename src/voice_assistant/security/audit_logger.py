"""
Security Audit Logger
Logs all security-related events for compliance and monitoring
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)

class AuditEventType(Enum):
    """Types of audit events"""
    AUTH_ATTEMPT = "auth_attempt"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    AUTHORIZATION_SUCCESS = "authorization_success"
    AUTHORIZATION_FAILURE = "authorization_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SECURITY_THREAT = "security_threat"
    DATA_ACCESS = "data_access"
    VOICE_SESSION = "voice_session"
    IP_BLOCKED = "ip_blocked"
    SYSTEM_ERROR = "system_error"

@dataclass
class AuditEvent:
    """Audit event data structure"""
    event_type: AuditEventType
    timestamp: float
    ip_address: Optional[str] = None
    user_id: Optional[str] = None
    username: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    success: bool = True
    details: Dict[str, Any] = None
    session_id: Optional[str] = None
    user_agent: Optional[str] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

class AuditLogger:
    """Security audit logger with multiple output formats"""
    
    def __init__(self, log_file: Optional[str] = None, 
                 enable_console: bool = True,
                 enable_json_format: bool = True):
        self.log_file = log_file
        self.enable_console = enable_console
        self.enable_json_format = enable_json_format
        
        # Statistics tracking
        self.event_counts: Dict[str, int] = {}
        self.failed_auth_attempts: Dict[str, List[float]] = {}
        self.blocked_ips: set = set()
        
        # Setup file logging if specified
        if self.log_file:
            self.file_logger = self._setup_file_logger()
        else:
            self.file_logger = None
    
    def _setup_file_logger(self) -> logging.Logger:
        """Setup file logger for audit events"""
        file_logger = logging.getLogger('audit')
        file_logger.setLevel(logging.INFO)
        
        # Create file handler
        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(self.log_file)
        
        if self.enable_json_format:
            formatter = logging.Formatter('%(message)s')
        else:
            formatter = logging.Formatter(
                '%(asctime)s - AUDIT - %(levelname)s - %(message)s'
            )
        
        handler.setFormatter(formatter)
        file_logger.addHandler(handler)
        
        return file_logger
    
    async def log_event(self, event: AuditEvent):
        """Log an audit event"""
        try:
            # Update statistics
            event_type_str = event.event_type.value
            self.event_counts[event_type_str] = self.event_counts.get(event_type_str, 0) + 1
            
            # Track failed authentication attempts
            if event.event_type == AuditEventType.AUTH_FAILURE and event.ip_address:
                if event.ip_address not in self.failed_auth_attempts:
                    self.failed_auth_attempts[event.ip_address] = []
                self.failed_auth_attempts[event.ip_address].append(event.timestamp)
                
                # Clean old attempts (older than 1 hour)
                cutoff_time = event.timestamp - 3600
                self.failed_auth_attempts[event.ip_address] = [
                    t for t in self.failed_auth_attempts[event.ip_address] 
                    if t > cutoff_time
                ]
            
            # Format event for logging
            if self.enable_json_format:
                log_message = json.dumps(asdict(event), default=str)
            else:
                log_message = self._format_event_text(event)
            
            # Log to file
            if self.file_logger:
                self.file_logger.info(log_message)
            
            # Log to console
            if self.enable_console:
                logger.info(f"AUDIT: {log_message}")
                
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    def _format_event_text(self, event: AuditEvent) -> str:
        """Format event as human-readable text"""
        timestamp_str = datetime.fromtimestamp(event.timestamp).isoformat()
        
        base_info = f"[{timestamp_str}] {event.event_type.value.upper()}"
        
        if event.user_id:
            base_info += f" user={event.user_id}"
        if event.username:
            base_info += f" username={event.username}"
        if event.ip_address:
            base_info += f" ip={event.ip_address}"
        if event.resource:
            base_info += f" resource={event.resource}"
        if event.action:
            base_info += f" action={event.action}"
        
        base_info += f" success={event.success}"
        
        if event.details:
            details_str = json.dumps(event.details)
            base_info += f" details={details_str}"
        
        return base_info
    
    async def log_auth_attempt(self, ip_address: str, username: Optional[str], 
                              timestamp: float):
        """Log authentication attempt"""
        event = AuditEvent(
            event_type=AuditEventType.AUTH_ATTEMPT,
            timestamp=timestamp,
            ip_address=ip_address,
            username=username
        )
        await self.log_event(event)
    
    async def log_successful_auth(self, user_id: str, ip_address: str, 
                                 timestamp: float):
        """Log successful authentication"""
        event = AuditEvent(
            event_type=AuditEventType.AUTH_SUCCESS,
            timestamp=timestamp,
            ip_address=ip_address,
            user_id=user_id,
            success=True
        )
        await self.log_event(event)
    
    async def log_failed_auth(self, username: Optional[str], ip_address: str, 
                             timestamp: float):
        """Log failed authentication"""
        event = AuditEvent(
            event_type=AuditEventType.AUTH_FAILURE,
            timestamp=timestamp,
            ip_address=ip_address,
            username=username,
            success=False
        )
        await self.log_event(event)
    
    async def log_authorization_failure(self, user_id: str, resource: str, 
                                       action: str, ip_address: str):
        """Log authorization failure"""
        event = AuditEvent(
            event_type=AuditEventType.AUTHORIZATION_FAILURE,
            timestamp=time.time(),
            ip_address=ip_address,
            user_id=user_id,
            resource=resource,
            action=action,
            success=False
        )
        await self.log_event(event)
    
    async def log_successful_authorization(self, user_id: str, resource: str, 
                                          action: str, ip_address: str):
        """Log successful authorization"""
        event = AuditEvent(
            event_type=AuditEventType.AUTHORIZATION_SUCCESS,
            timestamp=time.time(),
            ip_address=ip_address,
            user_id=user_id,
            resource=resource,
            action=action,
            success=True
        )
        await self.log_event(event)
    
    async def log_security_event(self, event_type: str, ip_address: str, 
                                details: Dict[str, Any]):
        """Log general security event"""
        event = AuditEvent(
            event_type=AuditEventType.SECURITY_THREAT,
            timestamp=time.time(),
            ip_address=ip_address,
            details=details,
            success=False
        )
        await self.log_event(event)
    
    async def log_voice_session(self, user_id: str, ip_address: str, 
                               audio_size: int):
        """Log voice session activity"""
        event = AuditEvent(
            event_type=AuditEventType.VOICE_SESSION,
            timestamp=time.time(),
            ip_address=ip_address,
            user_id=user_id,
            details={'audio_size': audio_size},
            success=True
        )
        await self.log_event(event)
    
    async def log_data_access(self, user_id: str, resource: str, 
                             action: str, ip_address: str):
        """Log data access event"""
        event = AuditEvent(
            event_type=AuditEventType.DATA_ACCESS,
            timestamp=time.time(),
            ip_address=ip_address,
            user_id=user_id,
            resource=resource,
            action=action,
            success=True
        )
        await self.log_event(event)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get audit statistics"""
        current_time = time.time()
        
        # Calculate recent failed auth attempts (last hour)
        recent_failed_auths = 0
        for ip, attempts in self.failed_auth_attempts.items():
            recent_failed_auths += len([
                t for t in attempts 
                if current_time - t < 3600
            ])
        
        return {
            'total_events': sum(self.event_counts.values()),
            'event_counts': self.event_counts.copy(),
            'recent_failed_auths': recent_failed_auths,
            'unique_ips_with_failed_auths': len(self.failed_auth_attempts),
            'blocked_ips_count': len(self.blocked_ips),
            'timestamp': current_time
        }
    
    async def get_failed_auth_attempts(self, ip_address: str, 
                                      time_window: int = 3600) -> int:
        """Get number of failed auth attempts for IP in time window"""
        if ip_address not in self.failed_auth_attempts:
            return 0
        
        current_time = time.time()
        cutoff_time = current_time - time_window
        
        return len([
            t for t in self.failed_auth_attempts[ip_address]
            if t > cutoff_time
        ])
    
    async def cleanup_old_logs(self, max_age_hours: int = 24):
        """Clean up old audit data from memory"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        # Clean up failed auth attempts
        for ip in list(self.failed_auth_attempts.keys()):
            self.failed_auth_attempts[ip] = [
                t for t in self.failed_auth_attempts[ip]
                if t > cutoff_time
            ]
            
            # Remove empty entries
            if not self.failed_auth_attempts[ip]:
                del self.failed_auth_attempts[ip]
        
        logger.info(f"Cleaned up audit data older than {max_age_hours} hours")
    
    async def export_logs(self, start_time: float, end_time: float, 
                         output_file: str):
        """Export logs for a specific time range"""
        # This would typically read from the log file and filter by time
        # For now, we'll just log the request
        logger.info(f"Export requested: {start_time} to {end_time} -> {output_file}")
        
        # In production, implement actual log file parsing and export