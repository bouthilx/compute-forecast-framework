#!/usr/bin/env python3
"""Run enhanced classification tests without uv environment issues."""

import os
import sys
from pathlib import Path

# Add package source to path
package_root = Path(__file__).parent
sys.path.insert(0, str(package_root / "src"))

# Mock rapidfuzz if not available
try:
    import rapidfuzz
except ImportError:
    print("Warning: rapidfuzz not available, using mock implementation")
    # Create a mock rapidfuzz module
    class MockFuzz:
        @staticmethod
        def ratio(s1, s2):
            # Simple character-based similarity
            if not s1 or not s2:
                return 0
            common = sum(1 for c1, c2 in zip(s1.lower(), s2.lower()) if c1 == c2)
            return int(100 * common / max(len(s1), len(s2)))
    
    class MockRapidFuzz:
        fuzz = MockFuzz()
    
    sys.modules['rapidfuzz'] = MockRapidFuzz()

# Now run the tests
from test_enhanced_classification import main

if __name__ == "__main__":
    sys.exit(main())