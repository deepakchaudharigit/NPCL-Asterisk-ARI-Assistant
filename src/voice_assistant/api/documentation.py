"""
Comprehensive API documentation system with OpenAPI/Swagger integration.
Provides automatic documentation generation for all FastAPI endpoints.
"""

from typing import Dict, Any, List, Optional
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import HTMLResponse
import json

from ..utils.dependency_manager import safe_import
from config.settings import get_settings

# Optional imports
pydantic = safe_import("pydantic", "pydantic", required=True)


def create_custom_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """Create comprehensive OpenAPI schema with NPCL-specific documentation"""
    
    if app.openapi_schema:
        return app.openapi_schema
    
    settings = get_settings()
    
    openapi_schema = get_openapi(
        title="NPCL Asterisk ARI Voice Assistant API",
        version="2.0.0",
        description="""
# NPCL Asterisk ARI Voice Assistant API

## Overview

The NPCL (Noida Power Corporation Limited) Asterisk ARI Voice Assistant is a comprehensive 
telephony-integrated AI system that provides intelligent customer service through voice 
interactions. This API provides endpoints for managing calls, monitoring system health, 
and integrating with external systems.

## Key Features

- **Real-time Voice Processing**: Low-latency audio processing with Gemini 1.5 Flash
- **Asterisk ARI Integration**: Complete telephony integration with bidirectional audio
- **Session Management**: Comprehensive call session tracking and management
- **Performance Monitoring**: Real-time system health and performance metrics
- **Security**: Enterprise-grade security with authentication and rate limiting

## Architecture

```
[Phone Caller] → [Asterisk PBX] → [FastAPI Server] → [Gemini 1.5 Flash]
                       ↓              ↓                ↓
                 [Audio Files] ← [TTS Engine] ← [AI Response]
                       ↓
              [External Media WebSocket] ← [Gemini Live API]
```

## Authentication

Most endpoints require authentication. Include your API key in the header:

```
Authorization: Bearer YOUR_API_KEY
```

## Rate Limiting

API calls are rate-limited to prevent abuse:
- **Standard endpoints**: 100 requests per minute
- **Call endpoints**: 60 requests per minute
- **Health endpoints**: 200 requests per minute

## Error Handling

All endpoints return standardized error responses:

```json
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human readable error message",
        "details": {
            "field": "Additional error details"
        }
    }
}
```

## WebSocket Endpoints

Real-time communication is available through WebSocket endpoints:
- `/ws/external_media/{channel_id}` - Bidirectional audio streaming
- `/ws/events` - Real-time system events
- `/ws/metrics` - Live performance metrics

## NPCL-Specific Features

This system is specifically designed for NPCL customer service:
- Power connection inquiries
- Complaint registration and tracking
- Billing information
- Service status updates
- Emergency reporting

## Support

For technical support, contact the NPCL IT team or refer to the deployment documentation.
        """,
        routes=app.routes,
        servers=[
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            },
            {
                "url": "https://voice-assistant.npcl.com",
                "description": "Production server"
            },
            {
                "url": "https://staging-voice-assistant.npcl.com", 
                "description": "Staging server"
            }
        ],
        contact={
            "name": "NPCL IT Support",
            "email": "it-support@npcl.com",
            "url": "https://npcl.com/support"
        },
        license_info={
            "name": "NPCL Internal Use",
            "url": "https://npcl.com/license"
        }
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token for API authentication"
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for service authentication"
        }
    }
    
    # Add global security requirement
    openapi_schema["security"] = [
        {"BearerAuth": []},
        {"ApiKeyAuth": []}
    ]
    
    # Add custom tags for better organization
    openapi_schema["tags"] = [
        {
            "name": "Call Management",
            "description": "Endpoints for managing voice calls and sessions"
        },
        {
            "name": "Audio Processing", 
            "description": "Audio processing and voice activity detection"
        },
        {
            "name": "AI Integration",
            "description": "Gemini AI integration and response generation"
        },
        {
            "name": "System Health",
            "description": "Health checks and system monitoring"
        },
        {
            "name": "Metrics",
            "description": "Performance metrics and analytics"
        },
        {
            "name": "Configuration",
            "description": "System configuration and settings"
        },
        {
            "name": "WebSocket",
            "description": "Real-time WebSocket endpoints"
        }
    ]
    
    # Add custom response schemas
    openapi_schema["components"]["schemas"].update({
        "CallInfo": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "Unique channel identifier"},
                "session_id": {"type": "string", "description": "Session identifier"},
                "caller_number": {"type": "string", "description": "Caller phone number"},
                "called_number": {"type": "string", "description": "Called phone number"},
                "start_time": {"type": "number", "description": "Call start timestamp"},
                "duration": {"type": "number", "description": "Call duration in seconds"},
                "state": {"type": "string", "enum": ["initializing", "ringing", "answered", "active", "ended"]},
                "metadata": {"type": "object", "description": "Additional call metadata"}
            },
            "required": ["channel_id", "state"]
        },
        "HealthStatus": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["healthy", "degraded", "unhealthy"]},
                "last_check": {"type": "string", "format": "date-time"},
                "checks": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "critical": {"type": "boolean"}
                        }
                    }
                }
            }
        },
        "SystemMetrics": {
            "type": "object",
            "properties": {
                "cpu_usage": {"type": "number", "description": "CPU usage percentage"},
                "memory_usage": {"type": "number", "description": "Memory usage percentage"},
                "active_calls": {"type": "integer", "description": "Number of active calls"},
                "total_calls": {"type": "integer", "description": "Total calls processed"},
                "error_rate": {"type": "number", "description": "Error rate percentage"}
            }
        },
        "ErrorResponse": {
            "type": "object",
            "properties": {
                "error": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Error code"},
                        "message": {"type": "string", "description": "Error message"},
                        "details": {"type": "object", "description": "Additional error details"}
                    },
                    "required": ["code", "message"]
                }
            }
        }
    })
    
    # Add example responses
    openapi_schema["components"]["examples"] = {
        "CallInfoExample": {
            "summary": "Active call information",
            "value": {
                "channel_id": "SIP/1234-00000001",
                "session_id": "sess_abc123",
                "caller_number": "+91-9876543210",
                "called_number": "1000",
                "start_time": 1704110400.0,
                "duration": 45.5,
                "state": "active",
                "metadata": {
                    "is_talking": False,
                    "audio_quality": "high"
                }
            }
        },
        "HealthStatusExample": {
            "summary": "System health status",
            "value": {
                "status": "healthy",
                "last_check": "2024-01-01T12:00:00Z",
                "checks": {
                    "cpu_usage": {
                        "description": "CPU usage below 90%",
                        "critical": True
                    },
                    "memory_usage": {
                        "description": "Memory usage below 90%", 
                        "critical": True
                    }
                }
            }
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def add_api_documentation(app: FastAPI):
    """Add comprehensive API documentation to FastAPI app"""
    
    # Set custom OpenAPI schema
    app.openapi = lambda: create_custom_openapi_schema(app)
    
    # Custom documentation endpoints
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        """Custom Swagger UI with NPCL branding"""
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title="NPCL Voice Assistant API Documentation",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
            swagger_favicon_url="https://npcl.com/favicon.ico"
        )
    
    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        """ReDoc documentation"""
        return get_redoc_html(
            openapi_url="/openapi.json",
            title="NPCL Voice Assistant API Documentation",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js",
            redoc_favicon_url="https://npcl.com/favicon.ico"
        )
    
    @app.get("/api-guide", response_class=HTMLResponse, include_in_schema=False)
    async def api_guide():
        """Comprehensive API guide"""
        return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <title>NPCL Voice Assistant API Guide</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        .header { background: #2c3e50; color: white; padding: 20px; margin: -40px -40px 40px -40px; }
        .section { margin: 30px 0; }
        .code { background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }
        .endpoint { background: #e8f5e8; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .method { font-weight: bold; color: #2980b9; }
        .url { font-family: monospace; background: #ecf0f1; padding: 2px 5px; }
        .example { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>NPCL Voice Assistant API Guide</h1>
        <p>Comprehensive guide for integrating with the NPCL Asterisk ARI Voice Assistant</p>
    </div>

    <div class="section">
        <h2>Quick Start</h2>
        <p>Get started with the NPCL Voice Assistant API in minutes:</p>
        
        <div class="code">
# 1. Get your API key from NPCL IT team
API_KEY="your-api-key-here"

# 2. Test the connection
curl -H "Authorization: Bearer $API_KEY" \\
     https://voice-assistant.npcl.com/health

# 3. Start monitoring calls
curl -H "Authorization: Bearer $API_KEY" \\
     https://voice-assistant.npcl.com/calls
        </div>
    </div>

    <div class="section">
        <h2>Core Endpoints</h2>
        
        <div class="endpoint">
            <div class="method">GET</div> <span class="url">/health</span>
            <p>Check system health status</p>
        </div>
        
        <div class="endpoint">
            <div class="method">GET</div> <span class="url">/calls</span>
            <p>List all active calls</p>
        </div>
        
        <div class="endpoint">
            <div class="method">GET</div> <span class="url">/calls/{channel_id}</span>
            <p>Get detailed information about a specific call</p>
        </div>
        
        <div class="endpoint">
            <div class="method">POST</div> <span class="url">/ari/events</span>
            <p>Handle incoming ARI events from Asterisk</p>
        </div>
        
        <div class="endpoint">
            <div class="method">GET</div> <span class="url">/metrics</span>
            <p>Get system performance metrics</p>
        </div>
    </div>

    <div class="section">
        <h2>WebSocket Integration</h2>
        <p>Real-time communication through WebSocket endpoints:</p>
        
        <div class="code">
// Connect to external media WebSocket
const ws = new WebSocket('wss://voice-assistant.npcl.com/ws/external_media/channel_id');

// Handle audio data
ws.onmessage = function(event) {
    const audioData = event.data;
    // Process audio data
};

// Send audio data
ws.send(audioBuffer);
        </div>
    </div>

    <div class="section">
        <h2>Authentication</h2>
        <p>All API requests require authentication using Bearer tokens:</p>
        
        <div class="example">
            <strong>Header:</strong> <code>Authorization: Bearer YOUR_JWT_TOKEN</code><br>
            <strong>Alternative:</strong> <code>X-API-Key: YOUR_API_KEY</code>
        </div>
    </div>

    <div class="section">
        <h2>Error Handling</h2>
        <p>All errors follow a consistent format:</p>
        
        <div class="code">
{
    "error": {
        "code": "INVALID_CHANNEL",
        "message": "Channel not found",
        "details": {
            "channel_id": "SIP/1234-00000001"
        }
    }
}
        </div>
    </div>

    <div class="section">
        <h2>Rate Limits</h2>
        <ul>
            <li><strong>Standard endpoints:</strong> 100 requests/minute</li>
            <li><strong>Call endpoints:</strong> 60 requests/minute</li>
            <li><strong>Health endpoints:</strong> 200 requests/minute</li>
        </ul>
    </div>

    <div class="section">
        <h2>Support</h2>
        <p>For technical support:</p>
        <ul>
            <li><strong>Email:</strong> it-support@npcl.com</li>
            <li><strong>Documentation:</strong> <a href="/docs">Swagger UI</a> | <a href="/redoc">ReDoc</a></li>
            <li><strong>Status Page:</strong> <a href="/health">System Health</a></li>
        </ul>
    </div>
</body>
</html>
        """)
    
    @app.get("/openapi.json", include_in_schema=False)
    async def get_openapi_json():
        """Get OpenAPI JSON schema"""
        return app.openapi()


def create_configuration_documentation() -> Dict[str, Any]:
    """Create comprehensive configuration documentation"""
    
    return {
        "title": "NPCL Voice Assistant Configuration Guide",
        "version": "2.0.0",
        "sections": {
            "environment_variables": {
                "title": "Environment Variables",
                "description": "Complete list of environment variables for configuration",
                "variables": {
                    "GOOGLE_API_KEY": {
                        "required": True,
                        "description": "Google AI Studio API key for Gemini access",
                        "example": "AIzaSyD...",
                        "security": "sensitive"
                    },
                    "ARI_BASE_URL": {
                        "required": True,
                        "description": "Asterisk ARI endpoint URL",
                        "example": "http://localhost:8088/ari",
                        "default": "http://localhost:8088/ari"
                    },
                    "ARI_USERNAME": {
                        "required": True,
                        "description": "ARI authentication username",
                        "example": "asterisk",
                        "default": "asterisk"
                    },
                    "ARI_PASSWORD": {
                        "required": True,
                        "description": "ARI authentication password",
                        "example": "1234",
                        "security": "sensitive"
                    },
                    "ENVIRONMENT": {
                        "required": False,
                        "description": "Deployment environment",
                        "example": "production",
                        "options": ["development", "staging", "production", "testing"],
                        "default": "production"
                    },
                    "LOG_LEVEL": {
                        "required": False,
                        "description": "Application log level",
                        "example": "INFO",
                        "options": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        "default": "INFO"
                    },
                    "MAX_CONCURRENT_CALLS": {
                        "required": False,
                        "description": "Maximum concurrent calls",
                        "example": "100",
                        "type": "integer",
                        "default": 100
                    },
                    "ENABLE_METRICS": {
                        "required": False,
                        "description": "Enable metrics collection",
                        "example": "true",
                        "type": "boolean",
                        "default": True
                    }
                }
            },
            "deployment_scenarios": {
                "title": "Deployment Scenarios",
                "description": "Configuration examples for different deployment scenarios",
                "scenarios": {
                    "development": {
                        "description": "Local development setup",
                        "config": {
                            "ENVIRONMENT": "development",
                            "LOG_LEVEL": "DEBUG",
                            "ENABLE_METRICS": "false",
                            "MAX_CONCURRENT_CALLS": "10"
                        }
                    },
                    "production": {
                        "description": "Production deployment",
                        "config": {
                            "ENVIRONMENT": "production",
                            "LOG_LEVEL": "WARNING",
                            "ENABLE_METRICS": "true",
                            "ENABLE_SECURITY_HEADERS": "true",
                            "ENABLE_RATE_LIMITING": "true",
                            "MAX_CONCURRENT_CALLS": "100"
                        }
                    },
                    "docker": {
                        "description": "Docker container deployment",
                        "config": {
                            "LOG_FILE_PATH": "/var/log/voice-assistant/app.log",
                            "BACKUP_STORAGE_PATH": "/var/backups/voice-assistant",
                            "DATABASE_URL": "postgresql://user:pass@db:5432/voice_assistant"
                        }
                    }
                }
            },
            "troubleshooting": {
                "title": "Troubleshooting Guide",
                "description": "Common issues and solutions",
                "issues": {
                    "connection_failed": {
                        "title": "Cannot connect to Asterisk ARI",
                        "symptoms": ["Connection refused", "Timeout errors"],
                        "solutions": [
                            "Check ARI_BASE_URL configuration",
                            "Verify Asterisk is running",
                            "Check ARI credentials",
                            "Ensure network connectivity"
                        ]
                    },
                    "audio_quality": {
                        "title": "Poor audio quality",
                        "symptoms": ["Choppy audio", "High latency", "Audio dropouts"],
                        "solutions": [
                            "Check network bandwidth",
                            "Adjust audio quality settings",
                            "Enable noise reduction",
                            "Verify audio format compatibility"
                        ]
                    },
                    "high_cpu": {
                        "title": "High CPU usage",
                        "symptoms": ["Slow response times", "System alerts"],
                        "solutions": [
                            "Reduce concurrent calls limit",
                            "Optimize audio processing settings",
                            "Scale horizontally",
                            "Check for memory leaks"
                        ]
                    }
                }
            }
        }
    }


def add_configuration_endpoint(app: FastAPI):
    """Add configuration documentation endpoint"""
    
    @app.get("/config-guide", response_class=HTMLResponse, include_in_schema=False)
    async def configuration_guide():
        """Configuration documentation"""
        config_doc = create_configuration_documentation()
        
        # Generate HTML from configuration documentation
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{config_doc['title']}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; margin: -40px -40px 40px -40px; }}
        .section {{ margin: 30px 0; }}
        .variable {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #007bff; }}
        .required {{ border-left-color: #dc3545; }}
        .code {{ background: #f4f4f4; padding: 15px; border-radius: 5px; font-family: monospace; }}
        .example {{ background: #e8f5e8; padding: 10px; border-radius: 5px; }}
        .warning {{ background: #fff3cd; padding: 10px; border-radius: 5px; border-left: 4px solid #ffc107; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{config_doc['title']}</h1>
        <p>Version {config_doc['version']}</p>
    </div>
    
    <div class="section">
        <h2>Environment Variables</h2>
        <p>Configure the NPCL Voice Assistant using these environment variables:</p>
        """
        
        # Add environment variables
        for var_name, var_info in config_doc['sections']['environment_variables']['variables'].items():
            required_class = "required" if var_info.get('required') else ""
            html_content += f"""
        <div class="variable {required_class}">
            <h4>{var_name} {'(Required)' if var_info.get('required') else '(Optional)'}</h4>
            <p>{var_info['description']}</p>
            {f'<div class="example"><strong>Example:</strong> {var_info["example"]}</div>' if 'example' in var_info else ''}
            {f'<div class="code"><strong>Default:</strong> {var_info["default"]}</div>' if 'default' in var_info else ''}
            {f'<div class="warning"><strong>Security:</strong> This is sensitive information</div>' if var_info.get('security') == 'sensitive' else ''}
        </div>
            """
        
        html_content += """
    </div>
    
    <div class="section">
        <h2>Deployment Examples</h2>
        """
        
        # Add deployment scenarios
        for scenario_name, scenario_info in config_doc['sections']['deployment_scenarios']['scenarios'].items():
            html_content += f"""
        <h3>{scenario_name.title()} Environment</h3>
        <p>{scenario_info['description']}</p>
        <div class="code">
            """
            for key, value in scenario_info['config'].items():
                html_content += f"{key}={value}<br>"
            html_content += """
        </div>
            """
        
        html_content += """
    </div>
</body>
</html>
        """
        
        return HTMLResponse(content=html_content)