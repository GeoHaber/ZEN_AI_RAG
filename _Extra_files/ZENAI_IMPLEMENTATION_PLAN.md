# ZenAI Project Implementation Plan

## Block Diagram

```
+-------------------+         +-------------------+         +-------------------+
|                   |  REST   |                   |  Async  |                   |
|   Orchestrator    +-------->+   Async Backend   +-------->+      LLM/RAG      |
|  (start_llm.py)   |  API    | (async_backend.py)|  Calls  | (llama.cpp, RAG)  |
+-------------------+         +-------------------+         +-------------------+
        |                           ^                               ^
        | Subprocess                | Streaming                     |
        v                           | Responses                     |
+-------------------+         +-------------------+         +-------------------+
|                   |  Web    |                   |  UI     |                   |
|     Frontend      +<--------+   UI Components   +<--------+   Config/Security |
|    (zena.py)      | Socket  | (ui_components.py)|  Events | (config_system.py |
+-------------------+         +-------------------+         +-------------------+
```

## Implementation Steps

1. **Map Orchestrator Logic**
   - Review and document process management, hardware profiling, and API endpoints in start_llm.py.
2. **Document Async Backend**
   - Summarize async model management, streaming, and error handling in async_backend.py.
3. **Summarize RAG & Model Pipeline**
   - Document model discovery, download, hot-swap, and RAG transparency.
4. **Analyze Main UI & Components**
   - Map chat, RAG, file upload, and modular UI logic in zena.py and ui_components.py.
5. **Map Frontend UX & Localization**
   - Document multilingual support, RAG cues, and user experience flows.
6. **Review Config & Security**
   - Summarize configuration, file validation, and security checks.
7. **Review & Expand Tests**
   - Ensure all critical paths and new features are covered by tests.
8. **Check Compliance**
   - Validate all logic against the master spec; document and address any gaps.
9. **Break Down Planned Features**
   - Create actionable tasks for popup UI, pulsing trigger, multilingual voice, website RAG, etc.

## Next Steps
- Proceed through each step in order, updating documentation and code as needed.
- Use the block diagram as a reference for system interactions and responsibilities.
- Prioritize transparency, security, and async/non-blocking design throughout.
