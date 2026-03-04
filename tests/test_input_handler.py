
import pytest
import asyncio
from unittest.mock import AsyncMock

class TestInputHandlerPattern:
    """TestInputHandlerPattern class."""
    
    @pytest.mark.asyncio
    async def test_handler_dict_dispatch(self):
        """
        Verify the architectural fix: dictionary-based handler dispatch.
        This reproduces the exact logic used in zena.py to ensure it works in isolation
        without needing to load the entire UI framework.
        """
        # 1. Setup Container (Mutable Dictionary)
        handlers = {'send': None}
        
        # 2. Define Receiver (simulates chip_action defined early in code)
        async def receiver_chip_action():
            """Receiver chip action."""
            # Chip action logic:
            # user_input.value = text (omitted for behavioral test)
            if handlers['send']:
                await handlers['send']()
            else:
                return "handler_missing"
            return "handler_called"
            
        # 3. Verify safety before handler is defined
        result = await receiver_chip_action()
        assert result == "handler_missing", "Should gracefully handle missing handler"
        
        # 4. Define Handler (simulates handle_send defined late in footer)
        mock_handler = AsyncMock()
        
        # 5. REGISTER Handler (The Fix)
        handlers['send'] = mock_handler
        
        # 6. Call Receiver again
        result = await receiver_chip_action()
        
        # 7. Verify Dispatch
        assert result == "handler_called", "Should call handler when present"
        mock_handler.assert_called_once()
