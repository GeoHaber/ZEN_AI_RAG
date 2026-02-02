"""
test_model_management.py
Verification of model selection and download API integration with AsyncZenAIBackend.
"""
import unittest
import sys
import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestModelManagement(unittest.TestCase):
    
    def test_get_models_from_hub_api(self):
        """Test that AsyncZenAIBackend.get_models() fetches from Hub API via httpx."""
        # Mock httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["qwen2.5-coder-7b.gguf", "llama-3.2-3b.gguf"]
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_response
        
        with patch('httpx.AsyncClient', return_value=mock_client), \
             patch('zena.ui'):
            import zena
            backend = zena.AsyncZenAIBackend()
            models = asyncio.run(backend.get_models())
            
            # Verify API was called
            mock_client.get.assert_called_once()
            call_url = mock_client.get.call_args[0][0]
            self.assertIn("8002", call_url, "Should call Hub API on port 8002")
            
            # Verify models returned
            self.assertIsInstance(models, list)
            self.assertEqual(len(models), 2)
            print(f"✓ get_models() returned: {models}")
    
    def test_get_models_fallback_on_error(self):
        """Test that get_models() returns fallback list if Hub API fails."""
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.side_effect = Exception("Connection refused")
        
        with patch('httpx.AsyncClient', return_value=mock_client), \
             patch('zena.ui'):
            import zena
            backend = zena.AsyncZenAIBackend()
            models = asyncio.run(backend.get_models())
            
            # Should return fallback list
            self.assertIsInstance(models, list)
            self.assertTrue(len(models) > 0, "Should return fallback models on error")
            print(f"✓ Fallback models: {models}")

if __name__ == '__main__':
    unittest.main(verbosity=2)
