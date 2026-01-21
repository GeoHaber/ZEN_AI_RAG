"""
test_model_management.py
TDD Test: Verify model selection and download API integration.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock

class TestModelManagement(unittest.TestCase):
    
    def test_get_models_from_hub_api(self):
        """Test that NebulaBackend.get_models() fetches from Hub API (port 8002)."""
        with patch('zena.requests.get') as mock_get:
            # Mock successful API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": ["qwen2.5-coder-7b.gguf", "llama-3.2-3b.gguf"]
            }
            mock_get.return_value = mock_response
            
            # Import and test
            with patch('zena.ui'):
                import zena
                backend = zena.NebulaBackend()
                models = backend.get_models()
                
                # Verify API was called
                mock_get.assert_called_once()
                call_args = mock_get.call_args[0][0]
                self.assertIn("8002", call_args, "Should call Hub API on port 8002")
                
                # Verify models returned
                self.assertIsInstance(models, list)
                self.assertEqual(len(models), 2)
                print(f"✓ get_models() returned: {models}")
    
    def test_get_models_fallback_on_error(self):
        """Test that get_models() returns fallback list if Hub API fails."""
        with patch('zena.requests.get') as mock_get:
            # Mock API failure
            mock_get.side_effect = Exception("Connection refused")
            
            with patch('zena.ui'):
                import zena
                backend = zena.NebulaBackend()
                models = backend.get_models()
                
                # Should return fallback list
                self.assertIsInstance(models, list)
                self.assertTrue(len(models) > 0, "Should return fallback models on error")
                print(f"✓ Fallback models: {models}")

if __name__ == '__main__':
    unittest.main(verbosity=2)
