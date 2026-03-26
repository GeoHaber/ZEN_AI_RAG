"""
server — Split modules for api_server.py

Sub-packages:
  schemas    — Pydantic request/response models + InferenceRequest
  state      — ResponseCache, ServerState, SwapTracker
  helpers    — Utility functions shared across routers
  hardware   — Hardware detection and GPU presets
  routing    — Domain/difficulty classification, strategies, RAG-aware routing
  feedback   — FeedbackCollector
  routers/   — FastAPI APIRouter modules
"""
