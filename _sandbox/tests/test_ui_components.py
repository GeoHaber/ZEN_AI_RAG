import pytest
from unittest.mock import MagicMock, patch
from ui_components import GlassCapsule, SmartChips, LivingLogo

# Mock NiceGUI ui to prevent actual rendering during unit tests
@pytest.fixture
def mock_ui():
    with patch('ui_components.ui') as mock:
        yield mock

class TestGlassCapsule:
    def test_init_creates_capsule(self, mock_ui):
        """Verify capsule compiles and initializes."""
        on_send = MagicMock()
        capsule = GlassCapsule(on_send=on_send)
        
        # Should create a row or card
        assert mock_ui.element.called or mock_ui.row.called or mock_ui.card.called

    def test_user_input_triggers_send(self, mock_ui):
        """Verify send button triggers callback."""
        on_send = MagicMock()
        capsule = GlassCapsule(on_send=on_send)
        
        # Simulate send action (mocking internal logic)
        capsule.handle_send()
        on_send.assert_called_once()

class TestSmartChips:
    def test_update_context(self, mock_ui):
        """Verify chips update based on context."""
        on_click = MagicMock()
        chips = SmartChips(on_click=on_click)
        
        # Initial state should be empty or default
        assert chips.current_context == "default"
        
        # Update context
        chips.update_context("coding")
        assert chips.current_context == "coding"
        # Should verify that ui.button or similar was called to re-render
        # (This implies the component has a re-render method)

class TestLivingLogo:
    def test_state_transitions(self, mock_ui):
        """Verify state changes update classes."""
        logo = LivingLogo()
        
        assert logo.state == "idle"
        
        logo.set_state("thinking")
        assert logo.state == "thinking"
        
        logo.set_state("speaking")
        assert logo.state == "speaking"
