"""
Input Validation and Sanitization
Provides comprehensive input validation and security checks
"""

import re
import html
import json
import base64
import hashlib
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass
from enum import Enum
import bleach
import validators
import logging

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom validation error"""
    pass

class SecurityThreat(Enum):
    """Types of security threats"""
    XSS = "xss"
    SQL_INJECTION = "sql_injection"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    SCRIPT_INJECTION = "script_injection"
    MALICIOUS_FILE = "malicious_file"
    SUSPICIOUS_PATTERN = "suspicious_pattern"

@dataclass
class ValidationRule:
    """Validation rule configuration"""
    name: str
    validator: Callable[[Any], bool]
    error_message: str
    required: bool = True

@dataclass
class ValidationResult:
    """Result of input validation"""
    is_valid: bool
    sanitized_value: Any = None
    errors: List[str] = None
    threats: List[SecurityThreat] = None
    confidence: float = 1.0

class InputValidator:
    """Base input validator with common validation methods"""
    
    def __init__(self):
        self.patterns = {
            'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
            'phone': re.compile(r'^\+?1?-?\.?\s?\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})$'),
            'alphanumeric': re.compile(r'^[a-zA-Z0-9]+$'),
            'username': re.compile(r'^[a-zA-Z0-9_-]{3,20}$'),
            'safe_string': re.compile(r'^[a-zA-Z0-9\s\-_.,!?]+$'),
            'uuid': re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'),
            'ip_address': re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
        }
        
        # Security patterns to detect threats
        self.threat_patterns = {
            SecurityThreat.XSS: [
                re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
                re.compile(r'javascript:', re.IGNORECASE),
                re.compile(r'on\w+\s*=', re.IGNORECASE),
                re.compile(r'<iframe[^>]*>', re.IGNORECASE),
                re.compile(r'<object[^>]*>', re.IGNORECASE),
                re.compile(r'<embed[^>]*>', re.IGNORECASE)
            ],
            SecurityThreat.SQL_INJECTION: [
                re.compile(r'(\bUNION\b|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b)', re.IGNORECASE),
                re.compile(r'(\bOR\b|\bAND\b)\s+\d+\s*=\s*\d+', re.IGNORECASE),
                re.compile(r"'.*?(\bOR\b|\bAND\b).*?'", re.IGNORECASE),
                re.compile(r'--\s*$', re.MULTILINE),
                re.compile(r'/\*.*?\*/', re.DOTALL)
            ],
            SecurityThreat.COMMAND_INJECTION: [
                re.compile(r'[;&|`$(){}[\]<>]'),
                re.compile(r'\b(cat|ls|pwd|whoami|id|uname|ps|netstat|ifconfig)\b'),
                re.compile(r'\.\./')
            ],
            SecurityThreat.PATH_TRAVERSAL: [
                re.compile(r'\.\.[\\/]'),
                re.compile(r'[\\/]\.\.[\\/]'),
                re.compile(r'^[\\/]'),
                re.compile(r'~[\\/]')
            ]
        }
    
    def validate_string(self, value: str, min_length: int = 0, 
                       max_length: int = 1000, pattern: str = None,
                       allow_html: bool = False) -> ValidationResult:
        """Validate string input"""
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                errors=["Value must be a string"]
            )
        
        errors = []
        threats = []
        
        # Length validation
        if len(value) < min_length:
            errors.append(f"String too short (minimum {min_length} characters)")
        
        if len(value) > max_length:
            errors.append(f"String too long (maximum {max_length} characters)")
        
        # Pattern validation
        if pattern and pattern in self.patterns:
            if not self.patterns[pattern].match(value):
                errors.append(f"String does not match required pattern: {pattern}")
        
        # Security threat detection
        detected_threats = self._detect_threats(value)
        threats.extend(detected_threats)
        
        # Sanitization
        sanitized_value = value
        if not allow_html:
            sanitized_value = html.escape(value)
            sanitized_value = bleach.clean(sanitized_value, tags=[], strip=True)
        
        is_valid = len(errors) == 0 and len(threats) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            sanitized_value=sanitized_value,
            errors=errors,
            threats=threats
        )
    
    def validate_email(self, email: str) -> ValidationResult:
        """Validate email address"""
        if not validators.email(email):
            return ValidationResult(
                is_valid=False,
                errors=["Invalid email format"]
            )
        
        return ValidationResult(
            is_valid=True,
            sanitized_value=email.lower().strip()
        )
    
    def validate_url(self, url: str, allowed_schemes: List[str] = None) -> ValidationResult:
        """Validate URL"""
        allowed_schemes = allowed_schemes or ['http', 'https']
        
        if not validators.url(url):
            return ValidationResult(
                is_valid=False,
                errors=["Invalid URL format"]
            )
        
        # Check scheme
        scheme = url.split('://')[0].lower()
        if scheme not in allowed_schemes:
            return ValidationResult(
                is_valid=False,
                errors=[f"URL scheme '{scheme}' not allowed"]
            )
        
        return ValidationResult(
            is_valid=True,
            sanitized_value=url
        )
    
    def validate_json(self, json_str: str, max_size: int = 10000) -> ValidationResult:
        """Validate JSON string"""
        if len(json_str) > max_size:
            return ValidationResult(
                is_valid=False,
                errors=[f"JSON too large (maximum {max_size} characters)"]
            )
        
        try:
            parsed = json.loads(json_str)
            return ValidationResult(
                is_valid=True,
                sanitized_value=parsed
            )
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Invalid JSON: {str(e)}"]
            )
    
    def validate_file_upload(self, filename: str, content: bytes,
                           allowed_extensions: List[str] = None,
                           max_size: int = 10 * 1024 * 1024) -> ValidationResult:
        """Validate file upload"""
        errors = []
        threats = []
        
        # Size validation
        if len(content) > max_size:
            errors.append(f"File too large (maximum {max_size} bytes)")
        
        # Extension validation
        if allowed_extensions:
            ext = filename.split('.')[-1].lower() if '.' in filename else ''
            if ext not in allowed_extensions:
                errors.append(f"File extension '{ext}' not allowed")
        
        # Filename validation
        if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
            errors.append("Filename contains invalid characters")
        
        # Content validation
        if self._is_malicious_file(content):
            threats.append(SecurityThreat.MALICIOUS_FILE)
        
        is_valid = len(errors) == 0 and len(threats) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            sanitized_value=filename,
            errors=errors,
            threats=threats
        )
    
    def validate_audio_data(self, audio_data: bytes, 
                           max_size: int = 50 * 1024 * 1024) -> ValidationResult:
        """Validate audio data for voice assistant"""
        errors = []
        
        # Size validation
        if len(audio_data) > max_size:
            errors.append(f"Audio data too large (maximum {max_size} bytes)")
        
        # Basic format validation (check for common audio headers)
        audio_headers = [
            b'RIFF',  # WAV
            b'ID3',   # MP3
            b'OggS',  # OGG
            b'fLaC',  # FLAC
        ]
        
        has_valid_header = any(audio_data.startswith(header) for header in audio_headers)
        if not has_valid_header and len(audio_data) > 100:
            # For raw PCM data, we can't check headers, so we allow it
            pass
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            sanitized_value=audio_data,
            errors=errors
        )
    
    def _detect_threats(self, value: str) -> List[SecurityThreat]:
        """Detect security threats in input"""
        threats = []
        
        for threat_type, patterns in self.threat_patterns.items():
            for pattern in patterns:
                if pattern.search(value):
                    threats.append(threat_type)
                    break
        
        return threats
    
    def _is_malicious_file(self, content: bytes) -> bool:
        """Check if file content appears malicious"""
        # Check for executable signatures
        malicious_signatures = [
            b'MZ',      # Windows PE
            b'\x7fELF', # Linux ELF
            b'#!/bin/', # Shell script
            b'<script', # HTML with script
            b'<?php',   # PHP script
        ]
        
        return any(content.startswith(sig) for sig in malicious_signatures)

class SecurityValidator(InputValidator):
    """Enhanced validator with advanced security features"""
    
    def __init__(self):
        super().__init__()
        self.reputation_db = {}  # IP/domain reputation
        self.threat_intelligence = {}  # Known threat indicators
    
    def validate_with_context(self, value: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate input with additional context"""
        # Get user context
        user_id = context.get('user_id')
        ip_address = context.get('ip_address')
        user_agent = context.get('user_agent')
        
        # Basic validation
        if isinstance(value, str):
            result = self.validate_string(value)
        else:
            result = ValidationResult(is_valid=True, sanitized_value=value)
        
        # Enhanced security checks
        if ip_address:
            ip_reputation = self._check_ip_reputation(ip_address)
            if ip_reputation < 0.5:  # Low reputation
                result.threats = result.threats or []
                result.threats.append(SecurityThreat.SUSPICIOUS_PATTERN)
                result.confidence *= ip_reputation
        
        # User behavior analysis
        if user_id:
            behavior_score = self._analyze_user_behavior(user_id, value)
            result.confidence *= behavior_score
        
        return result
    
    def validate_api_request(self, request_data: Dict[str, Any],
                           endpoint: str) -> ValidationResult:
        """Validate API request data"""
        errors = []
        threats = []
        sanitized_data = {}
        
        # Validate each field based on endpoint requirements
        validation_rules = self._get_validation_rules(endpoint)
        
        for field, rules in validation_rules.items():
            if field in request_data:
                value = request_data[field]
                field_result = self._validate_field(value, rules)
                
                if not field_result.is_valid:
                    errors.extend(field_result.errors or [])
                    threats.extend(field_result.threats or [])
                else:
                    sanitized_data[field] = field_result.sanitized_value
            elif any(rule.required for rule in rules):
                errors.append(f"Required field '{field}' is missing")
        
        return ValidationResult(
            is_valid=len(errors) == 0 and len(threats) == 0,
            sanitized_value=sanitized_data,
            errors=errors,
            threats=threats
        )
    
    def _check_ip_reputation(self, ip_address: str) -> float:
        """Check IP address reputation (0.0 = bad, 1.0 = good)"""
        # In production, this would query threat intelligence APIs
        if ip_address in self.reputation_db:
            return self.reputation_db[ip_address]
        
        # Default reputation for unknown IPs
        return 0.8
    
    def _analyze_user_behavior(self, user_id: str, input_value: Any) -> float:
        """Analyze user behavior patterns (0.0 = suspicious, 1.0 = normal)"""
        # In production, this would analyze:
        # - Request frequency
        # - Input patterns
        # - Geographic location
        # - Device fingerprinting
        
        return 1.0  # Default to normal behavior
    
    def _get_validation_rules(self, endpoint: str) -> Dict[str, List[ValidationRule]]:
        """Get validation rules for specific endpoint"""
        rules = {
            '/api/calls': {
                'phone_number': [
                    ValidationRule('phone_format', lambda x: self.patterns['phone'].match(x), 'Invalid phone number format')
                ],
                'message': [
                    ValidationRule('max_length', lambda x: len(x) <= 1000, 'Message too long'),
                    ValidationRule('safe_content', lambda x: not self._detect_threats(x), 'Message contains unsafe content')
                ]
            },
            '/api/sessions': {
                'session_id': [
                    ValidationRule('uuid_format', lambda x: self.patterns['uuid'].match(x), 'Invalid session ID format')
                ],
                'audio_data': [
                    ValidationRule('audio_size', lambda x: len(x) <= 10*1024*1024, 'Audio data too large')
                ]
            }
        }
        
        return rules.get(endpoint, {})
    
    def _validate_field(self, value: Any, rules: List[ValidationRule]) -> ValidationResult:
        """Validate a single field against rules"""
        errors = []
        
        for rule in rules:
            try:
                if not rule.validator(value):
                    errors.append(rule.error_message)
            except Exception as e:
                errors.append(f"Validation error for {rule.name}: {str(e)}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            sanitized_value=value,
            errors=errors
        )

