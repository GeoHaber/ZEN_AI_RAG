# ZenAI 2.1: The Intelligence Scaling & Reliability Manual

Welcome to **ZenAI 2.1**, a professional-grade, local-first artificial intelligence platform. This manual is designed to be your definitive guide to the "Triple Threat" architecture, providing clarity on how to leverage our advanced Swarm Intelligence, Retrieval Augmented Generation (RAG), and System Autonomy features.

---

## 🏛️ The "Triple Threat" Architecture

ZenAI 2.1 is built on a synergistic foundation that ensures every response is logically sound, factually accurate, and verified.

| Pillar | Technology | Purpose |
| :--- | :--- | :--- |
| **Logic** | **Smart LLM** (Qwen 2.5 / Llama 3) | The core "brain" that synthesizes information and provides human-like reasoning. |
| **Facts** | **Generic RAG** | The "library" that retrieves real-time data from your local files, websites, and documentation. |
| **Trust** | **NCP Swarm Arbitrator** | The "reviewer" that fact-checks the LLM, assigns specialists, and ensures reliability. |

---

## 🚀 Core Features

### 1. Specialist Swarm (NCP)
When **Swarm Mode (CoT)** is enabled, ZenAI doesn't just "talk"—it thinks. It automatically assigns the most relevant "Expert Specialists" to your query:
- **Logical Reasoning**: For philosophy or complex decision-making.
- **Senior Software Architect**: For deep code reviews and system design.
- **Security Auditor**: For risk assessment and vulnerability research.
- **Performance Engineer**: For optimization tasks.

### 2. The Intelligence Judge
Located in the **Left Sidebar**, the Judge allows you to benchmark your local model's performance.
- **Semantic Quality**: Measures how accurately the model answers ground-truth questions.
- **Semantic Drift**: Tracks whether your engine is becoming more or less capable over time.
- **Latency Tracking**: Monitors tokens-per-second (TPS) to ensure your hardware is optimized.

### 3. Self-Aware Help System
ZenAI knows its own code. By indexing its own READMEs, Specifications, and Python Docstrings, it can act as an expert on itself.
- **Tip**: Ask *"How do your internals work?"* or *"What are your specialist roles?"* to see this in action.

---

## 🌐 Remote Access (Messaging Gateways)

Connect to your ZenAI brain from anywhere in the world using secure messaging protocols.

### 🔹 Telegram Gateway
- **Setup**: Get a token from [@BotFather](https://t.me/botfather) and add it to `config.json`.
- **Authorization**: Add your numeric Telegram User ID to `telegram_whitelist`.
- **Command Support**: Use `/rag [query]` to search your local files via mobile.

### 🔹 WhatsApp (Twilio) Gateway
- **Setup**: Connect your Twilio Sandbox to ZenAI's webhook port (default: 5001).
- **Format**: Whitelist your number in E.164 format (e.g., `+1234567890`) in `config.json`.
- **Experience**: The WhatsApp gateway uses the same "Thinking" process as the desktop UI, delivering verified answers to your pocket.

---

## 💎 System Autonomy (Autopilot)

ZenAI 2.1 is the first version to feature active system self-improvement.

### 1. The "Shiny" Auto-Updater
ZenAI monitors the official `llama.cpp` repository for new performance releases.
- **Auto-Check**: The system checks for "Shiny" updates every time it starts.
- **Safe Substitution**: When you approve an update, ZenAI:
    1. Downloads the optimized binary.
    2. Creates a `.bak` of your current engine.
    3. Validates the new engine before going live.

### 2. The "Model Scout"
Don't settle for average models. The Model Scout scours Hugging Face for "Best-in-Class" AI.
- **Discovery**: It finds trending coding, reasoning, and math models.
- **Suggestions**: If a "Shiny" new model is outperforming your current one, ZenAI will suggest a download chip in the UI.

### 3. The "Anti-Zombie" Guardian
ZenAI 2.1 features an active process management system to ensure 100% startup reliability.
- **Clean Startup**: The system scans local ports (8080, 8001, 8002) for stale "Zombie" processes from previous sessions.
- **Auto-Pruning**: If a conflict is found, ZenAI offers to safely terminate the blocking process, preventing "Address already in use" errors.

---

## 🛠️ Developer Productivity (Batch Mode)

### 1. Batch Code Review
Analyze entire projects or directories in one go.
- **Deep Scrutiny**: The Batch Engine processes multiple files for security risks, logic flaws, and architectural improvements.
- **Permanent Reports**: Generates a detailed `_zena_analisis.md` report for every file analyzed, creating a persistent record of your project's health.
- **Engagement**: Features Claude-style randomized thinking messages and live progress spinners to keep you updated during long computations.

---

## ⚙️ Settings & Configuration

The **Settings (Gear Icon)** in the sidebar allows you to tailor the experience:

### 🌑 Display Prefrences
- **Dark Mode**: High-contrast, easy-on-the-eyes theme (Default).
- **Language**: Dynamic localization (English, German, French, etc.).

### 🧠 Performance Tuning
- **Optimal Experts**: Define how many LLM nodes the Swarm should use (3-8).
- **Network Access**: Toggle whether RAG is allowed to fetch live web data.
- **Voice Engine**: Enable or disable the real-time Text-to-Speech (TTS) engine.

---

## ❓ Troubleshooting

| Scenario | Solution |
| :--- | :--- |
| **Response is slow** | Reduce the number of 'Optimal Experts' in Settings or disable Swarm/CoT mode. |
| **Unknown User (TG/WA)** | Verify your ID or Phone Number is exactly matched in the `config.json` whitelist. |
| **Index Missing Info** | Click **Scan Now** in the RAG section to refresh your local knowledge base. |

---

*ZenAI 2.1.1 (Final Production Build) • Verified for RAG Indexing • Created by Antigravity*
