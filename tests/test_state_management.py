# -*- coding: utf-8 -*-
"""
test_state_management.py - Unit tests for state management module
Tests thread safety, pagination, and error handling
"""
import pytest
import threading
import time
from state_management import AttachmentState, ChatHistory, handle_error

class TestAttachmentState:
    """Test AttachmentState class."""
    
    def test_set_and_get(self):
        """Test basic set/get operations."""
        state = AttachmentState()
        state.set("test.txt", "content", "preview")
        
        name, content, preview = state.get()
        assert name == "test.txt"
        assert content == "content"
        assert preview == "preview"
    
    def test_has_attachment(self):
        """Test has_attachment check."""
        state = AttachmentState()
        assert state.has_attachment() is False
        
        state.set("file.txt", "data", "prev")
        assert state.has_attachment() is True
        
        state.clear()
        assert state.has_attachment() is False
    
    def test_clear(self):
        """Test clearing attachment."""
        state = AttachmentState()
        state.set("file.txt", "content", "preview")
        
        state.clear()
        name, content, preview = state.get()
        
        assert name is None
        assert content is None
        assert preview is None
    
    def test_thread_safety(self):
        """Test AttachmentState is thread-safe (CRITICAL TEST)."""
        state = AttachmentState()
        results = []
        errors = []
        
        def set_attachment(i):
            """Set attachment."""
            try:
                state.set(f"file{i}.txt", f"content{i}", f"preview{i}")
                time.sleep(0.001)  # Simulate some work
                name, content, preview = state.get()
                results.append((name, content, preview))
            except Exception as e:
                errors.append(e)
        
        # Run 20 threads concurrently
        threads = [threading.Thread(target=set_attachment, args=(i,)) for i in range(20)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Should have 20 results, no errors, no corruption
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 20
        
        # Final state should be valid (one of the attachments)
        name, content, preview = state.get()
        assert name is not None
        assert content is not None


class TestChatHistory:
    """Test ChatHistory class."""
    
    def test_add_message(self):
        """Test adding messages."""
        history = ChatHistory(max_messages=100)
        history.add('user', 'Hello')
        history.add('assistant', 'Hi there!')
        
        assert history.count() == 2
        messages = history.get_all()
        assert messages[0].role == 'user'
        assert messages[0].content == 'Hello'
        assert messages[1].role == 'assistant'
    
    def test_pagination(self):
        """Test auto-trimming old messages (CRITICAL TEST - prevents memory leaks)."""
        history = ChatHistory(max_messages=100)
        
        # Add 150 messages
        for i in range(150):
            history.add('user', f'Message {i}')
        
        # Should only keep last 100
        assert history.count() == 100
        
        # First message should be #50 (trimmed 0-49)
        messages = history.get_all()
        assert messages[0].content == 'Message 50'
        assert messages[-1].content == 'Message 149'
    
    def test_get_recent(self):
        """Test getting recent N messages."""
        history = ChatHistory()
        
        for i in range(20):
            history.add('user', f'Msg {i}')
        
        recent = history.get_recent(5)
        assert len(recent) == 5
        assert recent[-1].content == 'Msg 19'
        assert recent[0].content == 'Msg 15'
    
    def test_clear(self):
        """Test clearing history."""
        history = ChatHistory()
        history.add('user', 'Test')
        history.add('assistant', 'Response')
        
        assert history.count() == 2
        
        history.clear()
        assert history.count() == 0
        assert len(history.get_all()) == 0
    
    def test_message_timestamps(self):
        """Test messages have timestamps."""
        history = ChatHistory()
        history.add('user', 'Hello')
        
        messages = history.get_all()
        assert hasattr(messages[0], 'timestamp')
        assert messages[0].timestamp > 0


class TestErrorHandling:
    """Test centralized error handling."""
    
    def test_handle_error_logging(self, caplog):
        """Test error is logged."""
        error = ValueError("Test error")
        handle_error(error, "Test Context", notify_user=False)
        
        assert "Test Context" in caplog.text
        assert "ValueError" in caplog.text
    
    def test_error_message_mapping(self):
        """Test different error types get appropriate messages."""
        # This would require mocking ui.notify
        # For now, just verify function doesn't crash
        errors = [
            ConnectionError("Connection failed"),
            TimeoutError("Timeout"),
            ValueError("Invalid value"),
            FileNotFoundError("File missing"),
        ]
        
        for error in errors:
            try:
                handle_error(error, "Test", notify_user=False)
            except Exception as e:
                pytest.fail(f"handle_error raised exception: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
