"""
API module for Voice Assistant
Provides API documentation and endpoint management
"""

# Import modules with graceful fallback
try:
    from .documentation import add_api_documentation, add_configuration_endpoint
except ImportError:
    add_api_documentation = None
    add_configuration_endpoint = None

__all__ = [
    'add_api_documentation',
    'add_configuration_endpoint'
]