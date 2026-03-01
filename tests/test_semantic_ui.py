# -*- coding: utf-8 -*-
import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from tests.live_diagnostics import run_semantic_ui_audit
from ui.registry import UI_METADATA

@pytest.mark.asyncio
async def test_semantic_audit_logic():
    """Test semantic audit logic."""
    # Setup mock backend
    mock_backend = MagicMock()
    
    # Mock stream generator
    async def mock_stream(prompt):
        yield "The UI Registry looks "
        yield "well-structured and logically sound. "
        yield "All current actions are appropriate for a local AI assistant."
    
    # Assign the generator to the send_message_async call
    mock_backend.send_message_async.side_effect = lambda p: mock_stream(p)
    
    # Run the audit
    passed = await run_semantic_ui_audit(mock_backend)
    
    # Verify
    assert passed is True
    assert mock_backend.send_message_async.called
    
    # Test a failure case (LLM returns 'error')
    async def mock_error_stream(prompt):
        yield "There is an error in the logic "
        yield "of the settings button mapping."
    
    mock_backend.send_message_async.side_effect = lambda p: mock_error_stream(p)
    passed_with_error = await run_semantic_ui_audit(mock_backend)
    assert passed_with_error is False

@pytest.mark.asyncio
async def test_ui_registry_completeness():
    """Ensure every ID in registry has metadata (Spec #8 Compliance)."""
    from ui.registry import UI_IDS, UI_METADATA
    
    # Get all static attributes of UI_IDS that start with BTN, SW, EXP, or SET
    raw_ids = [getattr(UI_IDS, attr) for attr in dir(UI_IDS) 
               if not attr.startswith('__') and isinstance(getattr(UI_IDS, attr), str)]
    
    for rid in raw_ids:
        assert rid in UI_METADATA, f"UI ID {rid} is missing metadata. Spec violation!"
