# -*- coding: utf-8 -*-
"""
model_orchestrator.py - Intelligent Traffic Control for ZenAI V2
Routes user requests to specialized expert models based on intent and resources.
"""

import logging
from typing import Optional, AsyncGenerator
from .resource_manager import resource_manager

logger = logging.getLogger("Orchestrator")


class ModelOrchestrator:
    """
    Traffic Controller for ZenAI.
    - Uses a lightweight model (Qwen 2.5-3B) to classify intent.
    - Routes to experts (DeepSeek for Code, Llama for Chat, Qwen-Audio for Voice).
    - Manages model lifecycle via ResourceManager.
    """

    def __init__(self, backend):
        """Initialize instance."""
        self.backend = backend
        self.current_model = None
        self.router_model = "qwen2.5-3b-instruct-q5_k_m.gguf"  # Lightweight Router

        # Expert Registry
        self.experts = {
            "CODE": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
            "CHAT": "llama-3.2-3b.gguf",
            "VOICE": "qwen2-audio-7b-instruct.gguf",
        }

    async def _ensure_model(self, model_name: str):
        """Ensure the requested model is loaded, respecting RAM strategy."""
        if self.current_model == model_name:
            return

        strategy = resource_manager.strategy
        logger.info(f"[Orchestrator] Switching to {model_name} (Strategy: {strategy})")

        # In SERIAL mode, we might want to explicitly unload/gc before loading
        # But for now we rely on the backend's load function to handle basic swapping

        success = await self.backend.set_active_model(model_name)
        if success:
            self.current_model = model_name
        else:
            logger.error(f"[Orchestrator] Failed to load {model_name}")
            raise RuntimeError(f"Could not load expert: {model_name}")

    async def route_and_execute(self, user_input: str, system_prompt: str) -> AsyncGenerator[str, None]:
        """
        Main entry point:
        1. (Optional) Analyze intent using Router Model
        2. Load best Expert
        3. Stream response
        """

        # 1. Intent Analysis (Simplified for V2 Alpha)
        # In full version, we'd load self.router_model, ask it to classify, then switch.
        # For efficiency in this initial implementation, we'll use heuristic routing + lightweight router if needed.

        intent = self._heuristic_intent(user_input)
        expert_model = self.experts.get(intent, self.experts["CHAT"])

        logger.info(f"[Orchestrator] Intent: {intent} -> Model: {expert_model}")

        # 2. Switch to Expert
        await self._ensure_model(expert_model)

        # 3. Stream from Expert
        async for chunk in self.backend.send_message_async(user_input, system_prompt):
            yield chunk

    def _heuristic_intent(self, text: str) -> str:
        """Lightweight heuristic to save Router calls for obvious cases."""
        text_lower = text.lower()

        # Coding triggers
        if any(w in text_lower for w in ["code", "python", "function", "debug", "script", "json", "api"]):
            return "CODE"

        # Voice triggers (handled separately usually, but good to have)
        if any(w in text_lower for w in ["speak", "say", "voice", "audio"]):
            return "VOICE"

        return "CHAT"

    async def generate_voice(self, text: str, emotion: str = "Neutral") -> Optional[bytes]:
        """
        Generate audio using Qwen2-Audio.
        This is a specialized pipeline that loads the audio model.
        """
        logger.info(f"[Orchestrator] Generating Voice ({emotion})...")

        try:
            # 1. Load Audio Expert
            await self._ensure_model(self.experts["VOICE"])

            # 2. Send instruction to model (Hypothetical API for Qwen-Audio)
            # In a real implementation, this would hit a specific /v1/audio/generations endpoint of the backend
            # For now, we mock the switch logic which is the architectural goal.

            logger.info("[Orchestrator] Voice generation simulated (Model Loaded)")
            return b"WAV_DATA_PLACEHOLDER"

        except Exception as e:
            logger.error(f"[Orchestrator] Voice generation failed: {e}")
            return None


# Factory
def get_orchestrator(backend):
    return ModelOrchestrator(backend)
