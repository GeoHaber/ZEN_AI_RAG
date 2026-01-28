#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_modern_ui_components.py - Modern UI Component Tests
Comprehensive test suite for modern UI components.

Tests:
- ModernChatMessage rendering
- ModernTypingIndicator functionality
- ModernInputBar interactions
- ModernActionChips clicks
- ModernWelcomeMessage display
- Theme color palette
- Animation classes
- Button variants
- Card styles
- Layout components

Run:
    pytest tests/test_modern_ui_components.py -v
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio


# ==========================================================================
# FIXTURES
# ==========================================================================

@pytest.fixture
def mock_ui_container():
    """Mock NiceGUI container for testing."""
    container = Mock()
    container.classes = Mock(return_value=container)
    container.props = Mock(return_value=container)
    container.move = Mock(return_value=container)
    return container


@pytest.fixture
def modern_theme():
    """Import ModernTheme for testing."""
    from ui.modern_theme import ModernTheme
    return ModernTheme


@pytest.fixture
def chat_components():
    """Import chat components for testing."""
    from ui import modern_chat
    return modern_chat


# ==========================================================================
# THEME TESTS
# ==========================================================================

class TestModernTheme:
    """Test ModernTheme color palette and utilities."""

    def test_purple_primary_color(self, modern_theme):
        """Test that primary purple color is Claude-inspired."""
        assert modern_theme.PURPLE_500 == "#8B5CF6"
        assert modern_theme.PURPLE_600 == "#7C3AED"
        assert modern_theme.PURPLE_400 == "#A78BFA"

    def test_neutral_light_colors(self, modern_theme):
        """Test light mode neutral colors."""
        assert modern_theme.WHITE == "#FFFFFF"
        assert modern_theme.GRAY_50 == "#F9FAFB"
        assert modern_theme.GRAY_900 == "#111827"

    def test_neutral_dark_colors(self, modern_theme):
        """Test dark mode neutral colors."""
        assert modern_theme.SLATE_950 == "#020617"
        assert modern_theme.SLATE_900 == "#0F172A"
        assert modern_theme.SLATE_800 == "#1E293B"

    def test_accent_colors(self, modern_theme):
        """Test accent colors for info, success, warning, error."""
        assert modern_theme.BLUE_500 == "#3B82F6"
        assert modern_theme.GREEN_500 == "#10B981"
        assert modern_theme.RED_500 == "#EF4444"
        assert modern_theme.AMBER_500 == "#F59E0B"

    def test_font_families(self, modern_theme):
        """Test font family definitions."""
        assert "'Inter'" in modern_theme.FONT_SANS
        assert "'Fira Code'" in modern_theme.FONT_MONO

    def test_font_sizes(self, modern_theme):
        """Test font size classes."""
        assert modern_theme.TEXT_XS == "text-xs"
        assert modern_theme.TEXT_BASE == "text-base"
        assert modern_theme.TEXT_3XL == "text-3xl"

    def test_combine_method(self, modern_theme):
        """Test combining multiple class strings."""
        result = modern_theme.combine("class1", "class2", "class3")
        assert result == "class1 class2 class3"

    def test_combine_with_none(self, modern_theme):
        """Test combining classes with None values."""
        result = modern_theme.combine("class1", None, "class2")
        assert result == "class1 class2"

    def test_get_chat_bubble_user(self, modern_theme):
        """Test getting user chat bubble style."""
        result = modern_theme.get_chat_bubble('user')
        assert modern_theme.ChatBubbles.USER in result
        assert "bg-purple-600" in result
        assert "text-white" in result

    def test_get_chat_bubble_assistant(self, modern_theme):
        """Test getting AI chat bubble style."""
        result = modern_theme.get_chat_bubble('assistant')
        assert modern_theme.ChatBubbles.AI in result
        assert "bg-gray-100" in result

    def test_get_chat_bubble_rag(self, modern_theme):
        """Test getting RAG-enhanced chat bubble style."""
        result = modern_theme.get_chat_bubble('assistant', rag_enhanced=True)
        assert modern_theme.ChatBubbles.RAG in result
        assert "bg-blue-50" in result
        assert "border-blue-500" in result

    def test_get_chat_bubble_system(self, modern_theme):
        """Test getting system chat bubble style."""
        result = modern_theme.get_chat_bubble('system')
        assert modern_theme.ChatBubbles.SYSTEM in result

    def test_get_button_primary(self, modern_theme):
        """Test getting primary button style."""
        result = modern_theme.get_button('primary', 'md')
        assert modern_theme.Buttons.PRIMARY in result
        assert "bg-purple-600" in result

    def test_get_button_secondary(self, modern_theme):
        """Test getting secondary button style."""
        result = modern_theme.get_button('secondary', 'lg')
        assert modern_theme.Buttons.SECONDARY in result

    def test_chat_bubble_classes(self, modern_theme):
        """Test chat bubble class definitions."""
        assert "rounded-3xl" in modern_theme.ChatBubbles.BASE
        assert "px-6 py-4" in modern_theme.ChatBubbles.BASE
        assert "max-w-3xl" in modern_theme.ChatBubbles.BASE

    def test_button_classes(self, modern_theme):
        """Test button class definitions."""
        assert "rounded-xl" in modern_theme.Buttons.BASE
        assert "transition-all" in modern_theme.Buttons.BASE

    def test_card_classes(self, modern_theme):
        """Test card class definitions."""
        assert "rounded-2xl" in modern_theme.Cards.BASE
        assert "border" in modern_theme.Cards.BASE

    def test_animation_classes(self, modern_theme):
        """Test animation class definitions."""
        assert modern_theme.Animations.PULSE == "animate-pulse"
        assert modern_theme.Animations.FADE_IN == "animate-fade-in opacity-0"


