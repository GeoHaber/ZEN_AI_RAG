# -*- coding: utf-8 -*-
"""
Tests for loading messages in locales
"""

import pytest
import random
from ui.locales import get_locale
from ui.locales.base import BaseLocale
from ui.locales.es import SpanishLocale


class TestLoadingMessages:
    """Test fun loading messages are available."""

    def test_english_loading_messages_exist(self):
        """Test English locale has loading messages."""
        locale = get_locale()

        assert hasattr(locale, "LOADING_WAITING_FOR_USER")
        assert hasattr(locale, "LOADING_THINKING")
        assert hasattr(locale, "LOADING_RAG_THINKING")
        assert hasattr(locale, "LOADING_SWARM_THINKING")

        assert isinstance(locale.LOADING_WAITING_FOR_USER, list)
        assert isinstance(locale.LOADING_THINKING, list)
        assert isinstance(locale.LOADING_RAG_THINKING, list)
        assert isinstance(locale.LOADING_SWARM_THINKING, list)

    def test_loading_messages_not_empty(self):
        """Test loading message lists have content."""
        locale = get_locale()

        assert len(locale.LOADING_WAITING_FOR_USER) > 0
        assert len(locale.LOADING_THINKING) > 0
        assert len(locale.LOADING_RAG_THINKING) > 0
        assert len(locale.LOADING_SWARM_THINKING) > 0

    def test_loading_messages_are_strings(self):
        """Test all loading messages are strings."""
        locale = get_locale()

        for msg in locale.LOADING_WAITING_FOR_USER:
            assert isinstance(msg, str)
            assert len(msg) > 0

        for msg in locale.LOADING_THINKING:
            assert isinstance(msg, str)
            assert len(msg) > 0

        for msg in locale.LOADING_RAG_THINKING:
            assert isinstance(msg, str)
            assert len(msg) > 0

        for msg in locale.LOADING_SWARM_THINKING:
            assert isinstance(msg, str)
            assert len(msg) > 0

    def test_random_selection_works(self):
        """Test random message selection works."""
        locale = get_locale()

        # Should not raise exception
        msg1 = random.choice(locale.LOADING_WAITING_FOR_USER)
        msg2 = random.choice(locale.LOADING_THINKING)
        msg3 = random.choice(locale.LOADING_RAG_THINKING)
        msg4 = random.choice(locale.LOADING_SWARM_THINKING)

        assert isinstance(msg1, str)
        assert isinstance(msg2, str)
        assert isinstance(msg3, str)
        assert isinstance(msg4, str)

    def test_spanish_loading_messages_exist(self):
        """Test Spanish locale has loading messages."""
        locale = SpanishLocale()

        assert hasattr(locale, "LOADING_WAITING_FOR_USER")
        assert hasattr(locale, "LOADING_THINKING")
        assert hasattr(locale, "LOADING_RAG_THINKING")
        assert hasattr(locale, "LOADING_SWARM_THINKING")

        assert len(locale.LOADING_WAITING_FOR_USER) > 0
        assert len(locale.LOADING_THINKING) > 0
        assert len(locale.LOADING_RAG_THINKING) > 0
        assert len(locale.LOADING_SWARM_THINKING) > 0

    def test_messages_have_emojis(self):
        """Test loading messages include emojis for fun."""
        locale = get_locale()

        # Check at least one message has an emoji (unicode > 127)
        has_emoji_waiting = any(ord(c) > 127 for msg in locale.LOADING_WAITING_FOR_USER for c in msg)
        has_emoji_thinking = any(ord(c) > 127 for msg in locale.LOADING_THINKING for c in msg)

        assert has_emoji_waiting, "Waiting messages should have emojis"
        assert has_emoji_thinking, "Thinking messages should have emojis"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
