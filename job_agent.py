#!/usr/bin/env python3
"""
Job Search AI Agent - Legacy wrapper for backward compatibility

This is a simple wrapper that delegates to the new modular architecture.
For new deployments, use: python -m src.main
"""

import sys
import os

# Add src to path so we can import the new modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import main

if __name__ == '__main__':
    main()