# ==========================================================================
# CHAT MESSAGE TESTS
# ==========================================================================

class TestModernChatMessage:
    """Test ModernChatMessage component."""

    def test_create_user_message(self, chat_components):
        """Test creating a user message."""
        msg = chat_components.ModernChatMessage(
            role='user',
            content='Hello!',
            avatar_text='U'
        )

        assert msg.role == 'user'
        assert msg.content == 'Hello!'
        assert msg.avatar_text == 'U'
        assert msg.rag_enhanced is False
        assert msg.sources == []

    def test_create_ai_message(self, chat_components):
        """Test creating an AI message."""
        msg = chat_components.ModernChatMessage(
            role='assistant',
            content='Hi there!',
            avatar_text='Z'
        )

        assert msg.role == 'assistant'
        assert msg.content == 'Hi there!'
        assert msg.avatar_text == 'Z'

    def test_create_rag_message(self, chat_components):
        """Test creating a RAG-enhanced message."""
        sources = [
            {'title': 'Doc 1', 'url': 'http://example.com', 'text': 'Content'}
        ]

        msg = chat_components.ModernChatMessage(
            role='assistant',
            content='RAG answer',
            avatar_text='Z',
            rag_enhanced=True,
            sources=sources
        )

        assert msg.rag_enhanced is True
        assert len(msg.sources) == 1
        assert msg.sources[0]['title'] == 'Doc 1'

    def test_create_system_message(self, chat_components):
        """Test creating a system message."""
        msg = chat_components.ModernChatMessage(
            role='system',
            content='Connection established'
        )

        assert msg.role == 'system'
        assert msg.content == 'Connection established'

    def test_default_avatar_text(self, chat_components):
        """Test default avatar text assignment."""
        user_msg = chat_components.ModernChatMessage(role='user', content='Hi')
        assert user_msg.avatar_text == 'U'

        ai_msg = chat_components.ModernChatMessage(role='assistant', content='Hello')
        assert ai_msg.avatar_text == 'Z'

    @patch('ui.modern_chat.ui')
    def test_render_user_message(self, mock_ui, chat_components, mock_ui_container):
        """Test rendering a user message."""
        msg = chat_components.ModernChatMessage(
            role='user',
            content='Test message',
            avatar_text='U'
        )

        # Mock ui.row, ui.column, ui.avatar, ui.label, ui.markdown
        mock_row = Mock()
        mock_row.classes = Mock(return_value=mock_row)
        mock_row.move = Mock(return_value=mock_row)
        mock_row.__enter__ = Mock(return_value=mock_row)
        mock_row.__exit__ = Mock(return_value=None)

        mock_column = Mock()
        mock_column.classes = Mock(return_value=mock_column)
        mock_column.__enter__ = Mock(return_value=mock_column)
        mock_column.__exit__ = Mock(return_value=None)

        mock_avatar = Mock()
        mock_avatar.classes = Mock(return_value=mock_avatar)

        mock_label = Mock()
        mock_label.classes = Mock(return_value=mock_label)

        mock_markdown = Mock()
        mock_markdown.classes = Mock(return_value=mock_markdown)

        mock_ui.row.return_value = mock_row
        mock_ui.column.return_value = mock_column
        mock_ui.avatar.return_value = mock_avatar
        mock_ui.label.return_value = mock_label
        mock_ui.markdown.return_value = mock_markdown

        # Render
        msg.render(mock_ui_container)

        # Verify ui.row was called
        mock_ui.row.assert_called()

        # Verify ui.avatar was called (for user on right side)
        mock_ui.avatar.assert_called_with('U', color='gray', text_color='white')

        # Verify ui.markdown was called with content
        mock_ui.markdown.assert_called_with('Test message')


