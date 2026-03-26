import sys
from pathlib import Path

# Add project root and src to sys.path for all tests
root = Path(__file__).parent
src = root / "src"

for path in [root, src]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
