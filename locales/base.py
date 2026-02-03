# -*- coding: utf-8 -*-
"""
locales/base.py - Base Locale Class
Defines all UI strings that need localization.
Subclass this and override strings for new languages.
"""

class BaseLocale:
    """
    Base locale class containing all UI strings.
    Override in language-specific subclasses.
    """
    
    # ==========================================================================
    # METADATA
    # ==========================================================================
    LANGUAGE_CODE = "en"
    LANGUAGE_NAME = "English"
    LANGUAGE_NATIVE = "English"
    
    # ==========================================================================
    # APPLICATION
    # ==========================================================================
    APP_NAME = "ZenAI"
    APP_NAME_FULL = "ZenAI Assistant"
    APP_TITLE = "ZenAI"
    APP_WELCOME = "Welcome to ZenAI!"
    APP_TAGLINE = "Your AI-powered assistant"
    
    # ==========================================================================
    # NAVIGATION & SECTIONS
    # ==========================================================================
    NAV_MODEL_MANAGER = "MODEL MANAGER"
    NAV_AI_ENGINE = "AI ENGINE MODE"
    NAV_SYSTEM = "SYSTEM"
    NAV_SETTINGS = "SETTINGS"
    NAV_HELP = "HELP"
    
    # ==========================================================================
    # COMMON BUTTONS
    # ==========================================================================
    BTN_OK = "OK"
    BTN_CANCEL = "Cancel"
    BTN_CLOSE = "Close"
    BTN_SAVE = "Save"
    BTN_DELETE = "Delete"
    BTN_EDIT = "Edit"
    BTN_REFRESH = "Refresh"
    BTN_DOWNLOAD = "Download"
    BTN_UPLOAD = "Upload"
    BTN_START = "Start"
    BTN_STOP = "Stop"
    BTN_RETRY = "Retry"
    BTN_BACK = "Back"
    BTN_NEXT = "Next"
    BTN_SEND = "Send"
    BTN_CLEAR = "Clear"
    BTN_NEW_CHAT = "💬 New Chat"
    BTN_YES = "Yes"
    BTN_NO = "No"
    
    # ==========================================================================
    # CHAT
    # ==========================================================================
    CHAT_CLEARED = "Chat cleared"
    
    # ==========================================================================
    # MODEL MANAGEMENT
    # ==========================================================================
    MODEL_SECTION_TITLE = "📥 Download New Models"
    MODEL_ACTIVE_LABEL = "Active Model"
    MODEL_DOWNLOAD_NEW = "Download New Model"
    MODEL_QUICK_DOWNLOADS = "Quick Downloads"
    MODEL_CUSTOM_DOWNLOAD = "Custom Download"
    MODEL_CUSTOM_DESCRIPTION = "Download any GGUF model from Hugging Face"
    MODEL_REPO_PLACEHOLDER = "e.g. Qwen/Qwen2.5-7B-Instruct-GGUF"
    MODEL_FILE_PLACEHOLDER = "e.g. qwen2.5-7b-instruct-q4_k_m.gguf"
    MODEL_REPO_LABEL = "Repository ID"
    MODEL_FILE_LABEL = "Filename"
    
    # Model card labels
    MODEL_CONTEXT = "Context"
    MODEL_BENCHMARK = "Benchmark"
    MODEL_SPEED = "Speed"
    MODEL_QUALITY = "Quality"
    MODEL_LICENSE = "License"
    MODEL_PARAMETERS = "Parameters"
    MODEL_RAM_NEEDED = "RAM Needed"
    MODEL_DOWNLOADS = "downloads"
    MODEL_RELEASED = "Released"
    MODEL_WHAT_THIS_MEANS = "💾 What this means:"
    
    # Speed ratings
    SPEED_FAST = "⚡⚡⚡ Fast"
    SPEED_BALANCED = "⚡⚡ Balanced"
    SPEED_MODERATE = "⚡ Moderate"
    SPEED_SLOW = "Slower"
    
    # Quality ratings
    QUALITY_5_STAR = "⭐⭐⭐⭐⭐"
    QUALITY_4_STAR = "⭐⭐⭐⭐"
    QUALITY_3_STAR = "⭐⭐⭐"
    
    # ==========================================================================
    # AI ENGINE
    # ==========================================================================
    ENGINE_COT_SWARM = "CoT Swarm (Experts)"
    ENGINE_COT_DESCRIPTION = "Parallel Consensus Arbitrage"
    ENGINE_QUIET_MODE = "Quiet Mode (Hide Experts)"
    ENGINE_QUIET_DESCRIPTION = "Only show final verified answer"
    ENGINE_SCANNING_SWARM = "Scanning swarm..."
    ENGINE_EXPERTS_ONLINE = "{count} Experts Online"
    ENGINE_STANDALONE = "ZenAI Standalone Mode"
    
    # ==========================================================================
    # SYSTEM
    # ==========================================================================
    SYS_CHECK_VERSION = "Check llama.cpp Version"
    SYS_RUN_BENCHMARK = "Run Benchmark"
    SYS_DIAGNOSTICS = "Diagnostics"
    SYS_UPDATE_ENGINE = "Update Engine"
    SYS_GET_UPDATE = "Get Update (GitHub)"
    
    # ==========================================================================
    # SETTINGS
    # ==========================================================================
    SETTINGS_TITLE = "Settings"
    SETTINGS_SAVE = "Save Settings"
    SETTINGS_RESET = "Reset to Defaults"
    SETTINGS_SAVED = "Settings saved successfully"
    SETTINGS_RESET_CONFIRM = "Are you sure you want to reset all settings to defaults?"
    SETTINGS_LANGUAGE_CHANGED = "Language changed to {lang}. Refresh page to apply."
    
    # Settings Categories
    SETTINGS_CAT_LANGUAGE = "🌐 Language"
    SETTINGS_CAT_APPEARANCE = "🎨 Appearance"
    SETTINGS_CAT_AI_MODEL = "🤖 AI Model"
    SETTINGS_CAT_VOICE = "🎤 Voice"
    SETTINGS_CAT_RAG = "📚 RAG"
    SETTINGS_CAT_CHAT = "💬 Chat"
    SETTINGS_CAT_SYSTEM = "⚙️ System"
    
    # Language Settings
    SETTINGS_UI_LANGUAGE = "Interface Language"
    SETTINGS_UI_LANGUAGE_DESC = "Select the language for the user interface"
    
    # Appearance Settings
    SETTINGS_DARK_MODE = "Dark Mode"
    SETTINGS_DARK_MODE_DESC = "Enable dark color theme"
    SETTINGS_FONT_SIZE = "Font Size"
    SETTINGS_FONT_SIZE_SMALL = "Small"
    SETTINGS_FONT_SIZE_MEDIUM = "Medium"
    SETTINGS_FONT_SIZE_LARGE = "Large"
    SETTINGS_CHAT_DENSITY = "Chat Density"
    SETTINGS_CHAT_DENSITY_COMPACT = "Compact"
    SETTINGS_CHAT_DENSITY_COMFORTABLE = "Comfortable"
    SETTINGS_CHAT_DENSITY_SPACIOUS = "Spacious"
    SETTINGS_SHOW_AVATARS = "Show Avatars"
    SETTINGS_ANIMATE_MESSAGES = "Animate Messages"
    
    # AI Model Settings
    SETTINGS_DEFAULT_MODEL = "Default Model"
    SETTINGS_DEFAULT_MODEL_DESC = "Model to load on startup"
    SETTINGS_TEMPERATURE = "Temperature"
    SETTINGS_TEMPERATURE_DESC = "Higher = more creative, Lower = more focused (0.0-2.0)"
    SETTINGS_MAX_TOKENS = "Max Tokens"
    SETTINGS_MAX_TOKENS_DESC = "Maximum response length"
    SETTINGS_CONTEXT_WINDOW = "Context Window"
    SETTINGS_CONTEXT_WINDOW_DESC = "How much conversation history to remember"
    SETTINGS_TOP_P = "Top P"
    SETTINGS_REPEAT_PENALTY = "Repeat Penalty"
    SETTINGS_USE_COT_SWARM = "Enable CoT Swarm"
    SETTINGS_USE_COT_SWARM_DESC = "Use multi-expert consensus for better answers"
    SETTINGS_QUIET_COT = "Quiet CoT Mode"
    SETTINGS_QUIET_COT_DESC = "Hide expert deliberation, show only final answer"
    
    # Voice Settings
    SETTINGS_TTS_ENABLED = "Text-to-Speech"
    SETTINGS_TTS_ENABLED_DESC = "Enable voice output"
    SETTINGS_VOICE_SPEED = "Voice Speed"
    SETTINGS_VOICE_SPEED_DESC = "TTS speaking rate (0.5x - 2.0x)"
    SETTINGS_AUTO_SPEAK = "Auto-Speak Responses"
    SETTINGS_AUTO_SPEAK_DESC = "Automatically read AI responses aloud"
    SETTINGS_RECORDING_DURATION = "Recording Duration"
    SETTINGS_RECORDING_DURATION_DESC = "Voice input recording time (seconds)"
    
    # RAG Settings
    SETTINGS_RAG_ENABLED = "Enable RAG"
    SETTINGS_RAG_ENABLED_DESC = "Use knowledge base for answers"
    SETTINGS_CHUNK_SIZE = "Chunk Size"
    SETTINGS_CHUNK_SIZE_DESC = "Text segment size for indexing"
    SETTINGS_SIMILARITY_THRESHOLD = "Similarity Threshold"
    SETTINGS_SIMILARITY_THRESHOLD_DESC = "Minimum relevance score (0.0-1.0)"
    SETTINGS_MAX_RESULTS = "Max Results"
    SETTINGS_MAX_RESULTS_DESC = "Number of sources to retrieve"
    SETTINGS_AUTO_INDEX = "Auto-Index on Startup"
    SETTINGS_AUTO_INDEX_DESC = "Rebuild index when app starts"
    
    # Chat Settings
    SETTINGS_SHOW_TIMESTAMPS = "Show Timestamps"
    SETTINGS_SHOW_TIMESTAMPS_DESC = "Display time on each message"
    SETTINGS_AUTO_SCROLL = "Auto-Scroll"
    SETTINGS_AUTO_SCROLL_DESC = "Scroll to new messages automatically"
    SETTINGS_STREAM_RESPONSES = "Stream Responses"
    SETTINGS_STREAM_RESPONSES_DESC = "Show AI response as it's generated"
    SETTINGS_SHOW_TOKEN_COUNT = "Show Token Count"
    SETTINGS_SHOW_TOKEN_COUNT_DESC = "Display token usage per message"
    SETTINGS_SAVE_CONVERSATIONS = "Save Conversations"
    SETTINGS_SAVE_CONVERSATIONS_DESC = "Remember chat history between sessions"
    SETTINGS_HISTORY_DAYS = "History Retention"
    SETTINGS_HISTORY_DAYS_DESC = "Days to keep conversation history"
    
    # System Settings
    SETTINGS_API_PORT = "API Port"
    SETTINGS_API_PORT_DESC = "LLM backend server port"
    SETTINGS_MODELS_DIRECTORY = "Models Directory"
    SETTINGS_MODELS_DIRECTORY_DESC = "Folder containing GGUF model files"
    SETTINGS_CHECK_UPDATES = "Check Updates on Startup"
    SETTINGS_CHECK_UPDATES_DESC = "Look for new versions automatically"
    SETTINGS_AUTO_START_BACKEND = "Auto-Start Backend"
    SETTINGS_AUTO_START_BACKEND_DESC = "Launch LLM server with the app"
    SETTINGS_LOG_LEVEL = "Log Level"
    SETTINGS_LOG_LEVEL_DESC = "Verbosity of application logs"
    
    # ==========================================================================
    # RAG / SCAN & LEARN
    # ==========================================================================
    RAG_SCAN_LEARN = "Scan & Learn (RAG)"
    RAG_ENABLE = "Enable Scan & Learn (RAG)"
    RAG_SCAN_READ = "Scan & Read"
    RAG_START_SCANNING = "Start Scanning"
    RAG_SOURCE_TYPE = "Source Type"
    RAG_WEBSITE = "Website"
    RAG_LOCAL_DIRECTORY = "Local Directory"
    RAG_WEBSITE_URL = "Website URL"
    RAG_MAX_PAGES = "Max Pages"
    RAG_DIRECTORY_PATH = "Directory Path"
    RAG_MAX_FILES = "Max Files"
    RAG_START_SCAN = "Start Scan"
    RAG_ANSWERED_FROM_SOURCE = "**🔍 Answered from Data Source**"
    RAG_VIEW_SOURCES = "📂 View Source Data"
    RAG_LABEL = "Local Context"
    
    # ==========================================================================
    # CHAT INTERFACE
    # ==========================================================================
    CHAT_PLACEHOLDER = "Message ZenAI..."
    CHAT_PLACEHOLDER_ZENAI = "Ask me anything..."
    CHAT_QUICK_ACTIONS = "Quick Actions"
    CHAT_CHECK_MODEL = "Check Model Status"

    # Loading Messages - Fun rotating messages
    LOADING_WAITING_FOR_USER = [
        "💭 Waiting for your brilliant ideas...",
        "✨ Ready when you are...",
        "🎯 Standing by for your next question...",
        "🌟 Your wish is my command...",
        "💡 Awaiting your input...",
        "🚀 Ready to help whenever you're ready...",
    ]

    LOADING_THINKING = [
        "🤔 Thinking deeply...",
        "🧠 Neurons firing...",
        "⚙️ Crunching the numbers...",
        "✨ Summoning the answer spirits...",
        "🎯 Calculating the perfect response...",
        "🔬 Running the experiments...",
    ]

    LOADING_RAG_THINKING = [
        "📖 Reading through your documents...",
        "🔎 Searching the knowledge base...",
        "📚 Cross-referencing sources...",
        "🗂️ Indexing through information...",
        "🎯 Finding the perfect match...",
    ]

    LOADING_SWARM_THINKING = [
        "🐝 Consulting the expert swarm...",
        "👥 Gathering collective wisdom...",
        "🎯 Polling the experts...",
        "🌊 Hive mind activating...",
        "🏛️ Council in session...",
    ]

    LOADING_DISTRACTIONS = [
        "🤔 Hmm, scratching my head on this one...",
        "🏃‍♂️ Running to the library to check a fact...",
        "🍵 Brewing some digital tea while I think...",
        "📚 Flipping through the encyclopedia...",
        "✨ polishing the pixels...",
        "🧙‍♂️ Consulting the ancient scrolls...",
        "🤖 Beep boop... complex calculation in progress...",
        "🧐 Examining the evidence closely...",
        "🎭 Getting into character...",
        "🌌 Staring into the void for inspiration...",
    ]
    CHAT_LATEST_LLAMA = "Latest llama.cpp"
    CHAT_RUN_BENCHMARK = "Run Benchmark"
    CHAT_HELP = "Help"
    CHAT_YOU = "You"
    CHAT_THINKING = "Thinking..."
    CHAT_READY = "Ready"
    CHAT_RECORDING = "🔴 Recording (5s)..."
    CHAT_TRANSCRIBING = "Transcribing..."
    
    # ==========================================================================
    # FILE UPLOAD
    # ==========================================================================
    UPLOAD_ATTACHED = "📎 {filename} ({size} chars)"
    UPLOAD_SUCCESS = "Attached {filename}"
    UPLOAD_FAILED = "Upload failed: {error}"
    
    # ==========================================================================
    # VOICE
    # ==========================================================================
    VOICE_RECORDING = "🔴 Recording ({seconds}s)..."
    VOICE_TRANSCRIBING = "Transcribing..."
    VOICE_TRANSCRIBED = "Transcribed!"
    VOICE_NO_SPEECH = "No speech detected"
    VOICE_ERROR = "Voice Error: {error}"
    VOICE_NOT_AVAILABLE = "TTS not available (pyttsx3 missing)"
    
    # ==========================================================================
    # NOTIFICATIONS & MESSAGES
    # ==========================================================================
    # Model notifications
    NOTIFY_MODEL_LOADING = "🔄 Loading model: {model}..."
    NOTIFY_MODEL_READY = "✅ Model ready: {model}"
    NOTIFY_MODEL_ACTIVE = "✅ Active model: {model}"
    NOTIFY_MODEL_SET = "✅ Active model set: {model}"
    
    # Download notifications
    NOTIFY_DOWNLOAD_STARTING = "🚀 Starting download: {filename}..."
    NOTIFY_DOWNLOAD_STARTED = "✅ Download started! Check progress in your terminal."
    NOTIFY_DOWNLOAD_FAILED = "❌ Download failed: {error}"
    NOTIFY_DOWNLOAD_ERROR = "❌ Error: {error}"
    NOTIFY_HUB_CONNECTION_ERROR = "❌ Cannot connect to Hub. Is it running on port 8002?"
    
    # Upload/attachment notifications
    NOTIFY_ATTACHED = "Attached {name}"
    NOTIFY_UPLOAD_FAILED = "Upload failed: {error}"
    
    # Voice notifications  
    NOTIFY_SOUNDDEVICE_MISSING = "Error: SoundDevice not found (Headless?)"
    NOTIFY_TRANSCRIBED = "Transcribed!"
    NOTIFY_NO_SPEECH = "No speech detected"
    NOTIFY_TRANSCRIPTION_FAILED = "Transcription Failed: {error}"

    # ======================================================================
    # BATCH / ANALYSIS
    # ======================================================================
    BATCH_MENU = "Batch Jobs"
    BATCH_CREATE_REVIEW = "Create Code Review"
    BATCH_FILES_PLACEHOLDER = "Enter file paths or directory (comma-separated)"
    BATCH_ENQUEUE = "Enqueue"
    ANALYSIS_SAVED = "Analysis saved to _zena_analisis"

    # ======================================================================
    # ENGAGEMENT / THINKING MESSAGES
    # ======================================================================
    ENGAGE_THINKING_SHORT = "Thinking..."
    ENGAGE_THINKING_LONG = "Thinking deeply — fetching references and verifying facts..."
    ENGAGE_FETCHING_REFS = "Fetching references..."
    NOTIFY_VOICE_ERROR = "Voice Error: {error}"
    
    # RAG notifications
    NOTIFY_RAG_ENABLED = "RAG mode enabled"
    NOTIFY_RAG_DISABLED = "RAG mode disabled"
    NOTIFY_RAG_SCANNING = "🔍 Scanning {url}..."
    NOTIFY_RAG_SCRAPING = "📄 Scraping ({count}/{total}) - ETA: {eta}"
    NOTIFY_RAG_BUILDING = "✅ Scraped {count} pages. Building index..."
    NOTIFY_RAG_SUCCESS = "✅ RAG index ready!"
    NOTIFY_RAG_NO_DOCS = "No documents found or RAG not initialized"
    NOTIFY_RAG_FAILED = "RAG scan failed: {error}"
    NOTIFY_RAG_DIRECTORY_NOT_FOUND = "Directory not found: {path}"
    NOTIFY_RAG_ENTER_URL = "Please enter a website URL"
    NOTIFY_RAG_ENTER_PATH = "Please enter a directory path"
    NOTIFY_RAG_FINDING_FILES = "📂 Finding files..."
    
    # Version notifications
    NOTIFY_VERSION_UP_TO_DATE = "✅ Up to date! Version: {version}"
    NOTIFY_VERSION_CHECK_FAILED = "Version check failed: {error}"
    NOTIFY_UPDATE_MANUAL = "Update requires manual download currently. Opening GitHub..."
    
    # Benchmark notifications
    NOTIFY_BENCHMARK_RUNNING = "🏃 Running benchmark... (this will take ~30 seconds)"
    NOTIFY_BENCHMARK_COMPLETE = "✅ Benchmark Complete!"
    NOTIFY_BENCHMARK_FAILED = "❌ Benchmark failed: {error}"
    NOTIFY_BENCHMARK_RESULT = """✅ Benchmark Complete!

📊 Performance: {tokens_per_sec:.1f} tokens/sec
📝 Generated: {tokens} tokens
⏱️ Time: {seconds:.1f} seconds"""
    
    # Diagnostics
    NOTIFY_DIAGNOSTICS_RUNNING = "Running diagnostics..."
    NOTIFY_DIAGNOSTICS_FAILED = "Diagnostics failed: {error}"
    DIAG_LLM_ONLINE = "✅ LLM Backend: Online"
    DIAG_LLM_ERROR = "❌ LLM Backend: Error {code}"
    DIAG_LLM_OFFLINE = "❌ LLM Backend: Offline ({error}...)"
    DIAG_RAG_VECTORS = "{emoji} RAG: {count} vectors"
    DIAG_RAG_NOT_INIT = "{emoji} RAG: Not initialized"
    DIAG_MEMORY = "{emoji} Memory: {percent}% used"
    
    # Generic
    NOTIFY_ERROR = "❌ Error: {error}"
    NOTIFY_SUCCESS = "✅ Success!"
    NOTIFY_WARNING = "⚠️ Warning: {message}"
    NOTIFY_INFO = "ℹ️ {message}"
    NOTIFY_ENTER_BOTH_FIELDS = "Please enter both Repository ID and Filename"
    
    # ==========================================================================
    # WELCOME MESSAGES
    # ==========================================================================
    WELCOME_ZENAI = """👋 **Welcome to ZenAI!**

{source_msg}. I can help you with:
- **Batch Code Review**: Analyze entire directories for security and logic.
- **Deep Research**: Answering questions based on scanned data.
- **Auto-Maintenance**: Pruning zombie processes and scouting for "Shiny" updates.

*Ask me about my 'Anti-Zombie' guardian or 'Batch Review' capabilities!*"""

    WELCOME_SOURCE_WEBSITE = "I scanned the website: **{url}**"
    WELCOME_SOURCE_FILESYSTEM = "I scanned the local directory: **{path}**"
    WELCOME_SOURCE_KB = "I have access to your configured **Knowledge Base**"

    WELCOME_DEFAULT = """👋 **Welcome to ZenAI!**

I'm your AI assistant powered by NiceGUI. I can help you with:
- **Batch Code Review**: Deep architectural scans of multiple files.
- **AI Model Management**: Scouting and downloading "Best-in-Class" models.
- **Active Reliability**: My "Anti-Zombie" guardian ensures clean startups.
- **Voice Intelligence**: High-accuracy transcription and feedback.

*Try pasting a directory path in the Batch menu to get started!*"""

    # ==========================================================================
    # RAG SUCCESS MESSAGE
    # ==========================================================================
    RAG_SUCCESS_MSG = """✅ **RAG Index Ready!**

**Database Stats:**
- 📄 **Pages**: {count}
- 💾 **Size**: {size_mb:.2f} MB
- 📂 **Path**: `{path}`
- 🌐 **Source**: {source}"""

    RAG_SUCCESS_MSG_WITH_TYPES = """✅ **RAG Index Ready!**

**Database Stats:**
- 📁 **Files**: {count}
- 💾 **Size**: {size_mb:.2f} MB
- 📂 **Path**: `{path}`
- 🗂️ **Source**: {source}
- 📄 **Types**: {ext_summary}"""

    # ==========================================================================
    # TOOLTIPS
    # ==========================================================================
    TOOLTIP_DARK_MODE = "Toggle Dark Mode"
    TOOLTIP_ATTACH_FILE = "Attach file"
    TOOLTIP_VOICE_INPUT = "Voice input"
    TOOLTIP_SEND_MESSAGE = "Send message"
    
    # ==========================================================================
    # ERRORS
    # ==========================================================================
    ERROR_WEBSITE_UNREACHABLE = "Cannot access website: {error}"
    ERROR_GENERIC = "An error occurred: {error}"
    
    # ==========================================================================
    # LOADING / WAITING (Fun Rotating Messages)
    # ==========================================================================
    LOADING_WAITING_FOR_USER = [
        "Waiting for your brilliance...",
        "Pondering the digital void...",
        "Contemplating the meaning of code...",
        "Ready when you are!",
        "ZenAI at your service...",
        "Tidying up the neural networks...",
        "Brewing some fresh logic...",
        "Dreaming of electric sheep...",
        "Scanning the horizon for new ideas...",
        "Maintaining flow state..."
    ]

    LOADING_THINKING = [
        "Thinking...",
        "Processing...",
        "Generating response...",
        "Analyzing intent...",
        "Consulting neural pathways...",
        "Scratching my head for the best answer...",
        "Wait a second, let me double-check that logic...",
        "Almost there, just polishing the phrasing...",
        "Consulting the digital oracles...",
        "Hold on, this is a juicy one..."
    ]

    LOADING_SWARM_THINKING = [
        "Consulting expert swarm...",
        "Gathering consensus...",
        "Experts deliberating...",
        "Comparing parallel outputs...",
        "Verifying with the swarm..."
    ]

    LOADING_RAG_THINKING = [
        "Searching knowledge base...",
        "Retrieving relevant chunks...",
        "Consulting your project docs...",
        "Fact-checking against sources...",
        "Reading the fine print..."
    ]

    BATCH_PROGRESS_START = "🚀 Batch analysis started..."
    BATCH_PROGRESS_READING = "📄 Reading file: {filename}..."
    BATCH_PROGRESS_ANALYZING = "🧠 Analyzing content..."
    BATCH_PROGRESS_AI_REVIEW = "🤖 AI code review in progress..."
    BATCH_PROGRESS_WRITING = "💾 Writing analysis to {filename}..."
    BATCH_PROGRESS_COMPLETE = "✅ Batch analysis complete!"
    BATCH_ERROR_FILE = "❌ Error reading {filename}: {error}"
    
    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================
    
    def format(self, key: str, **kwargs) -> str:
        """
        Get a string by key name and format with kwargs.
        
        Usage:
            locale.format('NOTIFY_MODEL_LOADING', model='qwen2.5')
        """
        template = getattr(self, key, key)
        try:
            return template.format(**kwargs)
        except KeyError:
            return template
    
    def get(self, key: str, default: str | None = None) -> str:
        """Get a string by key name, with optional default."""
        return getattr(self, key, default or key)
