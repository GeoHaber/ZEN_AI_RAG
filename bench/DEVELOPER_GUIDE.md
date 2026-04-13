# RAG Test Bench — Developer Guide

This document exists to prevent regressions and protect the frontend codebase's fragile
single-script architecture. **Read this before editing `templates/index.html`.**

---

## ⚠️ Critical Rules for Editing `index.html`

### Rule 1 — The Entire App Lives in ONE `<script>` Tag

The frontend is a single-page application with **no build step**. All logic lives in a plain
`<script>` block near the bottom of `index.html`. If this block contains a **syntax error**,
the browser silently drops ALL JavaScript — every button, every rendering call, and every
pipeline card disappears with no obvious error visible on screen.

### Rule 2 — Always Verify Brace Balance After Any Edit

After every edit to `index.html`, run this check from the project root:

```bash
python -c "
import re
content = open('templates/index.html', encoding='utf-8').read()
scripts = list(re.finditer(r'<script>', content))
start = scripts[-1].start()
end = content.rfind('</script>')
js = content[start:end]
lines = js.splitlines()
stack, extra = [], []
for i, line in enumerate(lines):
    for char in line:
        if char == '{': stack.append(i+1)
        elif char == '}':
            if stack: stack.pop()
            else: extra.append(i+1)
print('Extra }:', extra)
print('Unclosed {:', stack[:5])
print('BALANCED!' if not extra and not stack else 'BROKEN — DO NOT DEPLOY')
"
```

✅ **Expected output:** `BALANCED!`
❌ **If you see** `BROKEN`: do not restart the server. Find and fix the brace first.

---

## Known Pitfalls (Lessons Learned)

### Pitfall A — Removing `fetch()` Without Removing Its `.catch()` Closure

**What happened:** `cancelCrawl()` originally used `fetch(API+'/api/crawl/cancel', ...)`.
It was refactored to be instant (no fetch needed). The `fetch()` call was deleted, but its
closing `.catch(function(e){...})` was left behind as an orphaned `}`. This produced one
extra `}` in the JS block, which broke ALL JavaScript on page load — pipelines disappeared.

**Rule:** When you remove a `fetch(...)` or any Promise chain, always remove the **entire
chain** including every `.then(...)` and `.catch(...)` that closes it.

---

### Pitfall B — One Too Many Closing Braces on a Single Line

**What happened:** When fixing `setPhase()` to add FAB-hiding logic, an automated edit
accidentally added an extra `}}}` instead of `}}`. This prematurely closed the entire
function, leaving the FAB-hide and `chat-mode` logic as dead unreachable code outside it.

**Rule:** On any dense single-line function (e.g., `if(el){...}}`), count every `{` and `}`
character — even ones on the same line — before accepting an edit.

---

### Pitfall C — The RAG Index Dimension Mismatch Crash

**What happened:** The saved `index_data/embeddings.npy` was built with a 96-dim model. After
switching to `all-MiniLM-L6-v2` (384-dim), the `TurboQuantIndex` crashed with:

```
ValueError: matmul: Input operand 1 has a mismatch in its core dimension 0
(size 96 is different from 384)
```

**Fix (already live):** `RAGIndex.load()` in `rag_index.py` now validates dimensions before
loading. If mismatched, it discards the old data safely with a warning log.

**Rule:** Never change `RAG_MODEL` without also clearing `index_data/` first.

---

### Pitfall D — Multiple `<script>` Tags in `index.html`

`index.html` contains **3 script tags**:
1. `<script type="module" src="/shared-ui/zen_chat.js">` — the Web Component loader
2. `<script>` — tiny DOMContentLoaded block (wires `zen-submit`/`zen-close` events)
3. `<script>` — **main app block** (~42,000+ chars) — this is the one that matters

Always target the **last** and **largest** `<script>` block when doing JS extraction/checks.

---

### Pitfall E — llm_config.json Leftover Test Values

**What happened:** `llm_config.json` had `"model": "test-model"` left from a previous test
run. The llama-server returned `500 Internal Server Error` for all pipelines because no model
named "test-model" existed.

**Fix:** Always make sure `llm_config.json` has a valid model name matching what is actually
**loaded** in the running llama-server instance. The file is read on every API request — no
server restart is needed after editing it.

**Rule:** After any LLM configuration change, use the **"Test LLM"** button in the Settings
drawer to verify the connection before running a chat query.

---

### Pitfall F — llama-server Ignores the `model` Field in Requests

**Important behavior:** `llama-server` loads **one model at startup** and always responds
with that model, regardless of what `model` name you send in the request body. The `model`
field in the JSON is accepted syntactically but **silently ignored** — the server always
answers with whatever `.gguf` file it was started with.

**How to switch models:** You must **restart the llama-server** with a different `--model` flag.
Changing `llm_config.json` or the Settings drawer `model` field only affects the display
name — it does not hot-swap the loaded model.

---

## Local Model Inventory (`C:\AI\Models`)

All models verified present as of 2026-04-02. Reference sizes shown.

