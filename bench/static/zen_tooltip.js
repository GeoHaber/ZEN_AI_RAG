/**
 * ZenTooltip — Universal ⓘ tooltip widget for all GeorgeHaber UIs.
 *
 * Drop-in: add <script src="zen_tooltip.js"></script> to any HTML page.
 *
 * How it works:
 *   1. Scans for elements with [data-tip="Term Name"] attribute
 *   2. Appends a styled ⓘ icon next to each
 *   3. On hover, shows a plain-English popup from the glossary
 *
 * You can also call ZenTooltip.attach(element, "term") or
 * ZenTooltip.define("term", "definition") from JS.
 *
 * Glossary is embedded at build time or loaded from glossary.json.
 */
(function () {
  'use strict';

  // ── Inline Glossary (flattened from glossary.json categories) ──────────
  const GLOSSARY = {
    // ── LLM Training ──
    "SFT": "Supervised Fine-Tuning — teaching a model by showing it correct input→output examples, like flashcards.",
    "DPO": "Direct Preference Optimization — training where the model learns from pairs of 'good' vs 'bad' answers instead of a separate reward model.",
    "LoRA": "Low-Rank Adaptation — a memory-efficient way to fine-tune large models by only updating a small set of extra weights instead of the whole model.",
    "LoRA Rank": "Controls how many extra parameters LoRA adds. Higher rank = more capacity but more memory. Rank 16 is a common sweet spot.",
    "QLoRA": "Quantized LoRA — combines 4-bit model compression with LoRA to fine-tune huge models on consumer GPUs.",
    "GGUF": "A file format for storing quantized LLM weights. Lets you run large models on CPUs or low-memory GPUs.",
    "Quantization": "Compressing a model's weights from 32-bit to smaller formats (8-bit, 4-bit, 3-bit). Shrinks size and speeds up inference with minimal quality loss.",
    "Epoch": "One full pass through the entire training dataset. More epochs = more learning, but too many can cause overfitting.",
    "Batch Size": "How many examples the model processes at once during training. Larger batches use more memory but train more stably.",
    "Learning Rate": "How big a step the model takes when updating its weights. Too high = unstable, too low = slow learning.",
    "Gradient Accumulation": "Simulates a larger batch size by adding up gradients over several small batches before updating. Saves memory.",
    "Warmup Steps": "Gradually increases the learning rate at the start of training to prevent early instability.",
    "Cosine Scheduler": "A learning rate schedule that smoothly decreases the rate following a cosine curve — fast learning early, gentle refinement later.",
    "bf16": "Brain Float 16 — a 16-bit number format optimized for training. Faster than fp32, better range than fp16.",
    "fp16": "Half-precision floating point — uses 16 bits instead of 32. Faster training but can overflow on some operations.",
    "Mixed Precision": "Uses both 16-bit and 32-bit numbers during training — fast where possible, precise where needed.",
    "DeepSpeed": "Microsoft's library for training large models across multiple GPUs with memory optimizations (ZeRO stages).",
    "ZeRO": "Zero Redundancy Optimizer — splits model states across GPUs so each GPU only stores a fraction. Stage 1-3 from least to most aggressive.",
    "Checkpoint": "A saved snapshot of model weights and optimizer state during training. Lets you resume if training crashes.",
    "Adapter": "Small trainable modules (like LoRA) bolted onto a frozen base model. Cheap to train and swap.",
    "Merge": "Combining a trained adapter back into the base model to create a single standalone model file.",
    "Overfitting": "When a model memorizes the training data too well and performs badly on new data it hasn't seen.",
    "Loss": "A number measuring how wrong the model's predictions are. Training aims to minimize this.",
    "Perplexity": "How 'surprised' the model is by text. Lower perplexity = the model predicts words more confidently.",
    "Token": "The smallest unit the model reads — usually a word piece or subword. 'unhappiness' might be 3 tokens.",
    "Context Window": "The maximum number of tokens a model can 'see' at once. Larger windows handle longer conversations.",

    // ── Distillation ──
    "Distillation": "Training a smaller 'student' model to mimic a larger 'teacher' model's outputs. Transfers knowledge without the teacher's size.",
    "Student Model": "The smaller model being trained to replicate the teacher's behavior.",
    "Teacher Model": "The larger, smarter model whose outputs the student learns from.",
    "Teacher Consensus": "When multiple teacher models agree on an answer. Higher agreement = higher confidence the answer is correct.",
    "GOLD Tier": "Highest quality — all teachers agree on this response. Safe to train on.",
    "SILVER Tier": "Partial agreement between teachers. May need review before training.",
    "DROP Tier": "Teachers disagreed significantly. This sample is excluded from training.",
    "Purification": "Filtering raw teacher outputs through quality tiers (GOLD/SILVER/DROP) to keep only the best training data.",
    "Multi-Teacher": "Using 2+ different LLMs as teachers for broader coverage and consensus-based quality filtering.",

    // ── RAG ──
    "RAG": "Retrieval-Augmented Generation — the model searches a knowledge base before answering, grounding its response in real documents.",
    "Embedding": "Converting text into a list of numbers (a vector) that captures its meaning. Similar texts have similar vectors.",
    "Vector Search": "Finding the most similar documents by comparing their embedding vectors. Think of it as 'semantic Google'.",
    "TurboQuant": "Our custom 3-bit vector compression that shrinks embeddings by 5-6x with near-zero accuracy loss.",
    "Chunk": "A piece of a larger document, sized for the model's context window. Usually 256-512 tokens.",
    "Chunking": "Splitting documents into smaller pieces (chunks) so the model can process them. Strategy affects retrieval quality.",
    "Reranking": "After initial retrieval, a second model re-scores results for better precision. CrossEncoder reranking adds ~15-20% accuracy.",
    "HyDE": "Hypothetical Document Embeddings — generates a fake answer first, then uses it to search for real documents. Better than raw query search.",
    "FLARE": "Forward-Looking Active REtrieval — detects when the model is uncertain mid-generation and fetches more context on the fly.",
    "CRAG": "Corrective RAG — grades retrieval confidence (Correct/Ambiguous/Incorrect) and self-heals by web-searching when local results are weak.",
    "Top-K": "How many documents to retrieve. K=5 means 'give me the 5 most relevant chunks'.",
    "Recall@K": "The fraction of relevant documents found in the top K results. R@5=80% means 4 out of 5 expected docs were retrieved.",
    "Cosine Similarity": "Measures how similar two vectors are by the angle between them. 1.0 = identical direction, 0 = unrelated.",
    "Sentence Transformer": "A neural network that converts sentences into meaningful vectors. We use all-MiniLM-L6-v2 as default.",
    "Knowledge Graph": "A structured database of facts as (subject, predicate, object) triples — e.g., ('Aspirin', 'is a', 'NSAID').",
    "Taxonomy Filter": "Pre-filters search results by project/topic/type hierarchy before scoring. Proven +83% recall improvement.",
    "Contradiction Detection": "Checks new facts against stored knowledge to catch conflicts before they enter the database.",
    "Temporal Validity": "Facts have start/end dates. Enables point-in-time queries like 'what was true on April 3?'.",
    "Faithfulness": "How accurately the model's answer reflects the retrieved documents — no hallucinated details.",
    "Relevance": "How well the retrieved documents match the user's actual question.",

    // ── Code Analysis ──
    "Severity": "How serious a code issue is: High (security risk), Medium (bug potential), Low (style/quality).",
    "Taint Analysis": "Tracks untrusted user input through the code to find where it could cause security vulnerabilities.",
    "Taint Mode": "When enabled, the scanner traces data flow from user input to dangerous sinks (SQL, eval, file I/O).",
    "Cyclomatic Complexity": "Counts the number of independent paths through code. Higher = harder to test and more bug-prone.",
    "Coupling": "How much one module depends on others. High coupling means changes ripple through the codebase.",
    "Afferent Coupling": "How many other modules depend on THIS module. High Ca = important but risky to change.",
    "Efferent Coupling": "How many other modules THIS module depends on. High Ce = fragile, breaks when dependencies change.",
    "Instability": "Ce / (Ca + Ce) — ranges from 0 (totally stable) to 1 (totally unstable). Unstable modules break more often.",
    "God Module": "A module with too many responsibilities — high coupling in both directions. Should be split up.",
    "Dead Code": "Code that's never called or reached. Adds confusion and maintenance burden for zero benefit.",
    "Orphan Map": "Finds UI actions with no backend handler and backend routes with no frontend caller.",
    "Schema Drift": "When the frontend expects fields that the backend doesn't send (or vice versa). Causes silent bugs.",
    "Tech Debt": "Accumulated shortcuts and workarounds in code. Like financial debt — cheap now, expensive later.",
    "Autofix": "Automatically applying safe code fixes for detected issues. Only done for high-confidence, low-risk repairs.",
    "Gate": "A quality threshold that must be passed before code can ship. Example: 'no more than 3 high-severity findings'.",
    "Bandit": "A Python security scanner that finds common vulnerability patterns like hardcoded passwords or SQL injection.",
    "Coverage": "What percentage of code is exercised by tests. 80%+ is typically the target.",
    "Policy": "A set of rules defining which findings to flag and which to ignore. Custom policies let you tune signal vs noise.",
    "Recipe": "A pre-built scan configuration combining a policy, engine, and severity thresholds for a specific use case.",
    "Profile": "A saved scan configuration that remembers your settings for quick repeat scans.",

    // ── Trading ──
    "Candlestick": "A chart bar showing open, high, low, close prices for a time period. Green = price went up, red = went down.",
    "RSI": "Relative Strength Index — momentum indicator from 0-100. Above 70 = overbought (may drop), below 30 = oversold (may rise).",
    "MACD": "Moving Average Convergence Divergence — shows the relationship between two moving averages. Crossovers signal trend changes.",
    "EMA": "Exponential Moving Average — like a simple average but gives more weight to recent prices.",
    "SMA": "Simple Moving Average — the plain average of the last N prices.",
    "Bollinger Bands": "Two bands around a moving average at ±2 standard deviations. Price touching the bands suggests it's stretched too far.",
    "Volume": "How many shares/contracts traded in a period. High volume confirms price moves; low volume suggests weakness.",
    "Blended Score": "Our combined score from sentiment (30%), technical (40%), and fundamental (30%) analysis.",
    "Sentiment Score": "How positive or negative news/social media is about a stock. Ranges from -1 (bearish) to +1 (bullish).",
    "Technical Score": "Score based on chart patterns and indicators (RSI, MACD, moving averages).",
    "Fundamental Score": "Score based on company financials — revenue, earnings, debt, valuation ratios.",
    "Regime": "The current market state: trending up (bull), trending down (bear), or going sideways (range-bound).",
    "Watchlist": "Your saved list of stocks to monitor. Updates in real-time with price changes and signals.",
    "Signal": "A buy/sell recommendation generated when multiple analysis agents agree.",
    "Agent Consensus": "When 2+ of our 3 AI agents (sentiment, technical, fundamental) agree on a direction.",

    // ── OCR ──
    "OCR": "Optical Character Recognition — extracting text from images. Converts photos of documents into editable text.",
    "Post-Processor": "An LLM that cleans up raw OCR output — fixing misspellings, broken words, and formatting errors.",
    "Confidence Tier": "How certain the OCR engine is about its reading. High confidence = probably correct, low = needs review.",

    // ── Infrastructure ──
    "Virtual Environment": "An isolated Python installation for a project. Keeps dependencies separate so projects don't conflict.",
    "WAL Mode": "Write-Ahead Logging — a SQLite journal mode that allows concurrent reads during writes. Faster and safer.",
    "WebSocket": "A persistent two-way connection between browser and server. Enables real-time updates without polling.",
    "REST API": "A web API that uses HTTP methods (GET, POST, PUT, DELETE) to read and write data.",
    "Service Worker": "A browser script that runs in the background — enables offline support, caching, and push notifications.",
    "PWA": "Progressive Web App — a website that behaves like a native app, with offline support and home-screen install.",
    "GPU Layers": "How many model layers to offload from CPU to GPU. -1 means 'all layers on GPU'. More layers = faster but more VRAM.",
    "KV Cache": "Key-Value Cache — stores previously computed attention values so the model doesn't recalculate them. Crucial for fast inference.",
    "Flash Attention": "An optimized attention algorithm that is 2-4x faster and uses less memory than standard attention.",
    "mlock": "Memory lock — pins model data in RAM so the operating system can't swap it to disk. Prevents slowdowns.",
    "Continuous Batching": "Processes multiple user requests simultaneously in a single batch. Improves throughput on servers.",
    "System Prompt": "Hidden instructions given to the LLM before the user's message. Defines the model's personality and behavior.",
    "Base URL": "The server address where the LLM API is running. For local models, typically http://localhost:port.",
    "API Key": "A secret token that authenticates your requests to an LLM provider. Keep it private.",

    // ── Healthcare ──
    "DMS": "Days Mean Stay — average number of days a patient stays in the hospital per admission. Lower is generally better for efficiency.",
    "CMI": "Case-mix Index — measures the average complexity of patients treated. Higher CMI means sicker, more resource-intensive patients.",
    "Occupancy": "Percentage of available hospital beds currently in use. Above 85% is considered high, risking overcrowding.",
    "Admissions": "The number of new patients admitted to the hospital within a given period.",
    "Bed Occupancy": "The ratio of occupied beds to total available beds, shown as a percentage or fraction.",
    "On Duty": "Clinicians (doctors, nurses) currently working their scheduled shift.",
    "Budget Execution": "Percentage of the allocated budget that has been spent so far. Tracks financial progress.",
    "Revenue": "Total income generated from patient care services, insurance, and other sources.",
    "Alert Severity": "Priority level of a system notification: Critical (immediate action), Moderate (attention needed), Info (awareness).",

    // ── Evaluation ──
    "Hallucination": "When the model confidently states something that isn't in the source material or isn't true.",
    "NLI Contradiction": "Natural Language Inference finds where the model's answer directly contradicts the evidence.",
    "Grounding": "How well the model's response is anchored to the retrieved source documents.",
    "F1 Score": "Harmonic mean of precision and recall — combining 'did I find everything?' and 'was everything correct?'.",
    "BLEU Score": "Measures how similar generated text is to reference text by counting matching word sequences.",
    "Judge Model": "A separate LLM used to score the quality of another model's responses. Like a teacher grading an exam.",
    "Benchmark": "A standardized test suite for comparing model performance across tasks."
  };

  // ── CSS (injected once) ────────────────────────────────────────────────
  const STYLE_ID = 'zen-tooltip-styles';
  if (!document.getElementById(STYLE_ID)) {
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      .zen-tip-icon {
        display: inline-flex; align-items: center; justify-content: center;
        width: 16px; height: 16px; border-radius: 50%; font-size: 10px;
        background: rgba(0, 240, 255, 0.15); color: #00f0ff;
        border: 1px solid rgba(0, 240, 255, 0.3); cursor: help;
        margin-left: 5px; vertical-align: middle; position: relative;
        font-style: normal; font-weight: 600; line-height: 1;
        transition: background 0.2s, transform 0.15s;
        flex-shrink: 0;
      }
      .zen-tip-icon:hover {
        background: rgba(0, 240, 255, 0.3); transform: scale(1.15);
      }
      /* Streamlit / light theme variant */
      [data-theme="light"] .zen-tip-icon,
      .stApp .zen-tip-icon {
        background: rgba(59, 130, 246, 0.12); color: #2563eb;
        border-color: rgba(59, 130, 246, 0.3);
      }
      [data-theme="light"] .zen-tip-icon:hover,
      .stApp .zen-tip-icon:hover {
        background: rgba(59, 130, 246, 0.25);
      }
      .zen-tip-popup {
        position: fixed; z-index: 999999; pointer-events: none;
        background: #1a1d2e; color: #e6edf3; border: 1px solid rgba(0, 240, 255, 0.25);
        border-radius: 8px; padding: 10px 14px; font-size: 13px; line-height: 1.5;
        max-width: 340px; min-width: 200px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 12px rgba(0,240,255,0.1);
        backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
        opacity: 0; transform: translateY(6px);
        transition: opacity 0.18s ease-out, transform 0.18s ease-out;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      }
      .zen-tip-popup.visible {
        opacity: 1; transform: translateY(0); pointer-events: auto;
      }
      .zen-tip-popup::before {
        content: ''; position: absolute; bottom: -6px; left: 24px;
        width: 10px; height: 10px; background: #1a1d2e;
        border-right: 1px solid rgba(0,240,255,0.25);
        border-bottom: 1px solid rgba(0,240,255,0.25);
        transform: rotate(45deg);
      }
      .zen-tip-popup.below::before {
        top: -6px; bottom: auto;
        border-right: none; border-bottom: none;
        border-left: 1px solid rgba(0,240,255,0.25);
        border-top: 1px solid rgba(0,240,255,0.25);
      }
      .zen-tip-popup .tip-term {
        font-weight: 700; color: #00f0ff; font-size: 12px;
        text-transform: uppercase; letter-spacing: 0.5px;
        margin-bottom: 4px;
      }
      .zen-tip-popup .tip-body {
        color: #c9d1d9;
      }
      /* Light theme popup */
      [data-theme="light"] .zen-tip-popup,
      .stApp .zen-tip-popup {
        background: #ffffff; color: #1f2937;
        border-color: rgba(59, 130, 246, 0.25);
        box-shadow: 0 8px 32px rgba(0,0,0,0.12), 0 0 8px rgba(59,130,246,0.08);
      }
      [data-theme="light"] .zen-tip-popup .tip-term,
      .stApp .zen-tip-popup .tip-term { color: #2563eb; }
      [data-theme="light"] .zen-tip-popup .tip-body,
      .stApp .zen-tip-popup .tip-body { color: #4b5563; }
      [data-theme="light"] .zen-tip-popup::before,
      .stApp .zen-tip-popup::before {
        background: #ffffff;
        border-color: rgba(59,130,246,0.25);
      }
      /* Tailwind dark theme (Market AI) */
      .dark .zen-tip-popup { background: #111827; border-color: rgba(75,85,99,0.5); }
      .dark .zen-tip-popup::before { background: #111827; border-color: rgba(75,85,99,0.5); }
      .dark .zen-tip-popup.below::before { border-color: rgba(75,85,99,0.5); }
    `;
    document.head.appendChild(style);
  }

  // ── Shared popup ───────────────────────────────────────────────────────
  let popup = document.getElementById('zen-tip-popup');
  if (!popup) {
    popup = document.createElement('div');
    popup.id = 'zen-tip-popup';
    popup.className = 'zen-tip-popup';
    document.body.appendChild(popup);
  }

  let hideTimeout = null;

  function showPopup(icon, term, definition) {
    clearTimeout(hideTimeout);
    popup.innerHTML = '<div class="tip-term">' + esc(term) + '</div><div class="tip-body">' + esc(definition) + '</div>';

    // Position above the icon
    const rect = icon.getBoundingClientRect();
    popup.classList.remove('below', 'visible');
    popup.style.left = Math.max(8, rect.left - 12) + 'px';

    // Try above first
    popup.style.top = '0px';
    popup.style.display = 'block';
    const pH = popup.offsetHeight;

    if (rect.top - pH - 10 > 0) {
      popup.style.top = (rect.top - pH - 10) + 'px';
    } else {
      popup.style.top = (rect.bottom + 10) + 'px';
      popup.classList.add('below');
    }

    // Keep popup on screen horizontally
    const pW = popup.offsetWidth;
    const maxLeft = window.innerWidth - pW - 8;
    if (parseFloat(popup.style.left) > maxLeft) {
      popup.style.left = Math.max(8, maxLeft) + 'px';
    }

    requestAnimationFrame(function () { popup.classList.add('visible'); });
  }

  function hidePopup() {
    hideTimeout = setTimeout(function () {
      popup.classList.remove('visible');
    }, 120);
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  // ── Core: attach tooltip to an element ─────────────────────────────────
  function attach(el, term) {
    if (el.querySelector('.zen-tip-icon')) return; // already has tooltip

    const key = findKey(term);
    if (!key) return;
    const def = GLOSSARY[key];

    const icon = document.createElement('i');
    icon.className = 'zen-tip-icon';
    icon.textContent = 'ⓘ';
    icon.setAttribute('aria-label', 'Info: ' + key);
    icon.setAttribute('role', 'img');

    icon.addEventListener('mouseenter', function () { showPopup(icon, key, def); });
    icon.addEventListener('mouseleave', hidePopup);
    icon.addEventListener('focus', function () { showPopup(icon, key, def); });
    icon.addEventListener('blur', hidePopup);
    icon.tabIndex = 0;

    el.appendChild(icon);
  }

  // ── Case-insensitive glossary lookup ───────────────────────────────────
  const _keyLower = {};
  Object.keys(GLOSSARY).forEach(function (k) { _keyLower[k.toLowerCase()] = k; });

  function findKey(term) {
    if (GLOSSARY[term]) return term;
    const lower = term.toLowerCase();
    if (_keyLower[lower]) return _keyLower[lower];
    // Partial match: "Learning Rate" in "learning_rate" or "learning-rate"
    const normalized = lower.replace(/[-_]/g, ' ');
    if (_keyLower[normalized]) return _keyLower[normalized];
    return null;
  }

  // ── Auto-scan: find [data-tip] elements ────────────────────────────────
  function scan(root) {
    root = root || document;
    var els = root.querySelectorAll('[data-tip]');
    for (var i = 0; i < els.length; i++) {
      attach(els[i], els[i].getAttribute('data-tip'));
    }
  }

  // ── Auto-discover: scan labels, headings, and known terms ──────────────
  function autoDiscover(root) {
    root = root || document;
    // Scan data-tip elements first
    scan(root);

    // Then scan labels, h3s, summary tags, setting rows, etc.
    var selectors = 'label, .setting-row label, .section h3, th, summary, [class*="label"], [class*="heading"]';
    var els = root.querySelectorAll(selectors);
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (el.querySelector('.zen-tip-icon')) continue;

      // Get text, strip emoji/special chars
      var text = (el.textContent || '').replace(/[^\w\s@/-]/g, '').trim();
      if (!text || text.length > 50) continue;

      var key = findKey(text);
      if (key) attach(el, key);
    }
  }

  // ── Define a custom term ───────────────────────────────────────────────
  function define(term, definition) {
    GLOSSARY[term] = definition;
    _keyLower[term.toLowerCase()] = term;
  }

  // ── MutationObserver for dynamic content ───────────────────────────────
  var observer = new MutationObserver(function (mutations) {
    for (var i = 0; i < mutations.length; i++) {
      var added = mutations[i].addedNodes;
      for (var j = 0; j < added.length; j++) {
        if (added[j].nodeType === 1) {
          scan(added[j]);
          // Also discover in dynamically added content
          if (added[j].querySelectorAll) {
            var tips = added[j].querySelectorAll('[data-tip]');
            for (var k = 0; k < tips.length; k++) {
              attach(tips[k], tips[k].getAttribute('data-tip'));
            }
          }
        }
      }
    }
  });

  // ── Initialize ─────────────────────────────────────────────────────────
  function init() {
    autoDiscover();
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // ── Public API ─────────────────────────────────────────────────────────
  window.ZenTooltip = {
    glossary: GLOSSARY,
    attach: attach,
    define: define,
    scan: scan,
    autoDiscover: autoDiscover,
    findKey: findKey
  };
})();