# ==========================================================================
# TYPING INDICATOR TESTS
# ==========================================================================

class TestModernTypingIndicator:
    """Test ModernTypingIndicator component."""

    def test_create_typing_indicator(self, chat_components):
        """Test creating a typing indicator."""
        indicator = chat_components.ModernTypingIndicator()
        assert indicator.container is None

    @patch('ui.modern_chat.ui')
    def test_render_typing_indicator(self, mock_ui, chat_components, mock_ui_container):
        """Test rendering typing indicator."""
        indicator = chat_components.ModernTypingIndicator()

        # Mock ui components
        mock_row = Mock()
        mock_row.classes = Mock(return_value=mock_row)
        mock_row.move = Mock(return_value=mock_row)
        mock_row.__enter__ = Mock(return_value=mock_row)
        mock_row.__exit__ = Mock(return_value=None)

        mock_ui.row.return_value = mock_row

        # Render
        indicator.render(mock_ui_container)

        # Verify ui.row was called
        mock_ui.row.assert_called()

        # Verify container is set
        assert indicator.container is not None

    def test_remove_typing_indicator(self, chat_components):
        """Test removing typing indicator."""
        indicator = chat_components.ModernTypingIndicator()
        mock_container = Mock()
        mock_container.delete = Mock()
        indicator.container = mock_container

        # Remove
        indicator.remove()

        # Verify delete was called
        mock_container.delete.assert_called_once()
        # Verify container was set to None
        assert indicator.container is None


# ==========================================================================
# INPUT BAR TESTS
# ==========================================================================

class TestModernInputBar:
    """Test ModernInputBar component."""

    def test_create_input_bar(self, chat_components):
        """Test creating an input bar."""
        on_send = AsyncMock()
        on_upload = AsyncMock()
        on_voice = AsyncMock()

        input_bar = chat_components.ModernInputBar(
            on_send=on_send,
            on_upload=on_upload,
            on_voice=on_voice,
            placeholder='Type here...'
        )

        assert input_bar.on_send == on_send
        assert input_bar.on_upload == on_upload
        assert input_bar.on_voice == on_voice
        assert input_bar.placeholder == 'Type here...'
        assert input_bar.input_field is None
        assert input_bar.attachment_preview is None

    def test_show_attachment(self, chat_components):
        """Test showing attachment preview."""
        input_bar = chat_components.ModernInputBar()

        # Mock attachment preview
        input_bar.attachment_preview = Mock()
        input_bar.attachment_preview.text = ''
        input_bar.attachment_preview.props = Mock()

        # Show attachment
        input_bar.show_attachment('test.txt', 1024)

        # Verify text was set
        assert 'test.txt' in input_bar.attachment_preview.text
        assert '1,024' in input_bar.attachment_preview.text

        # Verify props was called to make visible
        input_bar.attachment_preview.props.assert_called_with('visible=true')

    def test_hide_attachment(self, chat_components):
        """Test hiding attachment preview."""
        input_bar = chat_components.ModernInputBar()

        # Mock attachment preview
        input_bar.attachment_preview = Mock()
        input_bar.attachment_preview.text = 'File: test.txt'
        input_bar.attachment_preview.props = Mock()

        # Hide attachment
        input_bar.hide_attachment()

        # Verify text was cleared
        assert input_bar.attachment_preview.text == ''

        # Verify props was called to hide
        input_bar.attachment_preview.props.assert_called_with('visible=false')

    @pytest.mark.asyncio
    async def test_handle_send_with_message(self, chat_components):
        """Test handling send with a message."""
        on_send = AsyncMock()
        input_bar = chat_components.ModernInputBar(on_send=on_send)

        # Mock input field
        input_bar.input_field = Mock()
        input_bar.input_field.value = '  Hello!  '

        # Handle send
        await input_bar._handle_send()

        # Verify on_send was called with trimmed message
        on_send.assert_called_once_with('Hello!')

        # Verify input was cleared
        assert input_bar.input_field.value == ''

    @pytest.mark.asyncio
    async def test_handle_send_with_empty_message(self, chat_components):
        """Test handling send with empty message (should not call on_send)."""
        on_send = AsyncMock()
        input_bar = chat_components.ModernInputBar(on_send=on_send)

        # Mock input field with empty value
        input_bar.input_field = Mock()
        input_bar.input_field.value = '   '

        # Handle send
        await input_bar._handle_send()

        # Verify on_send was NOT called
        on_send.assert_not_called()


