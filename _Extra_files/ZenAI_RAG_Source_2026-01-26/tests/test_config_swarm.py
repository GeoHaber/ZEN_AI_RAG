# test_config_swarm.py
import unittest
import json
import os
from pathlib import Path
from config_system import AppConfig

class TestConfigSwarm(unittest.TestCase):
    def setUp(self):
        self.test_config_path = Path("test_config.json")
        if self.test_config_path.exists():
            os.remove(self.test_config_path)

    def tearDown(self):
        if self.test_config_path.exists():
            os.remove(self.test_config_path)

    def test_swarm_defaults(self):
        """Verify that swarm settings have correct defaults."""
        config = AppConfig()
        # These should FAIL initially as they are not yet implemented
        self.assertTrue(hasattr(config, "SWARM_SIZE"), "AppConfig missing SWARM_SIZE")
        self.assertTrue(hasattr(config, "SWARM_ENABLED"), "AppConfig missing SWARM_ENABLED")
        self.assertEqual(config.SWARM_SIZE, 3)
        self.assertEqual(config.SWARM_ENABLED, False)

    def test_swarm_persistence(self):
        """Verify that swarm settings persist after save/load."""
        config = AppConfig()
        config.SWARM_SIZE = 5
        config.SWARM_ENABLED = True
        config.to_json(self.test_config_path)

        # Load back
        new_config = AppConfig.from_json(self.test_config_path)
        self.assertEqual(new_config.SWARM_SIZE, 5)
        self.assertEqual(new_config.SWARM_ENABLED, True)

if __name__ == '__main__':
    unittest.main()
