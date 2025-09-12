"""
Production-optimized configuration settings for NPCL Asterisk ARI Voice Assistant.
Provides secure, scalable, and performance-tuned settings for production deployment.
"""

import os
from typing import Dict, Any, Optional, List
from enum import Enum

# Handle Pydantic v2 imports
try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic import BaseSettings
    except ImportError:
        raise ImportError("Either pydantic-settings or pydantic with BaseSettings is required. Install with: pip install pydantic-settings")

try:
    from pydantic import Field, field_validator
    # Pydantic v2
    PYDANTIC_V2 = True
except ImportError:
    from pydantic import Field, validator
    # Pydantic v1
    PYDANTIC_V2 = False

from .settings import VoiceAssistantSettings


class DeploymentEnvironment(str, Enum):
    """Deployment environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ProductionSettings(VoiceAssistantSettings):
    """Production-optimized settings"""
    
    # Environment Configuration
    environment: DeploymentEnvironment = Field(
        default=DeploymentEnvironment.PRODUCTION,
        env="ENVIRONMENT",
        description="Deployment environment"
    )
    
    # Security Settings
    enable_security_headers: bool = Field(
        default=True,
        env="ENABLE_SECURITY_HEADERS",
        description="Enable security headers in HTTP responses"
    )
    
    enable_rate_limiting: bool = Field(
        default=True,
        env="ENABLE_RATE_LIMITING",
        description="Enable API rate limiting"
    )
    
    rate_limit_calls_per_minute: int = Field(
        default=60,
        env="RATE_LIMIT_CALLS_PER_MINUTE",
        description="Maximum calls per minute per IP"
    )
    
    enable_request_logging: bool = Field(
        default=True,
        env="ENABLE_REQUEST_LOGGING",
        description="Enable detailed request logging"
    )
    
    # Performance Settings
    max_concurrent_calls: int = Field(
        default=100,
        env="MAX_CONCURRENT_CALLS",
        description="Maximum concurrent calls"
    )
    
    audio_processing_timeout: float = Field(
        default=5.0,
        env="AUDIO_PROCESSING_TIMEOUT",
        description="Audio processing timeout in seconds"
    )
    
    ai_response_timeout: float = Field(
        default=10.0,
        env="AI_RESPONSE_TIMEOUT",
        description="AI response timeout in seconds"
    )
    
    connection_pool_size: int = Field(
        default=20,
        env="CONNECTION_POOL_SIZE",
        description="HTTP connection pool size"
    )
    
    # Audio Quality Settings
    audio_quality_mode: str = Field(
        default="high",
        env="AUDIO_QUALITY_MODE",
        description="Audio quality mode: low, medium, high"
    )
    
    enable_noise_reduction: bool = Field(
        default=True,
        env="ENABLE_NOISE_REDUCTION",
        description="Enable audio noise reduction"
    )
    
    enable_echo_cancellation: bool = Field(
        default=True,
        env="ENABLE_ECHO_CANCELLATION",
        description="Enable echo cancellation"
    )
    
    # Monitoring and Observability
    enable_metrics: bool = Field(
        default=True,
        env="ENABLE_METRICS",
        description="Enable metrics collection"
    )
    
    metrics_port: int = Field(
        default=9090,
        env="METRICS_PORT",
        description="Metrics server port"
    )
    
    enable_health_checks: bool = Field(
        default=True,
        env="ENABLE_HEALTH_CHECKS",
        description="Enable health check endpoints"
    )
    
    health_check_interval: int = Field(
        default=30,
        env="HEALTH_CHECK_INTERVAL",
        description="Health check interval in seconds"
    )
    
    # Logging Configuration
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        env="LOG_LEVEL",
        description="Application log level"
    )
    
    log_format: str = Field(
        default="json",
        env="LOG_FORMAT",
        description="Log format: json, text"
    )
    
    enable_structured_logging: bool = Field(
        default=True,
        env="ENABLE_STRUCTURED_LOGGING",
        description="Enable structured logging"
    )
    
    log_file_path: Optional[str] = Field(
        default="/var/log/voice-assistant/app.log",
        env="LOG_FILE_PATH",
        description="Log file path"
    )
    
    log_rotation_size: str = Field(
        default="100MB",
        env="LOG_ROTATION_SIZE",
        description="Log rotation size"
    )
    
    log_retention_days: int = Field(
        default=30,
        env="LOG_RETENTION_DAYS",
        description="Log retention in days"
    )
    
    # Database Configuration
    enable_database: bool = Field(
        default=True,
        env="ENABLE_DATABASE",
        description="Enable database for session storage"
    )
    
    database_url: Optional[str] = Field(
        default=None,
        env="DATABASE_URL",
        description="Database connection URL"
    )
    
    database_pool_size: int = Field(
        default=20,
        env="DATABASE_POOL_SIZE",
        description="Database connection pool size"
    )
    
    # Redis Configuration
    enable_redis: bool = Field(
        default=True,
        env="ENABLE_REDIS",
        description="Enable Redis for caching"
    )
    
    redis_url: Optional[str] = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL",
        description="Redis connection URL"
    )
    
    redis_pool_size: int = Field(
        default=10,
        env="REDIS_POOL_SIZE",
        description="Redis connection pool size"
    )
    
    # Backup and Recovery
    enable_call_recording_backup: bool = Field(
        default=True,
        env="ENABLE_CALL_RECORDING_BACKUP",
        description="Enable call recording backup"
    )
    
    backup_storage_path: str = Field(
        default="/var/backups/voice-assistant",
        env="BACKUP_STORAGE_PATH",
        description="Backup storage path"
    )
    
    backup_retention_days: int = Field(
        default=90,
        env="BACKUP_RETENTION_DAYS",
        description="Backup retention in days"
    )
    
    # Alerting Configuration
    enable_alerting: bool = Field(
        default=True,
        env="ENABLE_ALERTING",
        description="Enable alerting system"
    )
    
    alert_webhook_url: Optional[str] = Field(
        default=None,
        env="ALERT_WEBHOOK_URL",
        description="Webhook URL for alerts"
    )
    
    alert_email_recipients: List[str] = Field(
        default_factory=list,
        env="ALERT_EMAIL_RECIPIENTS",
        description="Email recipients for alerts"
    )
    
    # Performance Thresholds
    cpu_usage_alert_threshold: float = Field(
        default=80.0,
        env="CPU_USAGE_ALERT_THRESHOLD",
        description="CPU usage alert threshold percentage"
    )
    
    memory_usage_alert_threshold: float = Field(
        default=85.0,
        env="MEMORY_USAGE_ALERT_THRESHOLD",
        description="Memory usage alert threshold percentage"
    )
    
    error_rate_alert_threshold: float = Field(
        default=5.0,
        env="ERROR_RATE_ALERT_THRESHOLD",
        description="Error rate alert threshold percentage"
    )
    
    response_time_alert_threshold: float = Field(
        default=2.0,
        env="RESPONSE_TIME_ALERT_THRESHOLD",
        description="Response time alert threshold in seconds"
    )
    
    # Validators - compatible with both Pydantic v1 and v2
    if PYDANTIC_V2:
        @field_validator("environment")
        @classmethod
        def validate_environment(cls, v):
            """Validate environment setting"""
            if v == DeploymentEnvironment.PRODUCTION:
                # Additional production validations can be added here
                pass
            return v
        
        @field_validator("max_concurrent_calls")
        @classmethod
        def validate_concurrent_calls(cls, v):
            """Validate concurrent calls limit"""
            if v < 1:
                raise ValueError("max_concurrent_calls must be at least 1")
            if v > 1000:
                raise ValueError("max_concurrent_calls should not exceed 1000")
            return v
        
        @field_validator("audio_processing_timeout", "ai_response_timeout")
        @classmethod
        def validate_timeouts(cls, v):
            """Validate timeout values"""
            if v <= 0:
                raise ValueError("Timeout values must be positive")
            if v > 60:
                raise ValueError("Timeout values should not exceed 60 seconds")
            return v
        
        @field_validator("rate_limit_calls_per_minute")
        @classmethod
        def validate_rate_limit(cls, v):
            """Validate rate limit"""
            if v < 1:
                raise ValueError("rate_limit_calls_per_minute must be at least 1")
            return v
    else:
        @validator("environment")
        def validate_environment(cls, v):
            """Validate environment setting"""
            if v == DeploymentEnvironment.PRODUCTION:
                # Additional production validations can be added here
                pass
            return v
        
        @validator("max_concurrent_calls")
        def validate_concurrent_calls(cls, v):
            """Validate concurrent calls limit"""
            if v < 1:
                raise ValueError("max_concurrent_calls must be at least 1")
            if v > 1000:
                raise ValueError("max_concurrent_calls should not exceed 1000")
            return v
        
        @validator("audio_processing_timeout", "ai_response_timeout")
        def validate_timeouts(cls, v):
            """Validate timeout values"""
            if v <= 0:
                raise ValueError("Timeout values must be positive")
            if v > 60:
                raise ValueError("Timeout values should not exceed 60 seconds")
            return v
        
        @validator("rate_limit_calls_per_minute")
        def validate_rate_limit(cls, v):
            """Validate rate limit"""
            if v < 1:
                raise ValueError("rate_limit_calls_per_minute must be at least 1")
            return v
    
    def get_optimized_audio_config(self) -> Dict[str, Any]:
        """Get optimized audio configuration for production"""
        quality_configs = {
            "low": {
                "sample_rate": 8000,
                "chunk_size": 160,
                "buffer_size": 800,
                "compression": True
            },
            "medium": {
                "sample_rate": 16000,
                "chunk_size": 320,
                "buffer_size": 1600,
                "compression": False
            },
            "high": {
                "sample_rate": 24000,
                "chunk_size": 480,
                "buffer_size": 2400,
                "compression": False
            }
        }
        
        base_config = quality_configs.get(self.audio_quality_mode, quality_configs["medium"])
        
        # Add production-specific settings
        base_config.update({
            "enable_noise_reduction": self.enable_noise_reduction,
            "enable_echo_cancellation": self.enable_echo_cancellation,
            "processing_timeout": self.audio_processing_timeout
        })
        
        return base_config
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration"""
        return {
            "enable_security_headers": self.enable_security_headers,
            "enable_rate_limiting": self.enable_rate_limiting,
            "rate_limit_calls_per_minute": self.rate_limit_calls_per_minute,
            "enable_request_logging": self.enable_request_logging,
            "cors_origins": ["https://*.npcl.com", "https://localhost:3000"] if self.environment == DeploymentEnvironment.PRODUCTION else ["*"],
            "allowed_hosts": ["*.npcl.com", "localhost"] if self.environment == DeploymentEnvironment.PRODUCTION else ["*"]
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return {
            "enable_metrics": self.enable_metrics,
            "metrics_port": self.metrics_port,
            "enable_health_checks": self.enable_health_checks,
            "health_check_interval": self.health_check_interval,
            "performance_thresholds": {
                "cpu_usage": self.cpu_usage_alert_threshold,
                "memory_usage": self.memory_usage_alert_threshold,
                "error_rate": self.error_rate_alert_threshold,
                "response_time": self.response_time_alert_threshold
            }
        }
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return {
            "level": self.log_level.value,
            "format": self.log_format,
            "structured": self.enable_structured_logging,
            "file_path": self.log_file_path,
            "rotation_size": self.log_rotation_size,
            "retention_days": self.log_retention_days,
            "handlers": {
                "console": True,
                "file": self.log_file_path is not None,
                "syslog": self.environment == DeploymentEnvironment.PRODUCTION
            }
        }
    
    # Configuration - compatible with both Pydantic v1 and v2
    if PYDANTIC_V2:
        model_config = {
            "env_file": ".env.production",
            "env_file_encoding": "utf-8",
            "case_sensitive": False,
            "extra": "ignore"
        }
    else:
        class Config:
            env_file = ".env.production"
            env_file_encoding = "utf-8"
            case_sensitive = False


def get_production_settings() -> ProductionSettings:
    """Get production settings instance"""
    return ProductionSettings()


# Environment-specific configurations
ENVIRONMENT_CONFIGS = {
    DeploymentEnvironment.DEVELOPMENT: {
        "log_level": LogLevel.DEBUG,
        "enable_metrics": False,
        "enable_security_headers": False,
        "enable_rate_limiting": False,
        "max_concurrent_calls": 10,
        "audio_quality_mode": "medium"
    },
    
    DeploymentEnvironment.STAGING: {
        "log_level": LogLevel.INFO,
        "enable_metrics": True,
        "enable_security_headers": True,
        "enable_rate_limiting": True,
        "max_concurrent_calls": 50,
        "audio_quality_mode": "high"
    },
    
    DeploymentEnvironment.PRODUCTION: {
        "log_level": LogLevel.WARNING,
        "enable_metrics": True,
        "enable_security_headers": True,
        "enable_rate_limiting": True,
        "max_concurrent_calls": 100,
        "audio_quality_mode": "high"
    },
    
    DeploymentEnvironment.TESTING: {
        "log_level": LogLevel.ERROR,
        "enable_metrics": False,
        "enable_security_headers": False,
        "enable_rate_limiting": False,
        "max_concurrent_calls": 5,
        "audio_quality_mode": "low"
    }
}


def get_environment_config(environment: DeploymentEnvironment) -> Dict[str, Any]:
    """Get configuration for specific environment"""
    return ENVIRONMENT_CONFIGS.get(environment, ENVIRONMENT_CONFIGS[DeploymentEnvironment.PRODUCTION])