
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from zena_mode.swarm_arbitrator import SwarmArbitrator

# Helper for async iteration
class AsyncIterator:
    """AsyncIterator class."""
    def __init__(self, items):
        self.items = iter(items)
    def __aiter__(self):
        return self
    async def __anext__(self):
        """Anext."""
        try:
            return next(self.items)
        except StopIteration:
            raise StopAsyncIteration

class TestTrafficController(unittest.IsolatedAsyncioTestCase):
    """TestTrafficController class."""
    def setUp(self):
        """Setup."""
        self.arbitrator = SwarmArbitrator(config={"enabled": True})
        # Mock endpoints
        self.arbitrator.endpoints = [
            "http://local:8001/v1/chat/completions",
            "http://expert:8005/v1/chat/completions"
        ]
        self.arbitrator.host = "127.0.0.1"

    async def test_traffic_controller_easy(self):
        """Test that easy queries stay on fast LLM"""
        # Mock difficulty evaluation to return EASY + HIGH CONFIDENCE
        mock_eval = {
            "difficulty": "easy",
            "confidence": 0.95,
            "reasoning": "Simple factual question"
        }
        
        with patch.object(self.arbitrator, '_evaluate_query_difficulty', new_callable=AsyncMock) as mock_diff:
            mock_diff.return_value = mock_eval
            
            # Mock LLM stream
            with patch.object(self.arbitrator, '_stream_from_llm') as mock_stream:
                mock_stream.return_value = AsyncIterator(["Fast response"])
                
                # Execute
                responses = []
                async for chunk in self.arbitrator._traffic_controller_mode("What is 2+2?"):
                    responses.append(chunk)
                
                # Verify
                full_resp = "".join(responses)
                self.assertIn("💨 **Fast response**", full_resp)
                # Ensure it called the FIRST endpoint (Fast LLM)
                mock_stream.assert_called_with(
                    self.arbitrator.endpoints[0], 
                    "What is 2+2?", 
                    "You are a helpful AI assistant."
                )

    async def test_traffic_controller_hard(self):
        """Test that hard queries go to expert LLM"""
        # Mock difficulty evaluation to return HARD
        mock_eval = {
            "difficulty": "hard",
            "confidence": 0.4,
            "reasoning": "Complex reasoning required"
        }
        
        with patch.object(self.arbitrator, '_evaluate_query_difficulty', new_callable=AsyncMock) as mock_diff:
            mock_diff.return_value = mock_eval
            
            with patch.object(self.arbitrator, '_stream_from_llm') as mock_stream:
                mock_stream.return_value = AsyncIterator(["Expert response"])
                
                responses = []
                async for chunk in self.arbitrator._traffic_controller_mode("Prove P=NP"):
                    responses.append(chunk)
                
                full_resp = "".join(responses)
                self.assertIn("🚀 **Expert routing**", full_resp)
                # Ensure it called the SECOND endpoint (Expert LLM)
                mock_stream.assert_called_with(
                    self.arbitrator.endpoints[1], 
                    "Prove P=NP", 
                    "You are a helpful AI assistant."
                )

if __name__ == '__main__':
    unittest.main()
