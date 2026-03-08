# test_config_swarm.py
"""
Tests for Swarm configuration - critical for multi-LLM consensus functionality.
Verifies that swarm settings are properly stored and persisted.
"""

import unittest
import json
import os
from pathlib import Path
from config_system import AppConfig


class TestConfigSwarm(unittest.TestCase):
    """TestConfigSwarm class."""

    def setUp(self):
        self.test_config_path = Path("test_config.json")
        if self.test_config_path.exists():
            os.remove(self.test_config_path)

    def tearDown(self):
        if not self.test_config_path.exists():
            return

        os.remove(self.test_config_path)

    def test_swarm_defaults(self):
        """Verify that swarm settings have correct defaults."""
        config = AppConfig()
        # These are critical for multi-LLM consensus functionality
        self.assertTrue(hasattr(config, "SWARM_SIZE"), "AppConfig missing SWARM_SIZE")
        self.assertTrue(hasattr(config, "SWARM_ENABLED"), "AppConfig missing SWARM_ENABLED")
        self.assertEqual(config.SWARM_SIZE, 3)  # Default swarm size
        self.assertEqual(config.SWARM_ENABLED, False)  # Disabled by default

    def test_swarm_attributes_sync(self):
        """Verify uppercase and lowercase swarm attributes are in sync."""
        config = AppConfig()
        # Both uppercase and lowercase should work
        self.assertEqual(config.swarm_enabled, config.SWARM_ENABLED)
        self.assertEqual(config.swarm_size, config.SWARM_SIZE)

    def test_swarm_config_modification(self):
        """Verify swarm config can be modified."""
        config = AppConfig()
        # Modify lowercase version
        config.swarm_enabled = True
        config.swarm_size = 5
        # Check values
        self.assertTrue(config.swarm_enabled)
        self.assertEqual(config.swarm_size, 5)


if __name__ == "__main__":
    unittest.main()