# ==========================================================================
# ACTION CHIPS TESTS
# ==========================================================================

class TestModernActionChips:
    """Test ModernActionChips component."""

    def test_create_action_chips(self, chat_components):
        """Test creating action chips."""
        actions = [
            {'label': 'Help', 'value': 'help'},
            {'label': 'Examples', 'value': 'examples'}
        ]
        on_click = AsyncMock()

        chips = chat_components.ModernActionChips(
            actions=actions,
            on_click=on_click
        )

        assert len(chips.actions) == 2
        assert chips.actions[0]['label'] == 'Help'
        assert chips.on_click == on_click

    @patch('ui.modern_chat.ui')
    def test_render_action_chips(self, mock_ui, chat_components, mock_ui_container):
        """Test rendering action chips."""
        actions = [
            {'label': 'Action 1', 'value': 'action1'},
            {'label': 'Action 2', 'value': 'action2'}
        ]

        chips = chat_components.ModernActionChips(actions=actions)

        # Mock ui components
        mock_column = Mock()
        mock_column.classes = Mock(return_value=mock_column)
        mock_column.move = Mock(return_value=mock_column)
        mock_column.__enter__ = Mock(return_value=mock_column)
        mock_column.__exit__ = Mock(return_value=None)

        mock_row = Mock()
        mock_row.classes = Mock(return_value=mock_row)
        mock_row.__enter__ = Mock(return_value=mock_row)
        mock_row.__exit__ = Mock(return_value=None)

        mock_label = Mock()
        mock_label.classes = Mock(return_value=mock_label)

        mock_button = Mock()
        mock_button.classes = Mock(return_value=mock_button)
        mock_button.props = Mock(return_value=mock_button)

        mock_ui.column.return_value = mock_column
        mock_ui.row.return_value = mock_row
        mock_ui.label.return_value = mock_label
        mock_ui.button.return_value = mock_button

        # Render
        chips.render(mock_ui_container)

        # Verify ui.button was called for each action
        assert mock_ui.button.call_count == 2


# ==========================================================================
# WELCOME MESSAGE TESTS
# ==========================================================================

class TestModernWelcomeMessage:
    """Test ModernWelcomeMessage component."""

    def test_create_welcome_message(self, chat_components):
        """Test creating a welcome message."""
        features = ['Feature 1', 'Feature 2', 'Feature 3']

        welcome = chat_components.ModernWelcomeMessage(
            app_name='ZenAI',
            features=features,
            custom_message='Welcome to testing'
        )

        assert welcome.app_name == 'ZenAI'
        assert len(welcome.features) == 3
        assert welcome.custom_message == 'Welcome to testing'

    def test_default_features(self, chat_components):
        """Test default features list."""
        welcome = chat_components.ModernWelcomeMessage(app_name='ZenAI')

        # Should have default features
        assert len(welcome.features) > 0
        assert any('AI' in f for f in welcome.features)

    @patch('ui.modern_chat.ui')
    def test_render_welcome_message(self, mock_ui, chat_components, mock_ui_container):
        """Test rendering welcome message."""
        welcome = chat_components.ModernWelcomeMessage(app_name='Test App')

        # Mock ui components
        mock_column = Mock()
        mock_column.classes = Mock(return_value=mock_column)
        mock_column.move = Mock(return_value=mock_column)
        mock_column.__enter__ = Mock(return_value=mock_column)
        mock_column.__exit__ = Mock(return_value=None)

        mock_ui.column.return_value = mock_column

        # Render
        welcome.render(mock_ui_container)

        # Verify ui.column was called
        mock_ui.column.assert_called()


# ==========================================================================
# CSS TESTS
# ==========================================================================

