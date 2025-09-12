"""
Voice Assistant Utilities
"""

# Import existing modules
try:
    from .ui_indicators import (
        SpinningIndicator,
        AudioResponseIndicator,
        get_audio_indicator,
        show_spinner
    )
except ImportError:
    SpinningIndicator = None
    AudioResponseIndicator = None
    get_audio_indicator = None
    show_spinner = None

# Import new modules
try:
    from .dependency_manager import get_dependency_manager, safe_import
except ImportError:
    get_dependency_manager = None
    safe_import = None

try:
    from .error_handler import get_error_handler, handle_errors
except ImportError:
    get_error_handler = None
    handle_errors = None

__all__ = [
    "SpinningIndicator",
    "AudioResponseIndicator", 
    "get_audio_indicator",
    "show_spinner",
    "get_dependency_manager",
    "safe_import",
    "get_error_handler",
    "handle_errors"
]