| Model | File | Size | Notes |
|---|---|---|---|
| **Qwen2.5-Coder 14B** | `Qwen2.5-Coder-14B-Instruct-Q4_K_M.gguf` | 8.4 GB | Currently loaded at :8090 |
| **Qwen2.5 14B** | `Qwen2.5-14B-Instruct-Q4_K_M.gguf` | 8.4 GB | Strong general reasoning |
| **Gemma 4 E4B** | `gemma-4-E4B-it-Q4_K_M.gguf` | 4.6 GB | Google's newest local model (2025) |
| **Gemma 2 9B** | `gemma-2-9b-it-Q4_K_M.gguf` | 5.4 GB | Google, strong at instruction following |
| **DeepSeek-R1 14B** | `DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` | 8.4 GB | Reasoning model, best for complex Q&A |
| **Qwen3.5 9B** | `Qwen3.5-9B-Q4_K_M.gguf` | 5.3 GB | Good balance of speed vs quality |
| **Mistral 7B** | `Mistral-7B-Instruct-v0.3.Q4_K_M.gguf` | 4.1 GB | Fast, reliable |
| **Llama 3.2 3B** | `Llama-3.2-3B-Instruct-Q4_K_M.gguf` | 1.9 GB | Fast, lightweight |
| **Phi-3.5 Mini** | `Phi-3.5-mini-instruct-Q4_K_M.gguf` | 2.2 GB | Microsoft, very fast |

### Recommended Model for RAG Q&A

For Romanian municipality data (`primariatm.ro`, `oradea.ro`), best choices:
- **Qwen2.5 14B** — best instruction following for RAG with documents
- **DeepSeek-R1 14B** — best if you need step-by-step reasoning about retrieved content
- **Gemma 4 E4B** — worth testing, Google's newest, good multilingual support

---

## About Gemma 4

**Gemma 4 E4B** (`gemma-4-E4B-it-Q4_K_M.gguf`) is Google's latest open small model family
released in 2025. Key characteristics:

- **E4B = ~4 billion effective parameters** after efficiency techniques (MoE-like architecture)
- **Multilingual**: Specifically trained with strong Romanian, French, German and other EU language support — excellent fit for this project's use case
- **Instruction tuned**: The `-it` suffix confirms it's fine-tuned for chat/instruction following
- **Compact**: At 4.6 GB (Q4_K_M quantization), it runs well on consumer GPUs or CPU-only

**To use Gemma 4 in RAG Test Bench:**
1. Stop the current llama-server
2. Restart it with: `llama-server --model "C:\AI\Models\gemma-4-E4B-it-Q4_K_M.gguf" --port 8090`
3. In the Settings drawer → select preset **"Local: Gemma 4 E4B"**
4. Click **"Test LLM"** — should return a response
5. Run a chat query

> **Verified (2026-04-02):** The API at port 8090 returns HTTP 200 for the Gemma 4 model name,
> but the server was loaded with Qwen2.5-Coder at the time (see Pitfall F above). A full
> restart with the Gemma 4 file is required for real Gemma 4 inference.

---

## Running the Dev Server

```bash
# From rag-test-bench/
python app.py
# → http://localhost:5050
```

**Server restart required** when:
- `app.py` routes change (new Flask endpoints)
- Python backend code changes
- `rag_index.py` or any `zen_core_libs` Python changes

**Browser refresh sufficient** when:
- `templates/index.html` changes (Ctrl+R)
- `zen_core_libs/ui/zen_chat.js` changes (hard-refresh: **Ctrl+Shift+R** — clears JS cache)
- `llm_config.json` changes (read on each API call, no restart needed)

---

## Architecture Quick Reference

| Element ID | Purpose |
|---|---|
| `phase-setup` | The "Index a Website" screen (default active phase) |
| `phase-crawling` | Progress screen shown during RAG indexing |
| `phase-grade` | Website Grader report screen |
| `phase-chat` | The `<zen-chat>` component screen |
| `pipeGrid` | Filled by `renderPipeCards()` on page load from `/api/pipelines` |
| `hdrChip` | "X chunks" header pill — clickable → calls `maybeClearIdx()` |
| `fabAdd` / `fabSearch` | Floating buttons — always hidden (set to `display:none` in `setPhase`) |
| `zenChatComponent` | The `<zen-chat>` web component — events bound in DOMContentLoaded |
| `_crawlTm` | JS variable — non-null = crawl is active. Check before clearing index. |
| `_chatCtrl` | JS `AbortController` — aborted on `goSetup()` to kill active LLM stream |

## Pipeline Presets (defined in `app.py`)

There are exactly **5 pipelines**. The UI grid shows 4 per row then wraps to a 5th.

| ID | Label | Key Feature |
|---|---|---|
| `baseline` | Baseline | Direct vector search, no post-processing |
| `reranked` | Reranked | + Reranker + Smart Dedup |
| `routed` | Query Routed | + Intent-aware routing |
| `full_stack` | Full Stack | + CRAG + Hallucination detection |
| `enterprise_stack` | Enterprise Stack | + HyDE + Advanced Reranking |

## zen-chat Web Component API

Located at: `zen_core_libs/zen_core_libs/ui/zen_chat.js`

| Method | Description |
|---|---|
| `setLang(code)` | Set language: `'EN'`, `'RO'`, `'HU'`, `'DE'`, `'FR'`, `'IT'` |
| `setWorking(bool)` | `true` = start rotating status messages + amber dot. `false` = revert to idle |
| `updateStatus()` | Sync dot color and title to current `isReady` state |
| `addMessage(text, role, id?)` | Add a chat bubble (`role='user'` or `'bot'`) |
| `setTypingIndicator(bool)` | Show/hide the animated typing dots |
| `clearMessages()` | Remove all chat bubbles |

**Status dot color meanings:**
- 🟢 Green = Ready / idle
- 🔴 Red = Not ready / offline
- 🟡 Amber = Working (LLM is streaming)

**Called automatically from `index.html`:**
- `sendChat()` → calls `zc.setLang(curLang)` then `zc.setWorking(true)`
- `singlePipeChat.finish()` → calls `zc.setWorking(false)`
- `multiPipeChat.finishAll()` → calls `zc.setWorking(false)`
