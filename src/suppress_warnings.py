#!/usr/bin/env python3
"""
Suppress common warnings and debug messages for clean terminal output.
This module should be imported before any other modules that might show warnings.
"""

import os
import warnings

# Suppress pygame welcome message
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

# Suppress pkg_resources deprecation warning
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pkg_resources")

# Suppress other common warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pygame")
warnings.filterwarnings("ignore", category=FutureWarning)

# Set environment variables to suppress various debug outputs
os.environ['PYTHONWARNINGS'] = 'ignore::DeprecationWarning'