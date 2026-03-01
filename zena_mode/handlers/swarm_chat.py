
import logging
from zena_mode.handlers.base import BaseZenHandler
from zena_mode.swarm_arbitrator import SwarmArbitrator, ArbitrationRequest, TaskType

logger = logging.getLogger("ZenAI.Handler.SwarmChat")

class SwarmChatHandler:
    """
    Advanced handler for Multi-LLM Consensus ("The Council").
    Routes prompts to the SwarmArbitrator for debate and synthesis.
    """
    
    def __init__(self):
        """Initialize instance."""
        # Initialize Arbitrator with discovery enabled
        self.arbitrator = SwarmArbitrator(config={
            "enabled": True,
            "size": 3,
            "min_experts": 1,
            "timeout_per_expert": 15.0
        })
        
    async def initialize(self):
        """Async discovery of swarm experts."""
        await self.arbitrator.discover_swarm()

    async def handle_post_async(self, handler: BaseZenHandler) -> bool:
        """
        Async handler for /api/chat/swarm
        """
        if handler.path != '/api/chat/swarm':
            return False

        try:
            params = handler.parse_json_body()
            user_msg = params.get('message', '')
            
            if not user_msg:
                handler.send_json_response(400, {"error": "Missing message"})
                return True

            logger.info(f"🧠 [Council] Convening for: {user_msg[:50]}...")
            
            import uuid
            # Create Request
            request = ArbitrationRequest(
                id=str(uuid.uuid4()),
                query=user_msg,
                task_type=TaskType.REASONING.value
            )
            
            # Execute Consensus
            # This runs the full debate: Broadcast -> Collect -> Synthesize
            result = await self.arbitrator.arbiter_decision(request)
            
            response_payload = {
                "response": result["consensus_answer"],
                "experts": result["individual_responses"],
                "meta": {
                    "method": result["method"],
                    "confidence": result["confidence"],
                    "duration": result["duration"]
                }
            }
            
            handler.send_json_response(200, response_payload)
            return True

        except Exception as e:
            logger.error(f"Council Error: {e}", exc_info=True)
            handler.send_json_response(500, {"error": str(e)})
            return True

# Singleton
_swarm_handler = None

async def get_swarm_handler():
    """Get swarm handler."""
    global _swarm_handler
    if _swarm_handler is None:
        _swarm_handler = SwarmChatHandler()
        await _swarm_handler.initialize()
    return _swarm_handler