class ContentFilter:
    """Content filtering for inappropriate or harmful content"""
    
    def __init__(self):
        self.profanity_list = set([
            # Add profanity words here
            'badword1', 'badword2'
        ])
        
        self.sensitive_patterns = [
            re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),  # Credit card
            re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),  # SSN
            re.compile(r'\b[A-Z]{2}\d{6,8}\b'),    # Passport
        ]
    
    def filter_content(self, text: str) -> ValidationResult:
        """Filter content for inappropriate material"""
        threats = []
        sanitized_text = text
        
        # Check for profanity
        words = text.lower().split()
        if any(word in self.profanity_list for word in words):
            threats.append(SecurityThreat.SUSPICIOUS_PATTERN)
            # Replace profanity with asterisks
            for word in words:
                if word in self.profanity_list:
                    sanitized_text = sanitized_text.replace(word, '*' * len(word))
        
        # Check for sensitive information
        for pattern in self.sensitive_patterns:
            if pattern.search(text):
                threats.append(SecurityThreat.SUSPICIOUS_PATTERN)
                # Redact sensitive information
                sanitized_text = pattern.sub('[REDACTED]', sanitized_text)
        
        return ValidationResult(
            is_valid=len(threats) == 0,
            sanitized_value=sanitized_text,
            threats=threats
        )