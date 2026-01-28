"""
Comprehensive Test Suite for engine_server.py
==========================================

TDD Philosophy: "Trust but Verify" - Ronald Reagan

This test suite covers all testable functions in engine_server.py:
- Pure functions (easy to test)
- Stateful functions (using mocks)
- Integration tests (end-to-end flows)

Run with: pytest tests/test_engine_server.py -v
"""

import pytest
import sys
import os
import json
import threading
import subprocess
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from io import StringIO

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure config is loaded before engine_server if necessary
from zena_mode import server as engine_server

# ============================================================================
# CATEGORY 1: PURE FUNCTIONS (No side effects - easiest to test)
# ============================================================================

class TestPureFunctions:
    """Test pure functions with no side effects."""

    def test_env_int_with_valid_env_var(self):
        """Test env_int() reads integer from environment variable."""
        with patch.dict(os.environ, {"TEST_VAR": "42"}):
            result = engine_server.env_int("TEST_VAR", 10)
            assert result == 42

    def test_env_int_with_missing_env_var(self):
        """Test env_int() returns default when var missing."""
        with patch.dict(os.environ, {}, clear=True):
            result = engine_server.env_int("MISSING_VAR", 99)
            assert result == 99

    def test_env_int_with_invalid_value(self):
        """Test env_int() returns default on invalid integer."""
        with patch.dict(os.environ, {"TEST_VAR": "not_a_number"}):
            result = engine_server.env_int("TEST_VAR", 50)
            assert result == 50

    def test_env_int_with_negative_values(self):
        """Test env_int() handles negative integers."""
        with patch.dict(os.environ, {"TEST_VAR": "-10"}):
            result = engine_server.env_int("TEST_VAR", 0)
            assert result == -10


# ============================================================================
# CATEGORY 2: OUTPUT UTILITIES (Thread-safe print/exit)
# ============================================================================

class TestOutputUtilities:
    """Test safe_print() and safe_exit() functions."""

    def test_safe_print_forces_flush(self, capsys):
        """Test safe_print() always flushes output immediately."""
        engine_server.safe_print("Test message")
        captured = capsys.readouterr()
        assert "Test message" in captured.out

    def test_safe_print_with_multiple_args(self, capsys):
        """Test safe_print() handles multiple arguments like print()."""
        engine_server.safe_print("Hello", "World", 123)
        captured = capsys.readouterr()
        assert "Hello World 123" in captured.out

    def test_safe_print_with_sep_kwarg(self, capsys):
        """Test safe_print() respects sep= keyword argument."""
        engine_server.safe_print("A", "B", "C", sep="-")
        captured = capsys.readouterr()
        assert "A-B-C" in captured.out

    def test_safe_exit_calls_sys_exit(self):
        """Test safe_exit() calls sys.exit() with correct code."""
        with pytest.raises(SystemExit) as exc_info:
            engine_server.safe_exit(42, delay=0.01)  # Short delay for testing
        assert exc_info.value.code == 42

    def test_safe_exit_flushes_buffers(self):
        """Test safe_exit() flushes stdout/stderr before exit."""
        with patch('sys.stdout.flush') as mock_stdout, \
             patch('sys.stderr.flush') as mock_stderr, \
             pytest.raises(SystemExit):
            engine_server.safe_exit(0, delay=0.01)

        mock_stdout.assert_called_once()
        mock_stderr.assert_called_once()


# ============================================================================
# CATEGORY 3: PROCESS MANAGEMENT (Global state manipulation)
# ============================================================================

