# ZenAI Development Roadmap & TODO

> Last Updated: January 2026

## 🎯 Priority Legend
- 🔴 **Critical** - Blocking issues / Security
- 🟠 **High** - Important features / Performance
- 🟡 **Medium** - Quality of life improvements
- 🟢 **Low** - Nice to have / Future

---

## 🛠️ ENVIRONMENT & HARDWARE VALIDATION (NEW)

### 🔴 High-Reliability Orchestration
- [x] Implement proactive port cleanup (kill Port 8001 zombie processes)
- [x] Add startup health-check loop (Wait for binding + crash capture)
- [x] Capture and log `llama-server.exe` stderr to `nebula_engine.log`
- [ ] Implement CPU Capability Detection (AVX2, AVX512, FMA) to suggest optimal binaries
- [ ] Audit background jobs that might interfere (Duplicate Python instances, high-CPU tasks)
- [ ] Add RAM & GPU VRAM availability checks with "Safe Launch" warnings

### 🟠 Swarm Parity & Ethics
- [x] respect `robots.txt` in real-time scraping
- [x] Implement "Pre-flight Crawlability Report" for user feedback
- [x] Automated "Refuse All" cookie banner/modal stripping
- [x] Anti-bot detection (Cloudflare, LinkedIn, Akamai) with difficulty scoring

---

## 🧪 TESTING IMPROVEMENTS

### 🔴 Automated UI Testing (E2E)
Since we know element locations and functions, create automated tests that simulate real user workflows:

```python
# Proposed: tests/test_ui_e2e.py
class UIElement:
    """Registry of UI elements with their selectors and expected behaviors."""
    SEND_BUTTON = {"selector": "button[icon='arrow_upward']", "action": "click", "wait_for": "response"}
    USER_INPUT = {"selector": "input[placeholder*='Message']", "action": "type"}
    CHAT_LOG = {"selector": ".chat-scroll-area", "expected": "contains messages"}
    # ... etc
```

**Tasks:**
- [ ] Create UI element registry with CSS selectors and Quasar component IDs
- [ ] Build Playwright/Selenium test harness for NiceGUI
- [ ] Test flows: Send message → Wait for response → Verify display
- [ ] Test flows: Upload file → Process → Verify attachment
- [ ] Test flows: Toggle dark mode → Verify CSS changes
- [ ] Add screenshot comparison for visual regression
- [ ] CI/CD integration for automated E2E tests

### 🟠 Response Validation Tests
Test expected LLM responses against known inputs:

```python
# Proposed structure
@pytest.mark.llm_response
async def test_greeting_response():
    response = await send_and_collect("Hello, who are you?")
    assert "ZenAI" in response or "assistant" in response.lower()
    assert "ChatGPT" not in response  # Identity check
```

