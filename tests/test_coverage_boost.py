import pytest
import os
import sys
import subprocess
import signal
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import subjects
import zena_mode.server as server
import utils

class TestCoverageBoost:
    """Tests to cover remaining logic in start_llm.py to reach 80% coverage."""

    def test_env_int(self):
        """Test env_int utility."""
        os.environ["TEST_ENV_INT"] = "42"
        assert server.env_int("TEST_ENV_INT", 10) == 42
        assert server.env_int("NON_EXISTENT", 10) == 10
        os.environ["TEST_ENV_INVALID"] = "not_an_int"
        assert server.env_int("TEST_ENV_INVALID", 10) == 10

    @patch('zena_mode.server.psutil.process_iter')
    def test_check_processes(self, mock_iter):
        """Test check_processes logic."""
        mock_proc = Mock()
        mock_proc.name.return_value = "test-proc"
        mock_proc.poll.return_value = 1 # Crashed
        
        server.MONITORED_PROCESSES.clear()
        server.register_process("Test", mock_proc, critical=True)
        
        crashed = server.check_processes()
        assert len(crashed) == 1
        assert crashed[0][0] == "Test"

    @patch('utils.psutil.pid_exists')
    @patch('utils.psutil.Process')
    def test_kill_process_tree(self, mock_proc_class, mock_exists):
        """Test recursive process killing."""
        mock_exists.return_value = True
        mock_child = Mock()
        mock_parent = Mock()
        mock_parent.children.return_value = [mock_child]
        mock_proc_class.return_value = mock_parent
        
        utils.kill_process_tree(1234)
        
        mock_child.terminate.assert_called_once()
        mock_parent.terminate.assert_called_once()

    @patch('utils.psutil.process_iter')
    def test_kill_process_by_name(self, mock_iter):
        """Test killing processes by filename."""
        mock_proc = Mock()
        mock_proc.info = {'pid': 9999, 'name': 'target.exe'}
        mock_iter.return_value = [mock_proc]
        
        utils.kill_process_by_name("target.exe")
        mock_proc.terminate.assert_called_once()

    def test_register_process_updates_globals(self):
        """Test register_process correctly populates tracking structures."""
        server.MONITORED_PROCESSES.clear()
        mock_p = Mock()
        server.register_process("Unit-Test-Proc", mock_p, critical=False)
        assert "Unit-Test-Proc" in server.MONITORED_PROCESSES
        assert not server.MONITORED_PROCESSES["Unit-Test-Proc"]["critical"]

    @patch('zena_mode.server.subprocess.Popen')
    def test_launch_expert_process_env(self, mock_popen):
        """Test expert launch passes correct environment."""
        with patch('zena_mode.server.MODEL_PATH') as mock_path:
            mock_path.exists.return_value = True
            server.launch_expert_process(9000, 4)
            
            args, kwargs = mock_popen.call_args
            assert kwargs['env']['LLM_PORT'] == "9000"
            assert kwargs['env']['LLM_THREADS'] == "4"

    @patch('zena_mode.server.launch_expert_process')
    @patch('zena_mode.server.kill_process_tree')
    def test_scale_swarm_integration(self, mock_kill, mock_launch):
        """Test scaling logic handles increase and decrease."""
        server.EXPERT_PROCESSES.clear()
        
        # Scale up
        server.scale_swarm(2)
        assert mock_launch.call_count == 2
        
        # Mock running experts
        server.EXPERT_PROCESSES[8005] = Mock(pid=1)
        server.EXPERT_PROCESSES[8006] = Mock(pid=2)
        
        # Scale down
        server.scale_swarm(1)
        assert mock_kill.call_count == 1
        assert len(server.EXPERT_PROCESSES) == 1

    @patch('zena_mode.server.ThreadingHTTPServer')
    def test_start_hub_daemon(self, mock_server):
        """Test management API starts in background thread."""
        with patch('threading.Thread') as mock_thread:
            server.start_hub()
            mock_thread.assert_called_once()
            assert mock_thread.call_args[1]['daemon'] is True

    @patch('zena_mode.server.asyncio.run')
    def test_start_voice_stream_server(self, mock_run):
        """Test voice stream server starts in thread."""
        with patch('zena_mode.server.websockets', True, create=True), \
             patch('threading.Thread') as mock_thread:
            server.start_voice_stream_server()
            mock_thread.assert_called_once()

    @patch('zena_mode.server.Path.exists')
    @patch('zena_mode.server.subprocess.Popen')
    def test_start_server_guard_bypass(self, mock_popen, mock_exists):
        """Test start_server logic when guard is bypassed."""
        mock_exists.return_value = True
        with patch('sys.argv', ["start_llm.py", "--guard-bypass"]), \
             patch('zena_mode.server.start_hub'), \
             patch('zena_mode.server.start_voice_stream_server'), \
             patch('zena_mode.server.kill_zombie_process'), \
             patch('zena_mode.server.kill_process_by_name'), \
             patch('zena_mode.server.is_port_active', return_value=True), \
             patch('zena_mode.server.check_processes', side_effect=[[], [("LLM-Server", 1, True)]]):
            
            # Use side_effect on poll to break the loop
            mock_proc = MagicMock()
            mock_proc.poll.side_effect = [None, 1] 
            mock_proc.communicate.return_value = (b"mock output", b"mock error")
            mock_popen.return_value = mock_proc
            
            # We need to swallow the sys.exit if break happens
            try:
                server.start_server()
            except SystemExit:
                pass
            
            assert mock_popen.call_count >= 1
            # Verify hub was NOT called if guard-bypass is present? 
            # Wait, the code says: if "--guard-bypass" NOT in sys.argv: start_hub()
            # My mock argv HAS it, so it should NOT start hub.
            server.start_hub.assert_not_called()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
