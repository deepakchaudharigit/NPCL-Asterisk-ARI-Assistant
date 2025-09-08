#!/usr/bin/env python3
"""
Simple script to run the voice assistant
"""

import sys
import os
from pathlib import Path

# Add src to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from main import main

if __name__ == "__main__":
    sys.exit(main())