**Tasks:**
- [ ] Create mock LLM backend for deterministic testing
- [ ] Build response pattern matchers (regex, keyword, sentiment)
- [ ] Test identity prompts (ZenAI should NOT say it's ChatGPT)
- [ ] Test RAG responses include source citations
- [ ] Test streaming chunk assembly integrity

### 🟡 Performance Benchmarks as Tests
- [ ] Add `pytest-benchmark` for critical paths
- [ ] Benchmark: RAG search latency (<100ms for k=5)
- [ ] Benchmark: Message render time (<50ms)
- [ ] Benchmark: File upload processing (<2s for 5MB)
- [ ] Track regressions in CI

---

## 💬 CONVERSATION MEMORY (NEW)

### 🟠 Integration with Main App
Connect `conversation_memory.py` to `zena.py`:

**Tasks:**
- [ ] Initialize ConversationMemory in app startup
- [ ] Store user messages with `memory.add_message("user", text)`
- [ ] Store assistant responses with `memory.add_message("assistant", response)`
- [ ] Inject history context into prompts for follow-up questions
- [ ] Add "What did we discuss?" capability

### 🟡 LLM-Based Summarization
- [ ] Trigger auto-summarization after 50 messages
- [ ] Store summaries in separate index
- [ ] Use summaries for long-term context recall
- [ ] Allow user to request "Summarize our conversation"

### 🟡 Multi-Session Support
- [ ] Generate unique session IDs per browser tab
- [ ] Allow session switching in UI
- [ ] Session persistence across browser refreshes
- [ ] Export/import conversation history

---

## 🔍 RAG IMPROVEMENTS

### 🟠 Hybrid Search Tuning
- [ ] Experiment with alpha values (semantic vs keyword balance)
- [ ] Implement query expansion using LLM
- [ ] Add re-ranking step using cross-encoder
- [ ] Filter low-confidence results

### 🟡 Source Attribution
- [ ] Track which chunks were used in response
- [ ] Show confidence scores for each source
- [ ] Allow user to filter by source quality
- [ ] Implement "Show me the original" feature

### 🟢 Advanced Chunking
- [ ] Semantic chunking (split at topic boundaries)
- [ ] Overlapping context windows
- [ ] Document structure awareness (headers, lists)
- [ ] Code-aware chunking for programming docs

---

## 🎨 UI/UX IMPROVEMENTS

### 🟠 Chat Experience
- [ ] Message editing (edit last message)
- [ ] Message deletion
- [ ] Copy message button
- [ ] Regenerate response button
- [ ] Stop generation button (cancel stream)

### 🟡 Accessibility
- [ ] Keyboard navigation (Tab, Enter, Esc)
- [ ] Screen reader support (ARIA labels)
- [ ] High contrast mode
- [ ] Font size controls

### 🟡 Mobile Responsiveness
- [ ] Test on mobile viewports
- [ ] Touch-friendly button sizes
- [ ] Swipe gestures for sidebar
- [ ] Virtual keyboard handling

### 🟢 Advanced Features
- [ ] Code syntax highlighting in responses
- [ ] Markdown rendering improvements
- [ ] Image display from RAG sources
- [ ] File preview in attachment area

---

## ⚡ PERFORMANCE OPTIMIZATIONS

### 🟠 Streaming Improvements
- [ ] Reduce chunk render latency
- [ ] Batch UI updates (debounce)
- [ ] WebSocket optimization for faster delivery
- [ ] Progressive rendering for long responses

### 🟡 Memory Management
- [ ] Limit in-memory message history
- [ ] Lazy load old conversations
- [ ] Clear old FAISS indexes periodically
- [ ] Monitor and log memory usage

### 🟡 Startup Time
- [ ] Lazy load embedding models
- [ ] Background index loading
- [ ] Cache compiled Tailwind CSS
- [ ] Optimize import chain

---

## 🔒 SECURITY ENHANCEMENTS

### 🔴 Input Sanitization
- [x] Path traversal prevention (FileValidator)
- [ ] XSS prevention in displayed content
- [ ] SQL injection prevention (parameterized queries ✓)
- [ ] Rate limiting for API endpoints

### 🟠 Authentication
- [ ] Optional user authentication
- [ ] Session tokens for multi-user
- [ ] API key management for external LLMs
- [ ] Secure settings storage

---

## 🤖 LLM/MODEL IMPROVEMENTS

### 🟠 Multi-Model Support
- [ ] Hot-swap between loaded models
- [ ] Model comparison mode (side-by-side)
- [ ] Auto-select model based on task type
- [ ] Model-specific prompt templates

### 🟡 Prompt Engineering
- [ ] System prompt customization UI
- [ ] Prompt templates library
- [ ] Chain-of-thought toggles
- [ ] Temperature/creativity controls

### 🟢 External API Support
- [ ] OpenAI API compatibility
- [ ] Anthropic Claude support
- [ ] Azure OpenAI integration
- [ ] Ollama remote connection

---

## 📊 OBSERVABILITY

### 🟡 Logging & Monitoring
- [ ] Structured JSON logging
- [ ] Request/response tracing
- [ ] Performance metrics dashboard
- [ ] Error alerting

### 🟢 Analytics
- [ ] Usage statistics
- [ ] Popular queries tracking
- [ ] Response quality metrics
- [ ] RAG hit/miss rates

---

## 🧹 CODE QUALITY

### 🟡 Refactoring
- [ ] Split `zena.py` into smaller modules
- [ ] Standardize error handling patterns
- [ ] Complete type hints coverage
- [ ] Docstring coverage >80%

### 🟡 Testing Coverage
- [ ] Achieve 80% code coverage
- [ ] Mock external dependencies
- [ ] Integration test suite
- [ ] Load/stress testing

---

## 📝 DOCUMENTATION

### 🟡 User Documentation
- [ ] Getting started guide
- [ ] Configuration reference
- [ ] Troubleshooting FAQ
- [ ] Video tutorials

### 🟢 Developer Documentation
- [ ] Architecture overview
- [ ] API documentation
- [ ] Contributing guide
- [ ] Plugin/extension system

---

## 🚀 DEPLOYMENT

### 🟢 Packaging
- [ ] Docker container
- [ ] Windows installer (NSIS/MSI)
- [ ] PyPI package
- [ ] One-click setup script

### 🟢 Cloud Deployment
- [ ] Azure deployment template
- [ ] AWS Lambda support
- [ ] Kubernetes manifests
- [ ] Auto-scaling configuration

---

## 📅 Release Milestones

### v1.1 (Q1 2026)
- [ ] Conversation memory integration
- [ ] Automated UI tests (basic)
- [ ] Response validation tests
- [ ] Bug fixes from v1.0

### v1.2 (Q2 2026)
- [ ] Multi-model support
- [ ] Enhanced RAG with re-ranking
- [ ] Mobile responsive UI
- [ ] Performance optimizations

### v2.0 (Q3 2026)
- [ ] Plugin system
- [ ] External API support
- [ ] Cloud deployment options
- [ ] Enterprise features

---

## 💡 Ideas Backlog

These are ideas that need more investigation:

1. **Voice conversation mode** - Full duplex audio chat
2. **Agent system** - Multi-step task execution
3. **Knowledge graph** - Entity relationship visualization
4. **Collaborative editing** - Multiple users in same session
5. **Offline mode** - Full functionality without internet
6. **Custom model fine-tuning** - Train on user data
7. **Browser extension** - RAG over current webpage
8. **Desktop widgets** - Quick access chat bubble

---

## 🐛 Known Issues

Track bugs that need fixing:

| Issue | Severity | Status | Notes |
|-------|----------|--------|-------|
| ~~Chat scroll not showing messages~~ | 🔴 | ✅ Fixed | calc(100vh-200px) |
| ~~Timeout on large files~~ | 🟠 | ✅ Fixed | 300s timeout |
| ~~Dark mode not syncing~~ | 🟡 | ✅ Fixed | JS syncDarkMode() |
| | | | |

---

## Contributing

To contribute:
1. Pick an item from TODO
2. Create feature branch: `feature/item-name`
3. Implement with tests
4. Submit PR with description

Priority: Focus on 🔴 Critical and 🟠 High items first.
