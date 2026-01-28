# -*- coding: utf-8 -*-
"""
locales/ro.py - Romanian Locale
Translation for Romanian language.
"""

from .base import BaseLocale


class RomanianLocale(BaseLocale):
    """Romanian (Română) locale."""
    
    LANGUAGE_CODE = "ro"
    LANGUAGE_NAME = "Romanian"
    LANGUAGE_NATIVE = "Română"
    
    # ==========================================================================
    # APP METADATA
    # ==========================================================================
    APP_TITLE = "ZenAI"
    APP_SUBTITLE = "Asistentul Tău AI Local"
    
    # ==========================================================================
    # NAVIGATION
    # ==========================================================================
    NAV_MODELS = "📦 Modele"
    NAV_ENGINE = "🤖 Motor AI"
    NAV_RAG = "📚 Scanează și Învață"
    NAV_SYSTEM = "⚙️ Sistem"
    NAV_POPULAR_MODELS = "🔥 Modele Populare"
    NAV_HF_DOWNLOAD = "📥 Descarcă de pe Hugging Face"
    NAV_LOCAL_MODELS = "📂 Modele Locale"
    NAV_NO_LOCAL_MODELS = "Nu s-au găsit modele locale"
    
    # ==========================================================================
    # BUTTONS
    # ==========================================================================
    BTN_DOWNLOAD = "Descarcă"
    BTN_CANCEL = "Anulează"
    BTN_CLOSE = "Închide"
    BTN_SAVE = "Salvează"
    BTN_LOAD = "Încarcă"
    BTN_SELECT = "Selectează"
    BTN_START = "Pornește"
    BTN_STOP = "Oprește"
    BTN_REFRESH = "Reîmprospătează"
    BTN_SETTINGS = "Setări"
    BTN_OK = "OK"
    BTN_YES = "Da"
    BTN_NO = "Nu"
    
    # ==========================================================================
    # MODEL CATALOG
    # ==========================================================================
    MODEL_PARAMETERS = "Parametri"
    MODEL_QUANTIZATION = "Cuantizare"
    MODEL_SIZE = "Dimensiune"
    MODEL_RAM_NEEDED = "RAM Necesar"
    MODEL_SPEED = "Viteză"
    MODEL_CONTEXT = "Context"
    MODEL_UNKNOWN = "Necunoscut"
    MODEL_SELECT_FILE = "Selectează fișierul de descărcat:"
    MODEL_SELECT_VARIANT = "Selectează varianta modelului"
    MODEL_LOADING_VARIANTS = "Se încarcă variantele..."
    MODEL_NO_VARIANTS = "Nu s-au găsit variante"
    
    # Speed ratings
    MODEL_SPEED_FAST = "⚡ Foarte Rapid"
    MODEL_SPEED_GOOD = "🚀 Rapid"
    MODEL_SPEED_MEDIUM = "⏱️ Mediu"
    MODEL_SPEED_SLOW = "🐢 Lent"
    MODEL_SPEED_VERY_SLOW = "🦥 Foarte Lent"
    
    # ==========================================================================
    # ENGINE / AI
    # ==========================================================================
    ENGINE_LOAD_MODEL = "Încarcă Modelul"
    ENGINE_ENTER_MODEL = "Introdu numele modelului..."
    ENGINE_COT_SWARM = "Roi CoT (Multi-Expert)"
    ENGINE_COT_DESCRIPTION = "Arbitraj prin Consens Paralel"
    ENGINE_QUIET_MODE = "Mod Silențios (Ascunde Experții)"
    ENGINE_QUIET_DESCRIPTION = "Afișează doar răspunsul final verificat"
    ENGINE_SCANNING_SWARM = "Se scanează roiul..."
    ENGINE_EXPERTS_ONLINE = "{count} Experți Online"
    ENGINE_STANDALONE = "Mod Independent ZenAI"
    
    # ==========================================================================
    # SYSTEM
    # ==========================================================================
    SYS_CHECK_VERSION = "Verifică Versiunea llama.cpp"
    SYS_RUN_BENCHMARK = "Rulează Benchmark"
    SYS_DIAGNOSTICS = "Diagnosticare"
    SYS_UPDATE_ENGINE = "Actualizează Motorul"
    SYS_GET_UPDATE = "Obține Actualizare (GitHub)"
    
    # ==========================================================================
    # SETTINGS
    # ==========================================================================
    SETTINGS_TITLE = "Setări"
    SETTINGS_SAVE = "Salvează Setările"
    SETTINGS_RESET = "Resetează la Valori Implicite"
    SETTINGS_SAVED = "Setările au fost salvate cu succes"
    SETTINGS_RESET_CONFIRM = "Ești sigur că vrei să resetezi toate setările?"
    SETTINGS_LANGUAGE_CHANGED = "Limba schimbată în {lang}. Reîmprospătează pagina pentru aplicare."
    
    SETTINGS_CAT_LANGUAGE = "🌐 Limbă"
    SETTINGS_CAT_APPEARANCE = "🎨 Aspect"
    SETTINGS_CAT_AI_MODEL = "🤖 Model AI"
    SETTINGS_CAT_VOICE = "🎤 Voce"
    SETTINGS_CAT_RAG = "📚 RAG"
    SETTINGS_CAT_CHAT = "💬 Chat"
    SETTINGS_CAT_SYSTEM = "⚙️ Sistem"
    
    SETTINGS_UI_LANGUAGE = "Limba Interfeței"
    SETTINGS_UI_LANGUAGE_DESC = "Selectează limba pentru interfața utilizatorului"
    SETTINGS_DARK_MODE = "Mod Întunecat"
    SETTINGS_DARK_MODE_DESC = "Activează tema de culori întunecate"
    SETTINGS_FONT_SIZE = "Dimensiune Font"
    SETTINGS_FONT_SIZE_SMALL = "Mic"
    SETTINGS_FONT_SIZE_MEDIUM = "Mediu"
    SETTINGS_FONT_SIZE_LARGE = "Mare"
    SETTINGS_CHAT_DENSITY = "Densitate Chat"
    SETTINGS_CHAT_DENSITY_COMPACT = "Compact"
    SETTINGS_CHAT_DENSITY_COMFORTABLE = "Confortabil"
    SETTINGS_CHAT_DENSITY_SPACIOUS = "Spațios"
    SETTINGS_SHOW_AVATARS = "Afișează Avataruri"
    SETTINGS_ANIMATE_MESSAGES = "Animează Mesajele"
    
    SETTINGS_DEFAULT_MODEL = "Model Implicit"
    SETTINGS_DEFAULT_MODEL_DESC = "Modelul de încărcat la pornire"
    SETTINGS_TEMPERATURE = "Temperatură"
    SETTINGS_TEMPERATURE_DESC = "Mai mare = mai creativ, Mai mic = mai focalizat (0.0-2.0)"
    SETTINGS_MAX_TOKENS = "Tokeni Maximi"
    SETTINGS_MAX_TOKENS_DESC = "Lungimea maximă a răspunsului"
    SETTINGS_CONTEXT_WINDOW = "Fereastră de Context"
    SETTINGS_CONTEXT_WINDOW_DESC = "Cât istoric de conversație să rețină"
    
    SETTINGS_TTS_ENABLED = "Text-în-Voce"
    SETTINGS_TTS_ENABLED_DESC = "Activează ieșirea vocală"
    SETTINGS_VOICE_SPEED = "Viteza Vocii"
    SETTINGS_VOICE_SPEED_DESC = "Rata de vorbire TTS (0.5x - 2.0x)"
    SETTINGS_AUTO_SPEAK = "Vorbește Automat Răspunsurile"
    SETTINGS_AUTO_SPEAK_DESC = "Citește automat răspunsurile cu voce tare"
    SETTINGS_RECORDING_DURATION = "Durata Înregistrării"
    SETTINGS_RECORDING_DURATION_DESC = "Timp de înregistrare vocală (secunde)"
    
    SETTINGS_RAG_ENABLED = "Activează RAG"
    SETTINGS_RAG_ENABLED_DESC = "Folosește baza de cunoștințe pentru răspunsuri"
    SETTINGS_CHUNK_SIZE = "Dimensiune Fragment"
    SETTINGS_CHUNK_SIZE_DESC = "Dimensiunea segmentului de text pentru indexare"
    SETTINGS_SIMILARITY_THRESHOLD = "Prag de Similitudine"
    SETTINGS_SIMILARITY_THRESHOLD_DESC = "Scor minim de relevanță (0.0-1.0)"
    SETTINGS_MAX_RESULTS = "Rezultate Maxime"
    SETTINGS_MAX_RESULTS_DESC = "Numărul de surse de recuperat"
    
    SETTINGS_SHOW_TIMESTAMPS = "Afișează Marcaje Temporale"
    SETTINGS_SHOW_TIMESTAMPS_DESC = "Afișează ora pe fiecare mesaj"
    SETTINGS_AUTO_SCROLL = "Derulare Automată"
    SETTINGS_AUTO_SCROLL_DESC = "Derulează automat la mesaje noi"
    SETTINGS_STREAM_RESPONSES = "Transmite Răspunsurile"
    SETTINGS_STREAM_RESPONSES_DESC = "Afișează răspunsul pe măsură ce este generat"
    SETTINGS_SAVE_CONVERSATIONS = "Salvează Conversațiile"
    SETTINGS_SAVE_CONVERSATIONS_DESC = "Reține istoricul între sesiuni"
    
    SETTINGS_API_PORT = "Port API"
    SETTINGS_API_PORT_DESC = "Portul serverului backend LLM"
    SETTINGS_MODELS_DIRECTORY = "Director Modele"
    SETTINGS_MODELS_DIRECTORY_DESC = "Folder cu fișierele de model GGUF"
    SETTINGS_CHECK_UPDATES = "Verifică Actualizări la Pornire"
    SETTINGS_CHECK_UPDATES_DESC = "Caută versiuni noi automat"
    SETTINGS_AUTO_START_BACKEND = "Pornește Backend-ul Automat"
    SETTINGS_AUTO_START_BACKEND_DESC = "Lansează serverul LLM cu aplicația"
    SETTINGS_LOG_LEVEL = "Nivel Jurnal"
    SETTINGS_LOG_LEVEL_DESC = "Verbozitatea jurnalelor aplicației"
    
    # ==========================================================================
    # RAG / SCAN & LEARN
    # ==========================================================================
    RAG_SCAN_LEARN = "Scanează și Învață (RAG)"
    RAG_ENABLE = "Activează Scanează și Învață (RAG)"
    RAG_SCAN_READ = "Scanează și Citește"
    RAG_START_SCANNING = "Începe Scanarea"
    RAG_SOURCE_TYPE = "Tip Sursă"
    RAG_WEBSITE = "Site Web"
    RAG_LOCAL_DIRECTORY = "Director Local"
    RAG_WEBSITE_URL = "URL Site Web"
    RAG_MAX_PAGES = "Pagini Max"
    RAG_DIRECTORY_PATH = "Cale Director"
    RAG_MAX_FILES = "Fișiere Max"
    RAG_START_SCAN = "Începe Scanarea"
    RAG_ANSWERED_FROM_SOURCE = "**🔍 Răspuns din Sursa de Date**"
    RAG_VIEW_SOURCES = "📂 Vezi Datele Sursă"
    
    # ==========================================================================
    # CHAT INTERFACE
    # ==========================================================================
    CHAT_PLACEHOLDER = "Scrie un mesaj..."
    CHAT_PLACEHOLDER_ZENAI = "Întreabă-mă orice..."
    CHAT_QUICK_ACTIONS = "Acțiuni Rapide"
    CHAT_CHECK_MODEL = "Verifică Starea Modelului"
    CHAT_LATEST_LLAMA = "Ultimul llama.cpp"
    CHAT_RUN_BENCHMARK = "Rulează Benchmark"
    CHAT_HELP = "Ajutor"
    CHAT_YOU = "Tu"
    CHAT_THINKING = "Gândesc..."
    CHAT_READY = "Pregătit"
    CHAT_RECORDING = "🔴 Înregistrez (5s)..."
    CHAT_TRANSCRIBING = "Transcriu..."
    
    # ==========================================================================
    # FILE UPLOAD
    # ==========================================================================
    UPLOAD_ATTACHED = "📎 {filename} ({size} caractere)"
    UPLOAD_SUCCESS = "{filename} atașat"
    UPLOAD_FAILED = "Încărcare eșuată: {error}"
    
    # ==========================================================================
    # VOICE
    # ==========================================================================
    VOICE_RECORDING = "🔴 Înregistrez ({seconds}s)..."
    VOICE_TRANSCRIBING = "Transcriu..."
    VOICE_TRANSCRIBED = "Transcris!"
    VOICE_NO_SPEECH = "Nu s-a detectat voce"
    VOICE_ERROR = "Eroare Voce: {error}"
    VOICE_NOT_AVAILABLE = "TTS indisponibil (lipsește pyttsx3)"
    
    # ==========================================================================
    # NOTIFICATIONS & MESSAGES
    # ==========================================================================
    # Model notifications
    NOTIFY_MODEL_LOADING = "🔄 Se încarcă modelul: {model}..."
    NOTIFY_MODEL_READY = "✅ Model pregătit: {model}"
    NOTIFY_MODEL_ACTIVE = "✅ Model activ: {model}"
    NOTIFY_MODEL_SET = "✅ Model activ setat: {model}"
    
    # Download notifications
    NOTIFY_DOWNLOAD_STARTING = "🚀 Se începe descărcarea: {filename}..."
    NOTIFY_DOWNLOAD_STARTED = "✅ Descărcare începută! Verifică progresul în terminal."
    NOTIFY_DOWNLOAD_FAILED = "❌ Descărcare eșuată: {error}"
    NOTIFY_DOWNLOAD_ERROR = "❌ Eroare: {error}"
    NOTIFY_HUB_CONNECTION_ERROR = "❌ Nu se poate conecta la Hub. Rulează pe portul 8002?"
    
    # Upload/attachment notifications
    NOTIFY_ATTACHED = "{name} atașat"
    NOTIFY_UPLOAD_FAILED = "Încărcare eșuată: {error}"
    
    # Voice notifications  
    NOTIFY_SOUNDDEVICE_MISSING = "Eroare: SoundDevice negăsit (Mod headless?)"
    NOTIFY_TRANSCRIBED = "Transcris!"
    NOTIFY_NO_SPEECH = "Nu s-a detectat voce"
    NOTIFY_TRANSCRIPTION_FAILED = "Transcriere Eșuată: {error}"
    NOTIFY_VOICE_ERROR = "Eroare Voce: {error}"
    
    # RAG notifications
    NOTIFY_RAG_ENABLED = "Mod RAG activat"
    NOTIFY_RAG_DISABLED = "Mod RAG dezactivat"
    NOTIFY_RAG_SCANNING = "🔍 Se scanează {url}..."
    NOTIFY_RAG_SCRAPING = "📄 Extragere ({count}/{total}) - ETA: {eta}"
    NOTIFY_RAG_BUILDING = "✅ {count} pagini extrase. Se construiește indexul..."
    NOTIFY_RAG_SUCCESS = "✅ Index RAG pregătit!"
    NOTIFY_RAG_NO_DOCS = "Nu s-au găsit documente sau RAG neinițializat"
    NOTIFY_RAG_FAILED = "Scanare RAG eșuată: {error}"
    NOTIFY_RAG_DIRECTORY_NOT_FOUND = "Director negăsit: {path}"
    NOTIFY_RAG_ENTER_URL = "Te rog introdu un URL de site web"
    NOTIFY_RAG_ENTER_PATH = "Te rog introdu o cale de director"
    NOTIFY_RAG_FINDING_FILES = "📂 Se caută fișierele..."
    
    # Version notifications
    NOTIFY_VERSION_UP_TO_DATE = "✅ La zi! Versiune: {version}"
    NOTIFY_VERSION_CHECK_FAILED = "Verificare versiune eșuată: {error}"
    NOTIFY_UPDATE_MANUAL = "Actualizarea necesită descărcare manuală momentan. Se deschide GitHub..."
    
    # Benchmark notifications
    NOTIFY_BENCHMARK_RUNNING = "🏃 Se rulează benchmark... (va dura ~30 secunde)"
    NOTIFY_BENCHMARK_COMPLETE = "✅ Benchmark Complet!"
    NOTIFY_BENCHMARK_FAILED = "❌ Benchmark eșuat: {error}"
    NOTIFY_BENCHMARK_RESULT = """✅ Benchmark Complet!

📊 Performanță: {tokens_per_sec:.1f} tokeni/sec
📝 Generați: {tokens} tokeni
⏱️ Timp: {seconds:.1f} secunde"""
    
    # Diagnostics
    NOTIFY_DIAGNOSTICS_RUNNING = "Se rulează diagnosticarea..."
    NOTIFY_DIAGNOSTICS_FAILED = "Diagnosticare eșuată: {error}"
    DIAG_LLM_ONLINE = "✅ Backend LLM: Online"
    DIAG_LLM_ERROR = "❌ Backend LLM: Eroare {code}"
    DIAG_LLM_OFFLINE = "❌ Backend LLM: Offline ({error}...)"
    DIAG_RAG_VECTORS = "{emoji} RAG: {count} vectori"
    DIAG_RAG_NOT_INIT = "{emoji} RAG: Neinițializat"
    DIAG_MEMORY = "{emoji} Memorie: {percent}% folosită"
    
    # Generic
    NOTIFY_ERROR = "❌ Eroare: {error}"
    NOTIFY_SUCCESS = "✅ Succes!"
    NOTIFY_WARNING = "⚠️ Avertisment: {message}"
    NOTIFY_INFO = "ℹ️ {message}"
    NOTIFY_ENTER_BOTH_FIELDS = "Te rog introdu atât ID-ul Repository-ului cât și Numele Fișierului"
    
    # ==========================================================================
    # WELCOME MESSAGES
    # ==========================================================================
    WELCOME_ZENAI = """👋 **Bine ai venit la ZenAI!**

{source_msg}. Te pot ajuta cu:
- **Revizuire Cod în Lot**: Analiză profundă a directoarelor întregi.
- **Cercetare Avansată**: Răspunsuri bazate pe datele scanate.
- **Auto-Mentenanță**: Eliminarea proceselor 'Zombie' și căutarea de actualizări.

*Întreabă-mă despre gardianul 'Anti-Zombie' sau capacitățile de 'Batch Review'!*"""

    WELCOME_SOURCE_WEBSITE = "Am scanat site-ul web: **{url}**"
    WELCOME_SOURCE_FILESYSTEM = "Am scanat directorul local: **{path}**"
    WELCOME_SOURCE_KB = "Am acces la **Baza ta de Cunoștințe** configurată"

    WELCOME_DEFAULT = """👋 **Bine ai venit la ZenAI!**

Sunt asistentul tău AI alimentat de NiceGUI. Te pot ajuta cu:
- **Revizuire Cod în Lot**: Scanări arhitecturale profunde.
- **Management Modele AI**: Căutarea și descărcarea modelelor 'Best-in-Class'.
- **Fiabilitate Activă**: Gardianul 'Anti-Zombie' asigură porniri curate.
- **Inteligență Vocală**: Transcriere și feedback de înaltă precizie.

*Încearcă să introduci o cale de director în meniul Batch pentru a începe!*"""

    # ==========================================================================
    # RAG SUCCESS MESSAGE
    # ==========================================================================
    RAG_SUCCESS_MSG = """✅ **Index RAG Pregătit!**

**Statistici Bază de Date:**
- 📄 **Pagini**: {count}
- 💾 **Dimensiune**: {size_mb:.2f} MB
- 📂 **Cale**: `{path}`
- 🌐 **Sursă**: {source}"""

    RAG_SUCCESS_MSG_WITH_TYPES = """✅ **Index RAG Pregătit!**

**Statistici Bază de Date:**
- 📁 **Fișiere**: {count}
- 💾 **Dimensiune**: {size_mb:.2f} MB
- 📂 **Cale**: `{path}`
- 🗂️ **Sursă**: {source}
- 📄 **Tipuri**: {ext_summary}"""

    # ==========================================================================
    # TOOLTIPS
    # ==========================================================================
    TOOLTIP_DARK_MODE = "Comută Modul Întunecat"
    TOOLTIP_ATTACH_FILE = "Atașează fișier"
    TOOLTIP_VOICE_INPUT = "Intrare vocală"
    TOOLTIP_SEND_MESSAGE = "Trimite mesajul"
    
    # ==========================================================================
    # ERRORS
    # ==========================================================================
    ERROR_WEBSITE_UNREACHABLE = "Nu se poate accesa site-ul web: {error}"
    ERROR_GENERIC = "A apărut o eroare: {error}"

    LOADING_THINKING = [
        "Gândesc...",
        "Procesez...",
        "Generez răspunsul...",
        "Analizez intenția...",
        "Consult căile neuronale...",
        "Mă scarpin în cap pentru cel mai bun răspuns...",
        "Stai o secundă, să verific logica...",
        "Aproape gata, mai cizelez puțin frazarea...",
        "Consult oracolul digital...",
        "Stai așa, asta e o întrebare interesantă..."
    ]

    LOADING_SWARM_THINKING = [
        "Consult roiul de experți...",
        "Adun consensul...",
        "Experții deliberează...",
        "Compar rezultatele paralele...",
        "Verific cu roiul..."
    ]

    LOADING_RAG_THINKING = [
        "Caut în baza de cunoștințe...",
        "Recuperez fragmente relevante...",
        "Consult documentele proiectului...",
        "Verific faptele cu sursele...",
        "Citesc detaliile..."
    ]

    # ======================================================================
    # BATCH / ANALYSIS
    # ======================================================================
    BATCH_MENU = "Sarcini în Lot"
    BATCH_CREATE_REVIEW = "Creare Revizuire Cod"
    BATCH_FILES_PLACEHOLDER = "Introduceți căile fișierelor (separate prin virgulă)"
    BATCH_ENQUEUE = "Adaugă în Coadă"
    ANALYSIS_SAVED = "Analiza a fost salvată în _zena_analisis"

    BATCH_PROGRESS_START = "🚀 Analiza în lot a început..."
    BATCH_PROGRESS_READING = "📄 Se citește fișierul: {filename}..."
    BATCH_PROGRESS_ANALYZING = "🧠 Se analizează conținutul..."
    BATCH_PROGRESS_AI_REVIEW = "🤖 Revizuire cod AI în curs..."
    BATCH_PROGRESS_WRITING = "💾 Se scrie analiza în {filename}..."
    BATCH_PROGRESS_COMPLETE = "✅ Analiza în lot este finalizată!"
    BATCH_ERROR_FILE = "❌ Eroare la citirea {filename}: {error}"
