# -*- coding: utf-8 -*-
"""
locales/he.py - Hebrew Locale
Translation for Hebrew language.
Note: Hebrew is RTL (right-to-left) language.
"""

from .base import BaseLocale


class HebrewLocale(BaseLocale):
    """Hebrew (עברית) locale."""
    
    LANGUAGE_CODE = "he"
    LANGUAGE_NAME = "Hebrew"
    LANGUAGE_NATIVE = "עברית"
    RTL = True  # Right-to-left language flag
    
    # ==========================================================================
    # APP METADATA
    # ==========================================================================
    APP_TITLE = "ZenAI"
    APP_SUBTITLE = "העוזר המקומי שלך לבינה מלאכותית"
    
    # ==========================================================================
    # NAVIGATION
    # ==========================================================================
    NAV_MODELS = "📦 מודלים"
    NAV_ENGINE = "🤖 מנוע AI"
    NAV_RAG = "📚 סרוק ולמד"
    NAV_SYSTEM = "⚙️ מערכת"
    NAV_POPULAR_MODELS = "🔥 מודלים פופולריים"
    NAV_HF_DOWNLOAD = "📥 הורד מ-Hugging Face"
    NAV_LOCAL_MODELS = "📂 מודלים מקומיים"
    NAV_NO_LOCAL_MODELS = "לא נמצאו מודלים מקומיים"
    
    # ==========================================================================
    # BUTTONS
    # ==========================================================================
    BTN_DOWNLOAD = "הורד"
    BTN_CANCEL = "ביטול"
    BTN_CLOSE = "סגור"
    BTN_SAVE = "שמור"
    BTN_LOAD = "טען"
    BTN_SELECT = "בחר"
    BTN_START = "התחל"
    BTN_STOP = "עצור"
    BTN_REFRESH = "רענן"
    BTN_SETTINGS = "הגדרות"
    BTN_OK = "אישור"
    BTN_YES = "כן"
    BTN_NO = "לא"
    
    # ==========================================================================
    # MODEL CATALOG
    # ==========================================================================
    MODEL_PARAMETERS = "פרמטרים"
    MODEL_QUANTIZATION = "קוונטיזציה"
    MODEL_SIZE = "גודל"
    MODEL_RAM_NEEDED = "RAM נדרש"
    MODEL_SPEED = "מהירות"
    MODEL_CONTEXT = "הקשר"
    MODEL_UNKNOWN = "לא ידוע"
    MODEL_SELECT_FILE = "בחר קובץ להורדה:"
    MODEL_SELECT_VARIANT = "בחר גרסת מודל"
    MODEL_LOADING_VARIANTS = "טוען גרסאות..."
    MODEL_NO_VARIANTS = "לא נמצאו גרסאות"
    
    # Speed ratings
    MODEL_SPEED_FAST = "⚡ מהיר מאוד"
    MODEL_SPEED_GOOD = "🚀 מהיר"
    MODEL_SPEED_MEDIUM = "⏱️ בינוני"
    MODEL_SPEED_SLOW = "🐢 איטי"
    MODEL_SPEED_VERY_SLOW = "🦥 איטי מאוד"
    
    # ==========================================================================
    # ENGINE / AI
    # ==========================================================================
    ENGINE_LOAD_MODEL = "טען מודל"
    ENGINE_ENTER_MODEL = "הזן שם מודל..."
    ENGINE_COT_SWARM = "נחיל CoT (רב-מומחים)"
    ENGINE_COT_DESCRIPTION = "ארביטראז' קונצנזוס מקבילי"
    ENGINE_QUIET_MODE = "מצב שקט (הסתר מומחים)"
    ENGINE_QUIET_DESCRIPTION = "הצג רק תשובה סופית מאומתת"
    ENGINE_SCANNING_SWARM = "סורק נחיל..."
    ENGINE_EXPERTS_ONLINE = "{count} מומחים מחוברים"
    ENGINE_STANDALONE = "מצב עצמאי"
    
    # ==========================================================================
    # SYSTEM
    # ==========================================================================
    SYS_CHECK_VERSION = "בדוק גרסת llama.cpp"
    SYS_RUN_BENCHMARK = "הרץ בנצ'מרק"
    SYS_DIAGNOSTICS = "אבחון"
    SYS_UPDATE_ENGINE = "עדכן מנוע"
    SYS_GET_UPDATE = "קבל עדכון (GitHub)"
    
    # ==========================================================================
    # SETTINGS
    # ==========================================================================
    SETTINGS_TITLE = "הגדרות"
    SETTINGS_SAVE = "שמור הגדרות"
    SETTINGS_RESET = "אפס לברירות מחדל"
    SETTINGS_SAVED = "ההגדרות נשמרו בהצלחה"
    SETTINGS_RESET_CONFIRM = "האם אתה בטוח שברצונך לאפס את כל ההגדרות?"
    SETTINGS_LANGUAGE_CHANGED = "השפה שונתה ל-{lang}. רענן את הדף ליישום."
    
    SETTINGS_CAT_LANGUAGE = "🌐 שפה"
    SETTINGS_CAT_APPEARANCE = "🎨 מראה"
    SETTINGS_CAT_AI_MODEL = "🤖 מודל AI"
    SETTINGS_CAT_VOICE = "🎤 קול"
    SETTINGS_CAT_RAG = "📚 RAG"
    SETTINGS_CAT_CHAT = "💬 צ'אט"
    SETTINGS_CAT_SYSTEM = "⚙️ מערכת"
    
    SETTINGS_UI_LANGUAGE = "שפת ממשק"
    SETTINGS_UI_LANGUAGE_DESC = "בחר את שפת ממשק המשתמש"
    SETTINGS_DARK_MODE = "מצב כהה"
    SETTINGS_DARK_MODE_DESC = "הפעל ערכת צבעים כהה"
    SETTINGS_FONT_SIZE = "גודל גופן"
    SETTINGS_FONT_SIZE_SMALL = "קטן"
    SETTINGS_FONT_SIZE_MEDIUM = "בינוני"
    SETTINGS_FONT_SIZE_LARGE = "גדול"
    SETTINGS_CHAT_DENSITY = "צפיפות צ'אט"
    SETTINGS_CHAT_DENSITY_COMPACT = "צפוף"
    SETTINGS_CHAT_DENSITY_COMFORTABLE = "נוח"
    SETTINGS_CHAT_DENSITY_SPACIOUS = "מרווח"
    SETTINGS_SHOW_AVATARS = "הצג אווטארים"
    SETTINGS_ANIMATE_MESSAGES = "הנפש הודעות"
    
    SETTINGS_DEFAULT_MODEL = "מודל ברירת מחדל"
    SETTINGS_DEFAULT_MODEL_DESC = "מודל לטעינה בהפעלה"
    SETTINGS_TEMPERATURE = "טמפרטורה"
    SETTINGS_TEMPERATURE_DESC = "גבוה = יותר יצירתי, נמוך = יותר ממוקד (0.0-2.0)"
    SETTINGS_MAX_TOKENS = "מקסימום טוקנים"
    SETTINGS_MAX_TOKENS_DESC = "אורך תגובה מקסימלי"
    SETTINGS_CONTEXT_WINDOW = "חלון הקשר"
    SETTINGS_CONTEXT_WINDOW_DESC = "כמה היסטוריית שיחה לזכור"
    
    SETTINGS_TTS_ENABLED = "טקסט לדיבור"
    SETTINGS_TTS_ENABLED_DESC = "הפעל פלט קולי"
    SETTINGS_VOICE_SPEED = "מהירות קול"
    SETTINGS_VOICE_SPEED_DESC = "קצב דיבור TTS (0.5x - 2.0x)"
    SETTINGS_AUTO_SPEAK = "הקרא תגובות אוטומטית"
    SETTINGS_AUTO_SPEAK_DESC = "קרא בקול תגובות AI באופן אוטומטי"
    SETTINGS_RECORDING_DURATION = "משך הקלטה"
    SETTINGS_RECORDING_DURATION_DESC = "זמן הקלטת קול (שניות)"
    
    SETTINGS_RAG_ENABLED = "הפעל RAG"
    SETTINGS_RAG_ENABLED_DESC = "השתמש בבסיס ידע לתשובות"
    SETTINGS_CHUNK_SIZE = "גודל מקטע"
    SETTINGS_CHUNK_SIZE_DESC = "גודל קטע טקסט לאינדוקס"
    SETTINGS_SIMILARITY_THRESHOLD = "סף דמיון"
    SETTINGS_SIMILARITY_THRESHOLD_DESC = "ציון רלוונטיות מינימלי (0.0-1.0)"
    SETTINGS_MAX_RESULTS = "מקסימום תוצאות"
    SETTINGS_MAX_RESULTS_DESC = "מספר מקורות לאחזר"
    
    SETTINGS_SHOW_TIMESTAMPS = "הצג חותמות זמן"
    SETTINGS_SHOW_TIMESTAMPS_DESC = "הצג זמן על כל הודעה"
    SETTINGS_AUTO_SCROLL = "גלילה אוטומטית"
    SETTINGS_AUTO_SCROLL_DESC = "גלול להודעות חדשות אוטומטית"
    SETTINGS_STREAM_RESPONSES = "הזרם תגובות"
    SETTINGS_STREAM_RESPONSES_DESC = "הצג תגובה בזמן יצירתה"
    SETTINGS_SAVE_CONVERSATIONS = "שמור שיחות"
    SETTINGS_SAVE_CONVERSATIONS_DESC = "זכור היסטוריה בין הפעלות"
    
    SETTINGS_API_PORT = "פורט API"
    SETTINGS_API_PORT_DESC = "פורט שרת backend LLM"
    SETTINGS_MODELS_DIRECTORY = "תיקיית מודלים"
    SETTINGS_MODELS_DIRECTORY_DESC = "תיקייה המכילה קבצי מודל GGUF"
    SETTINGS_CHECK_UPDATES = "בדוק עדכונים בהפעלה"
    SETTINGS_CHECK_UPDATES_DESC = "חפש גרסאות חדשות אוטומטית"
    SETTINGS_AUTO_START_BACKEND = "הפעל Backend אוטומטית"
    SETTINGS_AUTO_START_BACKEND_DESC = "הפעל שרת LLM עם האפליקציה"
    SETTINGS_LOG_LEVEL = "רמת לוג"
    SETTINGS_LOG_LEVEL_DESC = "רמת פירוט יומני האפליקציה"
    
    # ==========================================================================
    # RAG / SCAN & LEARN
    # ==========================================================================
    RAG_SCAN_LEARN = "סרוק ולמד (RAG)"
    RAG_ENABLE = "הפעל סרוק ולמד (RAG)"
    RAG_SCAN_READ = "סרוק וקרא"
    RAG_START_SCANNING = "התחל סריקה"
    RAG_SOURCE_TYPE = "סוג מקור"
    RAG_WEBSITE = "אתר אינטרנט"
    RAG_LOCAL_DIRECTORY = "תיקייה מקומית"
    RAG_WEBSITE_URL = "כתובת אתר"
    RAG_MAX_PAGES = "מקסימום עמודים"
    RAG_DIRECTORY_PATH = "נתיב תיקייה"
    RAG_MAX_FILES = "מקסימום קבצים"
    RAG_START_SCAN = "התחל סריקה"
    RAG_ANSWERED_FROM_SOURCE = "**🔍 תשובה ממקור הנתונים**"
    RAG_VIEW_SOURCES = "📂 הצג נתוני מקור"
    
    # ==========================================================================
    # CHAT INTERFACE
    # ==========================================================================
    CHAT_PLACEHOLDER = "כתוב הודעה..."
    CHAT_PLACEHOLDER_ZENA = "שאל אותי כל דבר..."
    CHAT_QUICK_ACTIONS = "פעולות מהירות"
    CHAT_CHECK_MODEL = "בדוק סטטוס מודל"
    CHAT_LATEST_LLAMA = "llama.cpp אחרון"
    CHAT_RUN_BENCHMARK = "הרץ בנצ'מרק"
    CHAT_HELP = "עזרה"
    CHAT_YOU = "אתה"
    CHAT_THINKING = "חושב..."
    CHAT_READY = "מוכן"
    CHAT_RECORDING = "🔴 מקליט (5 שניות)..."
    CHAT_TRANSCRIBING = "מתמלל..."
    
    # ==========================================================================
    # FILE UPLOAD
    # ==========================================================================
    UPLOAD_ATTACHED = "📎 {filename} ({size} תווים)"
    UPLOAD_SUCCESS = "{filename} צורף"
    UPLOAD_FAILED = "העלאה נכשלה: {error}"
    
    # ==========================================================================
    # VOICE
    # ==========================================================================
    VOICE_RECORDING = "🔴 מקליט ({seconds} שניות)..."
    VOICE_TRANSCRIBING = "מתמלל..."
    VOICE_TRANSCRIBED = "תומלל!"
    VOICE_NO_SPEECH = "לא זוהה דיבור"
    VOICE_ERROR = "שגיאת קול: {error}"
    VOICE_NOT_AVAILABLE = "TTS לא זמין (חסר pyttsx3)"
    
    # ==========================================================================
    # NOTIFICATIONS & MESSAGES
    # ==========================================================================
    # Model notifications
    NOTIFY_MODEL_LOADING = "🔄 טוען מודל: {model}..."
    NOTIFY_MODEL_READY = "✅ מודל מוכן: {model}"
    NOTIFY_MODEL_ACTIVE = "✅ מודל פעיל: {model}"
    NOTIFY_MODEL_SET = "✅ מודל פעיל הוגדר: {model}"
    
    # Download notifications
    NOTIFY_DOWNLOAD_STARTING = "🚀 מתחיל הורדה: {filename}..."
    NOTIFY_DOWNLOAD_STARTED = "✅ ההורדה החלה! בדוק התקדמות בטרמינל."
    NOTIFY_DOWNLOAD_FAILED = "❌ ההורדה נכשלה: {error}"
    NOTIFY_DOWNLOAD_ERROR = "❌ שגיאה: {error}"
    NOTIFY_HUB_CONNECTION_ERROR = "❌ לא ניתן להתחבר ל-Hub. האם הוא פועל על פורט 8002?"
    
    # Upload/attachment notifications
    NOTIFY_ATTACHED = "{name} צורף"
    NOTIFY_UPLOAD_FAILED = "העלאה נכשלה: {error}"
    
    # Voice notifications  
    NOTIFY_SOUNDDEVICE_MISSING = "שגיאה: SoundDevice לא נמצא (מצב Headless?)"
    NOTIFY_TRANSCRIBED = "תומלל!"
    NOTIFY_NO_SPEECH = "לא זוהה דיבור"
    NOTIFY_TRANSCRIPTION_FAILED = "התמלול נכשל: {error}"
    NOTIFY_VOICE_ERROR = "שגיאת קול: {error}"
    
    # RAG notifications
    NOTIFY_RAG_ENABLED = "מצב RAG הופעל"
    NOTIFY_RAG_DISABLED = "מצב RAG כובה"
    NOTIFY_RAG_SCANNING = "🔍 סורק {url}..."
    NOTIFY_RAG_SCRAPING = "📄 חילוץ ({count}/{total}) - זמן משוער: {eta}"
    NOTIFY_RAG_BUILDING = "✅ {count} עמודים חולצו. בונה אינדקס..."
    NOTIFY_RAG_SUCCESS = "✅ אינדקס RAG מוכן!"
    NOTIFY_RAG_NO_DOCS = "לא נמצאו מסמכים או RAG לא אותחל"
    NOTIFY_RAG_FAILED = "סריקת RAG נכשלה: {error}"
    NOTIFY_RAG_DIRECTORY_NOT_FOUND = "תיקייה לא נמצאה: {path}"
    NOTIFY_RAG_ENTER_URL = "אנא הזן כתובת אתר"
    NOTIFY_RAG_ENTER_PATH = "אנא הזן נתיב תיקייה"
    NOTIFY_RAG_FINDING_FILES = "📂 מחפש קבצים..."
    
    # Version notifications
    NOTIFY_VERSION_UP_TO_DATE = "✅ מעודכן! גרסה: {version}"
    NOTIFY_VERSION_CHECK_FAILED = "בדיקת גרסה נכשלה: {error}"
    NOTIFY_UPDATE_MANUAL = "העדכון דורש הורדה ידנית כרגע. פותח GitHub..."
    
    # Benchmark notifications
    NOTIFY_BENCHMARK_RUNNING = "🏃 מריץ בנצ'מרק... (ייקח כ-30 שניות)"
    NOTIFY_BENCHMARK_COMPLETE = "✅ הבנצ'מרק הושלם!"
    NOTIFY_BENCHMARK_FAILED = "❌ הבנצ'מרק נכשל: {error}"
    NOTIFY_BENCHMARK_RESULT = """✅ הבנצ'מרק הושלם!

📊 ביצועים: {tokens_per_sec:.1f} טוקנים/שנייה
📝 נוצרו: {tokens} טוקנים
⏱️ זמן: {seconds:.1f} שניות"""
    
    # Diagnostics
    NOTIFY_DIAGNOSTICS_RUNNING = "מריץ אבחון..."
    NOTIFY_DIAGNOSTICS_FAILED = "האבחון נכשל: {error}"
    DIAG_LLM_ONLINE = "✅ שרת LLM: מחובר"
    DIAG_LLM_ERROR = "❌ שרת LLM: שגיאה {code}"
    DIAG_LLM_OFFLINE = "❌ שרת LLM: לא מחובר ({error}...)"
    DIAG_RAG_VECTORS = "{emoji} RAG: {count} וקטורים"
    DIAG_RAG_NOT_INIT = "{emoji} RAG: לא אותחל"
    DIAG_MEMORY = "{emoji} זיכרון: {percent}% בשימוש"
    
    # Generic
    NOTIFY_ERROR = "❌ שגיאה: {error}"
    NOTIFY_SUCCESS = "✅ הצלחה!"
    NOTIFY_WARNING = "⚠️ אזהרה: {message}"
    NOTIFY_INFO = "ℹ️ {message}"
    NOTIFY_ENTER_BOTH_FIELDS = "אנא הזן גם מזהה מאגר וגם שם קובץ"
    
    # ==========================================================================
    # WELCOME MESSAGES
    # ==========================================================================
    WELCOME_ZENA = """👋 **ברוכים הבאים ל-ZenAI!**

{source_msg}. אני יכול לעזור לך עם:
- מענה על שאלות לגבי התוכן
- מציאת מידע במהירות
- מתן הדרכה

*שאל אותי אם תרצה!*"""

    WELCOME_SOURCE_WEBSITE = "סרקתי את האתר: **{url}**"
    WELCOME_SOURCE_FILESYSTEM = "סרקתי את התיקייה המקומית: **{path}**"
    WELCOME_SOURCE_KB = "יש לי גישה ל**בסיס הידע** המוגדר שלך"

    WELCOME_DEFAULT = """👋 **ברוכים הבאים ל-ZenAI!**

אני העוזר שלך לבינה מלאכותית מבית NiceGUI. אני יכול לעזור לך עם:
- ניהול מודלים של AI
- ניתוח קבצי קוד
- הרצת בנצ'מרקים
- תמלול קולי

*זכור, אני עדיין לומד ומשתפר!*"""

    # ==========================================================================
    # RAG SUCCESS MESSAGE
    # ==========================================================================
    RAG_SUCCESS_MSG = """✅ **אינדקס RAG מוכן!**

**סטטיסטיקות מסד נתונים:**
- 📄 **עמודים**: {count}
- 💾 **גודל**: {size_mb:.2f} MB
- 📂 **נתיב**: `{path}`
- 🌐 **מקור**: {source}"""

    RAG_SUCCESS_MSG_WITH_TYPES = """✅ **אינדקס RAG מוכן!**

**סטטיסטיקות מסד נתונים:**
- 📁 **קבצים**: {count}
- 💾 **גודל**: {size_mb:.2f} MB
- 📂 **נתיב**: `{path}`
- 🗂️ **מקור**: {source}
- 📄 **סוגים**: {ext_summary}"""

    # ==========================================================================
    # TOOLTIPS
    # ==========================================================================
    TOOLTIP_DARK_MODE = "החלף מצב כהה"
    TOOLTIP_ATTACH_FILE = "צרף קובץ"
    TOOLTIP_VOICE_INPUT = "קלט קולי"
    TOOLTIP_SEND_MESSAGE = "שלח הודעה"
    
    # ==========================================================================
    # ERRORS
    # ==========================================================================
    ERROR_WEBSITE_UNREACHABLE = "לא ניתן לגשת לאתר: {error}"
    ERROR_GENERIC = "אירעה שגיאה: {error}"
