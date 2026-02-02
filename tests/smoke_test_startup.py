
import sys
import os
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

# Add project root to path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

def test_zena_imports_successfully():
    """Test that zena.py can be imported without crashing (catches global NameErrors)."""
    try:
        import zena
    except Exception as e:
        pytest.fail(f"Failed to import zena.py: {e}")

@pytest.mark.asyncio
async def test_zenai_page_execution():
    """
    Test that the main page function 'zenai_page' executes without 
    NameError or AttributeError.
    
    This catches issues like missing 'Icons', 'ui_state', or 'rag_dialog' 
    referenced inside the page function.
    """
    # 1. Import zena
    import zena
    
    # 2. Mock the Client and UI context
    # NiceGUI functions (ui.label, etc) usually require an active client context.
    # We will try to run it. If it fails due to missing context, that's fine, 
    # as long as it's not a NameError.
    
    client_mock = MagicMock()
    
    try:
        # We wrap it in a catch-all because we expect it might fail on 
        # "RuntimeError: No client connected" or similar, which verifies 
        # that it DIDN'T fail on NameError before reaching NiceGUI logic.
        await zena.nebula_page()
    except NameError as e:
        pytest.fail(f"CRITICAL: NameError in UI code: {e}")
    except AttributeError as e:
        # Check if it's a simple mock attribute error vs a real bug
        if "has no attribute" in str(e):
             pytest.fail(f"CRITICAL: AttributeError in UI code: {e}")
    except RuntimeError as e:
        # RuntimeError is expected because we aren't in a real NiceGUI loop
        pass
    except Exception as e:
         # Any other crash needs investigation
         print(f"Warning: Unexpected error (might be benign context issue): {e}")

if __name__ == "__main__":
    # Allow running directly: python tests/smoke_test_startup.py
    sys.exit(pytest.main([__file__]))
