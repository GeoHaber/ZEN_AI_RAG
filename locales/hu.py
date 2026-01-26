# -*- coding: utf-8 -*-
"""
locales/hu.py - Hungarian Locale
Translation for Hungarian language.
"""

from .base import BaseLocale


class HungarianLocale(BaseLocale):
    """Hungarian (Magyar) locale."""
    
    LANGUAGE_CODE = "hu"
    LANGUAGE_NAME = "Hungarian"
    LANGUAGE_NATIVE = "Magyar"
    
    # ==========================================================================
    # APP METADATA
    # ==========================================================================
    APP_TITLE = "ZenAI"
    APP_SUBTITLE = "A Helyi AI Asszisztensed"
    
    # ==========================================================================
    # NAVIGATION
    # ==========================================================================
    NAV_MODELS = "📦 Modellek"
    NAV_ENGINE = "🤖 AI Motor"
    NAV_RAG = "📚 Szkennelés és Tanulás"
    NAV_SYSTEM = "⚙️ Rendszer"
    NAV_POPULAR_MODELS = "🔥 Népszerű Modellek"
    NAV_HF_DOWNLOAD = "📥 Letöltés Hugging Face-ről"
    NAV_LOCAL_MODELS = "📂 Helyi Modellek"
    NAV_NO_LOCAL_MODELS = "Nem található helyi modell"
    
    # ==========================================================================
    # BUTTONS
    # ==========================================================================
    BTN_DOWNLOAD = "Letöltés"
    BTN_CANCEL = "Mégse"
    BTN_CLOSE = "Bezárás"
    BTN_SAVE = "Mentés"
    BTN_LOAD = "Betöltés"
    BTN_SELECT = "Kiválasztás"
    BTN_START = "Indítás"
    BTN_STOP = "Leállítás"
    BTN_REFRESH = "Frissítés"
    BTN_SETTINGS = "Beállítások"
    BTN_OK = "OK"
    BTN_YES = "Igen"
    BTN_NO = "Nem"
    
    # ==========================================================================
    # MODEL CATALOG
    # ==========================================================================
    MODEL_PARAMETERS = "Paraméterek"
    MODEL_QUANTIZATION = "Kvantálás"
    MODEL_SIZE = "Méret"
    MODEL_RAM_NEEDED = "Szükséges RAM"
    MODEL_SPEED = "Sebesség"
    MODEL_CONTEXT = "Kontextus"
    MODEL_UNKNOWN = "Ismeretlen"
    MODEL_SELECT_FILE = "Válaszd ki a letöltendő fájlt:"
    MODEL_SELECT_VARIANT = "Válaszd ki a modell változatot"
    MODEL_LOADING_VARIANTS = "Változatok betöltése..."
    MODEL_NO_VARIANTS = "Nem találhatók változatok"
    
    # Speed ratings
    MODEL_SPEED_FAST = "⚡ Nagyon Gyors"
    MODEL_SPEED_GOOD = "🚀 Gyors"
    MODEL_SPEED_MEDIUM = "⏱️ Közepes"
    MODEL_SPEED_SLOW = "🐢 Lassú"
    MODEL_SPEED_VERY_SLOW = "🦥 Nagyon Lassú"
    
    # ==========================================================================
    # ENGINE / AI
    # ==========================================================================
    ENGINE_LOAD_MODEL = "Modell Betöltése"
    ENGINE_ENTER_MODEL = "Add meg a modell nevét..."
    ENGINE_COT_SWARM = "CoT Raj (Több-Szakértő)"
    ENGINE_COT_DESCRIPTION = "Párhuzamos Konszenzus Arbitrázs"
    ENGINE_QUIET_MODE = "Csendes Mód (Szakértők Elrejtése)"
    ENGINE_QUIET_DESCRIPTION = "Csak a végleges ellenőrzött válasz megjelenítése"
    ENGINE_SCANNING_SWARM = "Raj szkennelése..."
    ENGINE_EXPERTS_ONLINE = "{count} Szakértő Online"
    ENGINE_STANDALONE = "ZenAI Önálló Mód"
    
    # ==========================================================================
    # SYSTEM
    # ==========================================================================
    SYS_CHECK_VERSION = "llama.cpp Verzió Ellenőrzése"
    SYS_RUN_BENCHMARK = "Benchmark Futtatása"
    SYS_DIAGNOSTICS = "Diagnosztika"
    SYS_UPDATE_ENGINE = "Motor Frissítése"
    SYS_GET_UPDATE = "Frissítés Letöltése (GitHub)"
    
    # ==========================================================================
    # SETTINGS
    # ==========================================================================
    SETTINGS_TITLE = "Beállítások"
    SETTINGS_SAVE = "Beállítások Mentése"
    SETTINGS_RESET = "Alapértékek Visszaállítása"
    SETTINGS_SAVED = "Beállítások sikeresen mentve"
    SETTINGS_RESET_CONFIRM = "Biztosan visszaállítod az összes beállítást?"
    SETTINGS_LANGUAGE_CHANGED = "Nyelv megváltoztatva: {lang}. Frissítsd az oldalt az alkalmazáshoz."
    
    SETTINGS_CAT_LANGUAGE = "🌐 Nyelv"
    SETTINGS_CAT_APPEARANCE = "🎨 Megjelenés"
    SETTINGS_CAT_AI_MODEL = "🤖 AI Modell"
    SETTINGS_CAT_VOICE = "🎤 Hang"
    SETTINGS_CAT_RAG = "📚 RAG"
    SETTINGS_CAT_CHAT = "💬 Chat"
    SETTINGS_CAT_SYSTEM = "⚙️ Rendszer"
    
    SETTINGS_UI_LANGUAGE = "Felület Nyelve"
    SETTINGS_UI_LANGUAGE_DESC = "Válaszd ki a felhasználói felület nyelvét"
    SETTINGS_DARK_MODE = "Sötét Mód"
    SETTINGS_DARK_MODE_DESC = "Sötét színséma engedélyezése"
    SETTINGS_FONT_SIZE = "Betűméret"
    SETTINGS_FONT_SIZE_SMALL = "Kicsi"
    SETTINGS_FONT_SIZE_MEDIUM = "Közepes"
    SETTINGS_FONT_SIZE_LARGE = "Nagy"
    SETTINGS_CHAT_DENSITY = "Chat Sűrűség"
    SETTINGS_CHAT_DENSITY_COMPACT = "Kompakt"
    SETTINGS_CHAT_DENSITY_COMFORTABLE = "Kényelmes"
    SETTINGS_CHAT_DENSITY_SPACIOUS = "Tágas"
    SETTINGS_SHOW_AVATARS = "Avatarok Megjelenítése"
    SETTINGS_ANIMATE_MESSAGES = "Üzenetek Animálása"
    
    SETTINGS_DEFAULT_MODEL = "Alapértelmezett Modell"
    SETTINGS_DEFAULT_MODEL_DESC = "Indításkor betöltendő modell"
    SETTINGS_TEMPERATURE = "Hőmérséklet"
    SETTINGS_TEMPERATURE_DESC = "Magasabb = kreatívabb, Alacsonyabb = fókuszáltabb (0.0-2.0)"
    SETTINGS_MAX_TOKENS = "Maximum Tokenek"
    SETTINGS_MAX_TOKENS_DESC = "Maximális válasz hossz"
    SETTINGS_CONTEXT_WINDOW = "Kontextus Ablak"
    SETTINGS_CONTEXT_WINDOW_DESC = "Mennyi beszélgetés előzményt őrizzen meg"
    
    SETTINGS_TTS_ENABLED = "Szövegfelolvasás"
    SETTINGS_TTS_ENABLED_DESC = "Hang kimenet engedélyezése"
    SETTINGS_VOICE_SPEED = "Hang Sebesség"
    SETTINGS_VOICE_SPEED_DESC = "TTS beszédsebesség (0.5x - 2.0x)"
    SETTINGS_AUTO_SPEAK = "Válaszok Automatikus Felolvasása"
    SETTINGS_AUTO_SPEAK_DESC = "AI válaszok automatikus felolvasása"
    SETTINGS_RECORDING_DURATION = "Felvétel Időtartama"
    SETTINGS_RECORDING_DURATION_DESC = "Hangfelvétel időtartama (másodperc)"
    
    SETTINGS_RAG_ENABLED = "RAG Engedélyezése"
    SETTINGS_RAG_ENABLED_DESC = "Tudásbázis használata válaszokhoz"
    SETTINGS_CHUNK_SIZE = "Darab Méret"
    SETTINGS_CHUNK_SIZE_DESC = "Szöveg szegmens méret indexeléshez"
    SETTINGS_SIMILARITY_THRESHOLD = "Hasonlósági Küszöb"
    SETTINGS_SIMILARITY_THRESHOLD_DESC = "Minimális relevancia pontszám (0.0-1.0)"
    SETTINGS_MAX_RESULTS = "Maximum Eredmények"
    SETTINGS_MAX_RESULTS_DESC = "Lekérdezendő források száma"
    
    SETTINGS_SHOW_TIMESTAMPS = "Időbélyegek Megjelenítése"
    SETTINGS_SHOW_TIMESTAMPS_DESC = "Idő megjelenítése minden üzeneten"
    SETTINGS_AUTO_SCROLL = "Automatikus Görgetés"
    SETTINGS_AUTO_SCROLL_DESC = "Automatikusan görget az új üzenetekhez"
    SETTINGS_STREAM_RESPONSES = "Válaszok Streamelése"
    SETTINGS_STREAM_RESPONSES_DESC = "Válasz megjelenítése generálás közben"
    SETTINGS_SAVE_CONVERSATIONS = "Beszélgetések Mentése"
    SETTINGS_SAVE_CONVERSATIONS_DESC = "Előzmények megőrzése munkamenetek között"
    
    SETTINGS_API_PORT = "API Port"
    SETTINGS_API_PORT_DESC = "LLM backend szerver portja"
    SETTINGS_MODELS_DIRECTORY = "Modellek Könyvtára"
    SETTINGS_MODELS_DIRECTORY_DESC = "GGUF modell fájlokat tartalmazó mappa"
    SETTINGS_CHECK_UPDATES = "Frissítések Ellenőrzése Indításkor"
    SETTINGS_CHECK_UPDATES_DESC = "Új verziók automatikus keresése"
    SETTINGS_AUTO_START_BACKEND = "Backend Automatikus Indítása"
    SETTINGS_AUTO_START_BACKEND_DESC = "LLM szerver indítása az alkalmazással"
    SETTINGS_LOG_LEVEL = "Napló Szint"
    SETTINGS_LOG_LEVEL_DESC = "Alkalmazás naplók részletessége"
    
    # ==========================================================================
    # RAG / SCAN & LEARN
    # ==========================================================================
    RAG_SCAN_LEARN = "Szkennelés és Tanulás (RAG)"
    RAG_ENABLE = "Szkennelés és Tanulás Engedélyezése (RAG)"
    RAG_SCAN_READ = "Szkennelés és Olvasás"
    RAG_START_SCANNING = "Szkennelés Indítása"
    RAG_SOURCE_TYPE = "Forrás Típusa"
    RAG_WEBSITE = "Weboldal"
    RAG_LOCAL_DIRECTORY = "Helyi Mappa"
    RAG_WEBSITE_URL = "Weboldal URL"
    RAG_MAX_PAGES = "Max Oldalak"
    RAG_DIRECTORY_PATH = "Mappa Elérési Útja"
    RAG_MAX_FILES = "Max Fájlok"
    RAG_START_SCAN = "Szkennelés Indítása"
    RAG_ANSWERED_FROM_SOURCE = "**🔍 Válasz az Adatforrásból**"
    RAG_VIEW_SOURCES = "📂 Forrásadatok Megtekintése"
    
    # ==========================================================================
    # CHAT INTERFACE
    # ==========================================================================
    CHAT_PLACEHOLDER = "Írj egy üzenetet..."
    CHAT_PLACEHOLDER_ZENAI = "Kérdezz bármit..."
    CHAT_QUICK_ACTIONS = "Gyors Műveletek"
    CHAT_CHECK_MODEL = "Modell Állapot Ellenőrzése"
    CHAT_LATEST_LLAMA = "Legújabb llama.cpp"
    CHAT_RUN_BENCHMARK = "Benchmark Futtatása"
    CHAT_HELP = "Súgó"
    CHAT_YOU = "Te"
    CHAT_THINKING = "Gondolkodom..."
    CHAT_READY = "Kész"
    CHAT_RECORDING = "🔴 Felvétel (5mp)..."
    CHAT_TRANSCRIBING = "Átírás..."
    
    # ==========================================================================
    # FILE UPLOAD
    # ==========================================================================
    UPLOAD_ATTACHED = "📎 {filename} ({size} karakter)"
    UPLOAD_SUCCESS = "{filename} csatolva"
    UPLOAD_FAILED = "Feltöltés sikertelen: {error}"
    
    # ==========================================================================
    # VOICE
    # ==========================================================================
    VOICE_RECORDING = "🔴 Felvétel ({seconds}mp)..."
    VOICE_TRANSCRIBING = "Átírás..."
    VOICE_TRANSCRIBED = "Átírva!"
    VOICE_NO_SPEECH = "Nem észlelt beszéd"
    VOICE_ERROR = "Hang Hiba: {error}"
    VOICE_NOT_AVAILABLE = "TTS nem érhető el (hiányzik a pyttsx3)"
    
    # ==========================================================================
    # NOTIFICATIONS & MESSAGES
    # ==========================================================================
    # Model notifications
    NOTIFY_MODEL_LOADING = "🔄 Modell betöltése: {model}..."
    NOTIFY_MODEL_READY = "✅ Modell kész: {model}"
    NOTIFY_MODEL_ACTIVE = "✅ Aktív modell: {model}"
    NOTIFY_MODEL_SET = "✅ Aktív modell beállítva: {model}"
    
    # Download notifications
    NOTIFY_DOWNLOAD_STARTING = "🚀 Letöltés indítása: {filename}..."
    NOTIFY_DOWNLOAD_STARTED = "✅ Letöltés elindult! Ellenőrizd a haladást a terminálban."
    NOTIFY_DOWNLOAD_FAILED = "❌ Letöltés sikertelen: {error}"
    NOTIFY_DOWNLOAD_ERROR = "❌ Hiba: {error}"
    NOTIFY_HUB_CONNECTION_ERROR = "❌ Nem lehet csatlakozni a Hub-hoz. Fut a 8002-es porton?"
    
    # Upload/attachment notifications
    NOTIFY_ATTACHED = "{name} csatolva"
    NOTIFY_UPLOAD_FAILED = "Feltöltés sikertelen: {error}"
    
    # Voice notifications  
    NOTIFY_SOUNDDEVICE_MISSING = "Hiba: SoundDevice nem található (Headless mód?)"
    NOTIFY_TRANSCRIBED = "Átírva!"
    NOTIFY_NO_SPEECH = "Nem észlelt beszéd"
    NOTIFY_TRANSCRIPTION_FAILED = "Átírás Sikertelen: {error}"
    NOTIFY_VOICE_ERROR = "Hang Hiba: {error}"
    
    # RAG notifications
    NOTIFY_RAG_ENABLED = "RAG mód engedélyezve"
    NOTIFY_RAG_DISABLED = "RAG mód letiltva"
    NOTIFY_RAG_SCANNING = "🔍 Szkennelés: {url}..."
    NOTIFY_RAG_SCRAPING = "📄 Kinyerés ({count}/{total}) - Várható idő: {eta}"
    NOTIFY_RAG_BUILDING = "✅ {count} oldal kinyerve. Index építése..."
    NOTIFY_RAG_SUCCESS = "✅ RAG index kész!"
    NOTIFY_RAG_NO_DOCS = "Nem találhatók dokumentumok vagy a RAG nincs inicializálva"
    NOTIFY_RAG_FAILED = "RAG szkennelés sikertelen: {error}"
    NOTIFY_RAG_DIRECTORY_NOT_FOUND = "Mappa nem található: {path}"
    NOTIFY_RAG_ENTER_URL = "Kérlek add meg a weboldal URL-jét"
    NOTIFY_RAG_ENTER_PATH = "Kérlek add meg a mappa elérési útját"
    NOTIFY_RAG_FINDING_FILES = "📂 Fájlok keresése..."
    
    # Version notifications
    NOTIFY_VERSION_UP_TO_DATE = "✅ Naprakész! Verzió: {version}"
    NOTIFY_VERSION_CHECK_FAILED = "Verzió ellenőrzés sikertelen: {error}"
    NOTIFY_UPDATE_MANUAL = "A frissítéshez jelenleg manuális letöltés szükséges. GitHub megnyitása..."
    
    # Benchmark notifications
    NOTIFY_BENCHMARK_RUNNING = "🏃 Benchmark futtatása... (kb. 30 másodperc)"
    NOTIFY_BENCHMARK_COMPLETE = "✅ Benchmark Kész!"
    NOTIFY_BENCHMARK_FAILED = "❌ Benchmark sikertelen: {error}"
    NOTIFY_BENCHMARK_RESULT = """✅ Benchmark Kész!

📊 Teljesítmény: {tokens_per_sec:.1f} token/mp
📝 Generált: {tokens} token
⏱️ Idő: {seconds:.1f} másodperc"""
    
    # Diagnostics
    NOTIFY_DIAGNOSTICS_RUNNING = "Diagnosztika futtatása..."
    NOTIFY_DIAGNOSTICS_FAILED = "Diagnosztika sikertelen: {error}"
    DIAG_LLM_ONLINE = "✅ LLM Backend: Online"
    DIAG_LLM_ERROR = "❌ LLM Backend: Hiba {code}"
    DIAG_LLM_OFFLINE = "❌ LLM Backend: Offline ({error}...)"
    DIAG_RAG_VECTORS = "{emoji} RAG: {count} vektor"
    DIAG_RAG_NOT_INIT = "{emoji} RAG: Nincs inicializálva"
    DIAG_MEMORY = "{emoji} Memória: {percent}% használatban"
    
    # Generic
    NOTIFY_ERROR = "❌ Hiba: {error}"
    NOTIFY_SUCCESS = "✅ Sikeres!"
    NOTIFY_WARNING = "⚠️ Figyelmeztetés: {message}"
    NOTIFY_INFO = "ℹ️ {message}"
    NOTIFY_ENTER_BOTH_FIELDS = "Kérlek add meg a Repository ID-t és a Fájlnevet is"
    
    # ==========================================================================
    # WELCOME MESSAGES
    # ==========================================================================
    WELCOME_ZENAI = """👋 **Üdvözöllek a ZenAI-ban!**

{source_msg}. Segíthetek neked:
- Kérdések megválaszolásában a tartalomról
- Információk gyors megtalálásában
- Útmutatás nyújtásában

*Kérdezz, ha szeretnél!*"""

    WELCOME_SOURCE_WEBSITE = "Beszkenneltem a weboldalt: **{url}**"
    WELCOME_SOURCE_FILESYSTEM = "Beszkenneltem a helyi mappát: **{path}**"
    WELCOME_SOURCE_KB = "Hozzáférek a beállított **Tudásbázisodhoz**"

    WELCOME_DEFAULT = """👋 **Üdvözöllek a ZenAI-ban!**

A NiceGUI által hajtott AI asszisztensed vagyok. Segíthetek neked:
- AI modellek kezelésében
- Kódfájlok elemzésében
- Benchmarkok futtatásában
- Hangátírásban

*Ne feledd, még mindig tanulok és fejlődöm!*"""

    # ==========================================================================
    # RAG SUCCESS MESSAGE
    # ==========================================================================
    RAG_SUCCESS_MSG = """✅ **RAG Index Kész!**

**Adatbázis Statisztikák:**
- 📄 **Oldalak**: {count}
- 💾 **Méret**: {size_mb:.2f} MB
- 📂 **Útvonal**: `{path}`
- 🌐 **Forrás**: {source}"""

    RAG_SUCCESS_MSG_WITH_TYPES = """✅ **RAG Index Kész!**

**Adatbázis Statisztikák:**
- 📁 **Fájlok**: {count}
- 💾 **Méret**: {size_mb:.2f} MB
- 📂 **Útvonal**: `{path}`
- 🗂️ **Forrás**: {source}
- 📄 **Típusok**: {ext_summary}"""

    # ==========================================================================
    # TOOLTIPS
    # ==========================================================================
    TOOLTIP_DARK_MODE = "Sötét Mód Váltása"
    TOOLTIP_ATTACH_FILE = "Fájl csatolása"
    TOOLTIP_VOICE_INPUT = "Hangbemenet"
    TOOLTIP_SEND_MESSAGE = "Üzenet küldése"
    
    # ==========================================================================
    # ERRORS
    # ==========================================================================
    ERROR_WEBSITE_UNREACHABLE = "Nem érhető el a weboldal: {error}"
    ERROR_GENERIC = "Hiba történt: {error}"
