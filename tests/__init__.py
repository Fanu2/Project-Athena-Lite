"""
Tests package for Local AI Document Assistant.
"""

import sys
import os

# Ensure the app package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_database import *
from tests.test_extraction import *
from tests.test_indexing import *
from tests.test_chat import *

__all__ = [
    "test_database",
    "test_extraction", 
    "test_indexing",
    "test_chat",
]