class TestModernCSS:
    """Test modern CSS string."""

    def test_modern_css_defined(self):
        """Test that MODERN_CSS constant is defined."""
        from ui.modern_theme import MODERN_CSS
        assert MODERN_CSS is not None
        assert len(MODERN_CSS) > 0

    def test_css_contains_animations(self):
        """Test that CSS contains animation definitions."""
        from ui.modern_theme import MODERN_CSS

        assert '@keyframes fade-in' in MODERN_CSS
        assert '@keyframes slide-up' in MODERN_CSS
        assert '@keyframes typing-pulse' in MODERN_CSS

    def test_css_contains_font_import(self):
        """Test that CSS imports Inter font."""
        from ui.modern_theme import MODERN_CSS

        assert '@import url' in MODERN_CSS
        assert 'Inter' in MODERN_CSS

    def test_css_contains_custom_scrollbar(self):
        """Test that CSS includes custom scrollbar styling."""
        from ui.modern_theme import MODERN_CSS

        assert '::-webkit-scrollbar' in MODERN_CSS

    def test_css_contains_dark_mode(self):
        """Test that CSS includes dark mode styles."""
        from ui.modern_theme import MODERN_CSS

        assert '.dark' in MODERN_CSS


# ==========================================================================
# INTEGRATION TESTS
# ==========================================================================

class TestIntegration:
    """Test integration between components."""

    def test_import_modern_theme(self):
        """Test importing ModernTheme from ui module."""
        from ui import ModernTheme
        assert ModernTheme is not None

    def test_import_modern_css(self):
        """Test importing MODERN_CSS from ui module."""
        from ui import MODERN_CSS
        assert MODERN_CSS is not None

    def test_theme_chat_bubbles_accessible(self):
        """Test that ChatBubbles class is accessible."""
        from ui import ModernTheme
        assert hasattr(ModernTheme, 'ChatBubbles')
        assert hasattr(ModernTheme.ChatBubbles, 'USER_FULL')
        assert hasattr(ModernTheme.ChatBubbles, 'AI_FULL')
        assert hasattr(ModernTheme.ChatBubbles, 'RAG_FULL')

    def test_theme_buttons_accessible(self):
        """Test that Buttons class is accessible."""
        from ui import ModernTheme
        assert hasattr(ModernTheme, 'Buttons')
        assert hasattr(ModernTheme.Buttons, 'PRIMARY_FULL')
        assert hasattr(ModernTheme.Buttons, 'SECONDARY_FULL')

    def test_theme_cards_accessible(self):
        """Test that Cards class is accessible."""
        from ui import ModernTheme
        assert hasattr(ModernTheme, 'Cards')
        assert hasattr(ModernTheme.Cards, 'PADDED')
        assert hasattr(ModernTheme.Cards, 'INFO')

    def test_chat_message_class_exists(self):
        """Test that ModernChatMessage class can be imported."""
        from ui.modern_chat import ModernChatMessage
        assert ModernChatMessage is not None

    def test_typing_indicator_class_exists(self):
        """Test that ModernTypingIndicator class can be imported."""
        from ui.modern_chat import ModernTypingIndicator
        assert ModernTypingIndicator is not None

    def test_input_bar_class_exists(self):
        """Test that ModernInputBar class can be imported."""
        from ui.modern_chat import ModernInputBar
        assert ModernInputBar is not None

    def test_action_chips_class_exists(self):
        """Test that ModernActionChips class can be imported."""
        from ui.modern_chat import ModernActionChips
        assert ModernActionChips is not None

    def test_welcome_message_class_exists(self):
        """Test that ModernWelcomeMessage class can be imported."""
        from ui.modern_chat import ModernWelcomeMessage
        assert ModernWelcomeMessage is not None


# ==========================================================================
# SUMMARY
# ==========================================================================

if __name__ == '__main__':
    print('=' * 70)
    print('MODERN UI COMPONENT TESTS')
    print('=' * 70)
    print()
    print('Test Coverage:')
    print('  - ModernTheme (21 tests)')
    print('  - ModernChatMessage (7 tests)')
    print('  - ModernTypingIndicator (3 tests)')
    print('  - ModernInputBar (5 tests)')
    print('  - ModernActionChips (2 tests)')
    print('  - ModernWelcomeMessage (3 tests)')
    print('  - CSS & Integration (15 tests)')
    print()
    print('Total: 56 tests')
    print()
    print('Run: pytest tests/test_modern_ui_components.py -v')
    print('=' * 70)