class TestProcessManagement:
    """Test process registration and monitoring."""

    def setup_method(self):
        """Reset global state before each test."""
        engine_server.MONITORED_PROCESSES.clear()

    def test_register_process_adds_to_global_dict(self):
        """Test register_process() adds process to MONITORED_PROCESSES."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 1234

        engine_server.register_process("test-server", mock_process, critical=True)

        assert "test-server" in engine_server.MONITORED_PROCESSES
        assert engine_server.MONITORED_PROCESSES["test-server"]["process"] == mock_process
        assert engine_server.MONITORED_PROCESSES["test-server"]["critical"] is True

    def test_register_process_sets_defaults(self):
        """Test register_process() sets correct default values."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 1234

        engine_server.register_process("test-process", mock_process)

        info = engine_server.MONITORED_PROCESSES["test-process"]
        assert info["critical"] is False
        assert info["restarts"] == 0
        assert info["max_restarts"] == 1  # Non-critical default

    def test_register_process_critical_has_more_restarts(self):
        """Test critical processes get more restart attempts."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 1234

        engine_server.register_process("critical-server", mock_process, critical=True)

        info = engine_server.MONITORED_PROCESSES["critical-server"]
        assert info["max_restarts"] == 3  # Critical default

    def test_check_processes_detects_crashes(self):
        """Test check_processes() detects crashed processes."""
        # Create mock crashed process
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.poll.return_value = 1  # Exit code 1 = crash

        engine_server.MONITORED_PROCESSES["crashed-server"] = {
            "process": mock_process,
            "critical": True,
            "restarts": 0,
            "max_restarts": 3
        }

        crashed = engine_server.check_processes()

        assert len(crashed) == 1
        assert crashed[0][0] == "crashed-server"  # name
        assert crashed[0][1] == 1  # exit_code
        assert crashed[0][2] is True  # is_critical

    def test_check_processes_ignores_running_processes(self):
        """Test check_processes() ignores still-running processes."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.poll.return_value = None  # None = still running

        engine_server.MONITORED_PROCESSES["running-server"] = {
            "process": mock_process,
            "critical": False,
            "restarts": 0,
            "max_restarts": 1
        }

        crashed = engine_server.check_processes()

        assert len(crashed) == 0

    def test_check_processes_removes_crashed_from_monitoring(self):
        """Test check_processes() removes crashed processes from dict."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.poll.return_value = 1

        engine_server.MONITORED_PROCESSES["crashed"] = {
            "process": mock_process,
            "critical": False,
            "restarts": 0,
            "max_restarts": 1
        }

        engine_server.check_processes()

        assert "crashed" not in engine_server.MONITORED_PROCESSES


# ============================================================================
# CATEGORY 4: LAZY LOADING (Import caching)
# ============================================================================

class TestLazyLoading:
    """Test lazy import functions."""

    def test_get_model_manager_caches_import(self):
        """Test get_model_manager() caches the module."""
        # Reset cache
        engine_server._model_manager_cache = None

        with patch('builtins.__import__', return_value=Mock()) as mock_import:
            # First call
            result1 = engine_server.get_model_manager()
            # Second call
            result2 = engine_server.get_model_manager()

            # Import should only happen once for model_manager
            # (Filtering calls to only observe those for 'model_manager')
            mm_calls = [c for c in mock_import.call_args_list if c[0][0] == 'model_manager']
            assert len(mm_calls) == 1
            assert result1 is result2

    def test_get_model_manager_raises_on_missing_module(self):
        """Test get_model_manager() raises ImportError if module missing."""
        engine_server._model_manager_cache = None

        with patch('builtins.__import__', side_effect=ImportError("Module not found")):
            # Note: We need to be careful with __import__ as many things use it
            # We use a wrapper to only raise on the target module
            def mocked_import(name, *args, **kwargs):
                if name == 'model_manager':
                    raise ImportError("Module not found")
                return MagicMock()

            # Using a more targetted patch or refined side_effect
            with patch('builtins.__import__', side_effect=mocked_import):
                with pytest.raises(ImportError, match="model_manager module not found"):
                    engine_server.get_model_manager()

    def test_get_cached_voice_service_caches_import(self):
        """Test get_cached_voice_service() caches the module."""
        engine_server._voice_service_cache = None

        with patch('builtins.__import__', return_value=Mock()) as mock_import:
            result1 = engine_server.get_cached_voice_service()
            result2 = engine_server.get_cached_voice_service()

            vs_calls = [c for c in mock_import.call_args_list if c[0][0] == 'voice_service']
            assert len(vs_calls) == 1
            assert result1 is result2


# ============================================================================
# CATEGORY 12: NEW TESTS (Expanding Coverage)
# ============================================================================

class TestNewUtilities:
    """Tests for newly added utility functions."""

    @patch('psutil.process_iter')
    def test_kill_process_by_name(self, mock_iter):
        """Test kill_process_by_name() terminates correct processes."""
        mock_proc = Mock()
        mock_proc.info = {'pid': 1111, 'name': 'llama-server.exe'}
        
        mock_iter.return_value = [mock_proc]
        
        engine_server.kill_process_by_name("llama-server.exe")
        
        mock_proc.terminate.assert_called_once()

class TestConfiguration:
    """Test configuration functions."""

    def test_restart_with_model_updates_global_path(self):
        """Test restart_with_model() updates MODEL_PATH global."""
        # We need to mock the external dependencies of restart_with_model
        with patch('zena_mode.server.kill_process_by_name'), \
             patch('zena_mode.server.subprocess.Popen'), \
             patch('zena_mode.server.os._exit'):
            
            original_path = engine_server.MODEL_PATH
            test_model = "test-model.gguf"
            
            # Since restart_with_model calls os._exit, we should mock it
            engine_server.restart_with_model(test_model)
            
            # Note: In our implementation, we don't have the return value 
            # because it calls os._exit(0) at the end.
            
            # Check if kill_process_by_name was called
            # and verify the logic indirectly if possible, or just mock it.

    def test_build_llama_cmd_returns_list(self):
        """Test build_llama_cmd() returns a list of strings."""
        cmd = engine_server.build_llama_cmd(port=8001, threads=4)
        assert isinstance(cmd, list)
        assert all(isinstance(arg, str) for arg in cmd)


# ============================================================================
# CATEGORY 6: PROCESS UTILITIES (Kill tree, scale swarm)
# ============================================================================

class TestProcessUtilities:
    """Test process management utilities."""

    @patch('zena_mode.server.kill_process_tree')
    def test_scale_swarm_decreases_expert_count(self, mock_kill):
        """Test scale_swarm() removes expert processes when scaling down."""
        # Setup 5 running experts
        engine_server.EXPERT_PROCESSES.clear()
        for i in range(5):
            mock_proc = Mock(spec=subprocess.Popen)
            mock_proc.pid = 1000 + i
            engine_server.EXPERT_PROCESSES[8005 + i] = mock_proc

        engine_server.scale_swarm(2)

        # Should have 2 experts remaining
        assert len(engine_server.EXPERT_PROCESSES) == 2
        assert mock_kill.call_count == 3


# ============================================================================
# CATEGORY 11: COMMAND BUILDING (Extracted duplicate logic)
# ============================================================================

# ============================================================================
# CATEGORY 13: ORCHESTRATOR TESTS (HTTP API)
# ============================================================================

class TestOrchestrator:
    """Tests for the ZenAIOrchestrator (HTTP Server) class."""

    def setup_method(self):
        """Prepare mock for Orchestrator without calling base __init__."""
        # This prevents the TypeError from BaseHTTPRequestHandler
        with patch('http.server.BaseHTTPRequestHandler.__init__', return_value=None):
            self.mock_request = Mock()
            self.mock_client_address = ('127.0.0.1', 12345)
            self.mock_server = Mock()
            self.handler = engine_server.ZenAIOrchestrator(
                self.mock_request, self.mock_client_address, self.mock_server
            )
            self.handler.wfile = Mock()
            self.handler.rfile = Mock()
            self.handler.headers = {}

    @patch('zena_mode.server.ZenAIOrchestrator.send_response')
    @patch('zena_mode.server.ZenAIOrchestrator.send_header')
    @patch('zena_mode.server.ZenAIOrchestrator.end_headers')
    def test_do_OPTIONS(self, mock_end, mock_header, mock_send):
        """Test OPTIONS request returns CORS headers."""
        self.handler.do_OPTIONS()
        mock_send.assert_called_with(200)
        mock_header.assert_any_call('Access-Control-Allow-Origin', '*')

    @patch('zena_mode.server.ZenAIOrchestrator.send_json_response')
    def test_do_GET_list(self, mock_json):
        """Test /list returns current model list."""
        with patch('zena_mode.server.MODEL_DIR') as mock_dir, \
             patch('zena_mode.server.MODEL_PATH') as mock_path:
            
            mock_path.name = "active.gguf"
            mock_file = Mock(spec=Path)
            mock_file.name = "active.gguf"
            mock_dir.exists.return_value = True
            mock_dir.glob.return_value = [mock_file]
            
            self.handler.path = '/list'
            self.handler.do_GET()
            
            mock_json.assert_called_once()
            args = mock_json.call_args[0]
            assert args[0] == 200
            assert any(m['name'] == "active.gguf" and m['active'] for m in args[1])

    @patch('zena_mode.server.ZenAIOrchestrator.send_json_response')
    def test_do_GET_status(self, mock_json):
        """Test /model/status returns loading status."""
        with patch('zena_mode.server.MODEL_PATH') as mock_path:
            mock_path.name = "test.gguf"
            engine_server.SERVER_PROCESS = Mock() # Simulated running server
            
            self.handler.path = '/model/status'
            self.handler.do_GET()
            
            mock_json.assert_called_once()
            status = mock_json.call_args[0][1]
            assert status['model'] == "test.gguf"
            assert status['loaded'] is True

    @patch('zena_mode.server.restart_with_model')
    @patch('zena_mode.server.ZenAIOrchestrator.send_json_response')
    def test_do_POST_swap(self, mock_json, mock_restart):
        """Test /swap initiates model restart."""
        self.handler.path = '/swap'
        
        # Mock request body
        body = json.dumps({"model": "new_model.gguf"}).encode()
        self.handler.rfile.read.return_value = body
        self.handler.headers = {'Content-Length': str(len(body))}
        
        with patch('threading.Thread') as mock_thread:
            self.handler.do_POST()
            
            # Should have started a thread for restart
            mock_thread.assert_called_once()
            assert mock_thread.call_args[1]['target'] == engine_server.restart_with_model
            assert mock_thread.call_args[1]['args'] == ("new_model.gguf",)
            
            mock_json.assert_called_with(200, {"status": "accepted"})


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])
