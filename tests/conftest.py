# conftest.py - pytest configuration for Zena tests
import sys
from pathlib import Path

# Add project root to Python path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
