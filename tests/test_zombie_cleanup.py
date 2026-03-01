"""
TDD: Zombie Cleanup and Port Conflict Resolution
===============================================
Tests that start_llm.py can handle "zombie" processes and port conflicts.
"""
import pytest
import os
import sys
import socket
import psutil
import time
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import start_llm
from utils import is_port_active

class TestZombieCleanup:
    """Tests for identifying and resolving zombie/orphan processes."""

    def test_kill_process_by_port_works(self):
        """TDD: Verify we can kill a process given only its port."""
        # 1. Start a separate dummy listener on a high port
        test_port = 9999
        # Small python script that just listens on a port
        script = f"import socket, time; s=socket.socket(); s.bind(('127.0.0.1', {test_port})); s.listen(1); time.sleep(10)"
        proc = subprocess.Popen([sys.executable, "-c", script])
        
        # Wait for port to activate
        time.sleep(1)
        assert is_port_active(test_port) is True
        
        # 2. Call the cleanup utility
        from utils import kill_process_by_port
        kill_process_by_port(test_port)
        
        # Give OS a moment to release
        time.sleep(1)
        
        # 3. Verify port is now free
        assert is_port_active(test_port) is False
        
        # Cleanup (if still alive)
        try: proc.kill()
        except Exception: pass

    def test_start_server_cleanup_logic(self):
        """TDD: Verify start_server() cleans up port BEFORE launching."""
        # This tests the 'Fix' we intend to implement
        with patch('start_llm.kill_process_by_port') as mock_kill_port, \
             patch('start_llm.kill_process_by_name') as mock_kill_name, \
             patch('start_llm.subprocess.Popen') as mock_popen, \
             patch('start_llm.register_process'), \
             patch('start_llm.MODEL_PATH') as mock_path, \
             patch('start_llm.SERVER_EXE') as mock_exe:
            
            mock_path.exists.return_value = True
            mock_exe.exists.return_value = True
            mock_popen.return_value.poll.return_value = None # Still running
            
            # We need to break the infinite loop in start_server
            # by making poll() return something after first check
            mock_popen.return_value.poll.side_effect = [None, 0] 
            mock_popen.return_value.communicate.return_value = (b"mock out", b"mock err")
            
            try:
                # We expect start_server to try to kill old instances on port 8001
                # if we add that logic.
                with patch('sys.argv', ['start_llm.py', '--guard-bypass']):
                    start_llm.start_server()
            except SystemExit:
                pass
            
            # AT LEAST one of these should be called to prevent port collision
            # Our goal is to ensure kill_process_by_port(8001) happens.
            assert mock_kill_port.called or mock_kill_name.called

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
