# -*- coding: utf-8 -*-
"""
locales/es.py - Spanish Locale
Example translation for Spanish language.
"""

from .base import BaseLocale


class SpanishLocale(BaseLocale):
    """Spanish (Español) locale."""
    
    LANGUAGE_CODE = "es"
    LANGUAGE_NAME = "Spanish"
    LANGUAGE_NATIVE = "Español"
    
    # ==========================================================================
    # APP METADATA
    # ==========================================================================
    APP_TITLE = "ZenAI"
    APP_SUBTITLE = "Tu Asistente IA Local"
    
    # ==========================================================================
    # NAVIGATION
    # ==========================================================================
    NAV_MODELS = "📦 Modelos"
    NAV_ENGINE = "🤖 Motor IA"
    NAV_RAG = "📚 Escanear y Aprender"
    NAV_SYSTEM = "⚙️ Sistema"
    NAV_POPULAR_MODELS = "🔥 Modelos Populares"
    NAV_HF_DOWNLOAD = "📥 Descargar de Hugging Face"
    NAV_LOCAL_MODELS = "📂 Modelos Locales"
    NAV_NO_LOCAL_MODELS = "No hay modelos locales encontrados"
    
    # ==========================================================================
    # BUTTONS
    # ==========================================================================
    BTN_DOWNLOAD = "Descargar"
    BTN_CANCEL = "Cancelar"
    BTN_CLOSE = "Cerrar"
    BTN_SAVE = "Guardar"
    BTN_LOAD = "Cargar"
    BTN_SELECT = "Seleccionar"
    BTN_START = "Iniciar"
    BTN_STOP = "Detener"
    BTN_REFRESH = "Actualizar"
    BTN_SETTINGS = "Ajustes"
    BTN_OK = "Aceptar"
    BTN_YES = "Sí"
    BTN_NO = "No"
    
    # ==========================================================================
    # MODEL CATALOG
    # ==========================================================================
    MODEL_PARAMETERS = "Parámetros"
    MODEL_QUANTIZATION = "Cuantización"
    MODEL_SIZE = "Tamaño"
    MODEL_RAM_NEEDED = "RAM Necesaria"
    MODEL_SPEED = "Velocidad"
    MODEL_CONTEXT = "Contexto"
    MODEL_UNKNOWN = "Desconocido"
    MODEL_SELECT_FILE = "Seleccionar archivo a descargar:"
    MODEL_SELECT_VARIANT = "Seleccionar variante de modelo"
    MODEL_LOADING_VARIANTS = "Cargando variantes..."
    MODEL_NO_VARIANTS = "No se encontraron variantes"
    
    # Speed ratings
    MODEL_SPEED_FAST = "⚡ Muy Rápido"
    MODEL_SPEED_GOOD = "🚀 Rápido"
    MODEL_SPEED_MEDIUM = "⏱️ Medio"
    MODEL_SPEED_SLOW = "🐢 Lento"
    MODEL_SPEED_VERY_SLOW = "🦥 Muy Lento"
    
    # ==========================================================================
    # ENGINE / AI
    # ==========================================================================
    ENGINE_LOAD_MODEL = "Cargar Modelo"
    ENGINE_ENTER_MODEL = "Ingresa nombre de modelo..."
    ENGINE_COT_SWARM = "Enjambre CoT (Multi-Experto)"
    ENGINE_COT_DESCRIPTION = "Arbitraje de Consenso Paralelo"
    ENGINE_QUIET_MODE = "Modo Silencioso (Ocultar Expertos)"
    ENGINE_QUIET_DESCRIPTION = "Solo mostrar respuesta final verificada"
    ENGINE_SCANNING_SWARM = "Escaneando enjambre..."
    ENGINE_EXPERTS_ONLINE = "{count} Expertos En Línea"
    ENGINE_STANDALONE = "Modo Independiente"
    
    # ==========================================================================
    # SYSTEM
    # ==========================================================================
    SYS_CHECK_VERSION = "Verificar Versión de llama.cpp"
    SYS_RUN_BENCHMARK = "Ejecutar Benchmark"
    SYS_DIAGNOSTICS = "Diagnósticos"
    SYS_UPDATE_ENGINE = "Actualizar Motor"
    SYS_GET_UPDATE = "Obtener Actualización (GitHub)"
    
    # ==========================================================================
    # SETTINGS
    # ==========================================================================
    SETTINGS_TITLE = "Configuración"
    SETTINGS_SAVE = "Guardar Configuración"
    SETTINGS_RESET = "Restablecer Valores"
    SETTINGS_SAVED = "Configuración guardada exitosamente"
    SETTINGS_RESET_CONFIRM = "¿Estás seguro de que quieres restablecer toda la configuración?"
    SETTINGS_LANGUAGE_CHANGED = "Idioma cambiado a {lang}. Actualiza la página para aplicar."

    SETTINGS_CAT_LANGUAGE = "🌐 Idioma"
    SETTINGS_CAT_APPEARANCE = "🎨 Apariencia"
    SETTINGS_CAT_AI_MODEL = "🤖 Modelo IA"
    SETTINGS_CAT_VOICE = "🎤 Voz"
    SETTINGS_CAT_RAG = "📚 RAG"
    SETTINGS_CAT_CHAT = "💬 Chat"
    SETTINGS_CAT_SYSTEM = "⚙️ Sistema"
    
    SETTINGS_UI_LANGUAGE = "Idioma de la Interfaz"
    SETTINGS_UI_LANGUAGE_DESC = "Selecciona el idioma de la interfaz de usuario"
    SETTINGS_DARK_MODE = "Modo Oscuro"
    SETTINGS_DARK_MODE_DESC = "Activar tema de colores oscuros"
    SETTINGS_FONT_SIZE = "Tamaño de Fuente"
    SETTINGS_FONT_SIZE_SMALL = "Pequeño"
    SETTINGS_FONT_SIZE_MEDIUM = "Mediano"
    SETTINGS_FONT_SIZE_LARGE = "Grande"
    SETTINGS_CHAT_DENSITY = "Densidad del Chat"
    SETTINGS_CHAT_DENSITY_COMPACT = "Compacto"
    SETTINGS_CHAT_DENSITY_COMFORTABLE = "Cómodo"
    SETTINGS_CHAT_DENSITY_SPACIOUS = "Espacioso"
    SETTINGS_SHOW_AVATARS = "Mostrar Avatares"
    SETTINGS_ANIMATE_MESSAGES = "Animar Mensajes"
    
    SETTINGS_DEFAULT_MODEL = "Modelo Predeterminado"
    SETTINGS_DEFAULT_MODEL_DESC = "Modelo a cargar al iniciar"
    SETTINGS_TEMPERATURE = "Temperatura"
    SETTINGS_TEMPERATURE_DESC = "Mayor = más creativo, Menor = más enfocado (0.0-2.0)"
    SETTINGS_MAX_TOKENS = "Tokens Máximos"
    SETTINGS_MAX_TOKENS_DESC = "Longitud máxima de respuesta"
    SETTINGS_CONTEXT_WINDOW = "Ventana de Contexto"
    SETTINGS_CONTEXT_WINDOW_DESC = "Cuánto historial de conversación recordar"
    
    SETTINGS_TTS_ENABLED = "Texto a Voz"
    SETTINGS_TTS_ENABLED_DESC = "Habilitar salida de voz"
    SETTINGS_VOICE_SPEED = "Velocidad de Voz"
    SETTINGS_VOICE_SPEED_DESC = "Velocidad de habla TTS (0.5x - 2.0x)"
    SETTINGS_AUTO_SPEAK = "Hablar Respuestas Automáticamente"
    SETTINGS_AUTO_SPEAK_DESC = "Leer automáticamente las respuestas en voz alta"
    SETTINGS_RECORDING_DURATION = "Duración de Grabación"
    SETTINGS_RECORDING_DURATION_DESC = "Tiempo de grabación de voz (segundos)"
    
    SETTINGS_RAG_ENABLED = "Habilitar RAG"
    SETTINGS_RAG_ENABLED_DESC = "Usar base de conocimiento para respuestas"
    SETTINGS_CHUNK_SIZE = "Tamaño de Fragmento"
    SETTINGS_CHUNK_SIZE_DESC = "Tamaño de segmento de texto para indexación"
    SETTINGS_SIMILARITY_THRESHOLD = "Umbral de Similitud"
    SETTINGS_SIMILARITY_THRESHOLD_DESC = "Puntuación mínima de relevancia (0.0-1.0)"
    SETTINGS_MAX_RESULTS = "Resultados Máximos"
    SETTINGS_MAX_RESULTS_DESC = "Número de fuentes a recuperar"
    
    SETTINGS_SHOW_TIMESTAMPS = "Mostrar Marcas de Tiempo"
    SETTINGS_SHOW_TIMESTAMPS_DESC = "Mostrar hora en cada mensaje"
    SETTINGS_AUTO_SCROLL = "Desplazamiento Automático"
    SETTINGS_AUTO_SCROLL_DESC = "Desplazar a nuevos mensajes automáticamente"
    SETTINGS_STREAM_RESPONSES = "Transmitir Respuestas"
    SETTINGS_STREAM_RESPONSES_DESC = "Mostrar respuesta mientras se genera"
    SETTINGS_SAVE_CONVERSATIONS = "Guardar Conversaciones"
    SETTINGS_SAVE_CONVERSATIONS_DESC = "Recordar historial entre sesiones"
    
    SETTINGS_API_PORT = "Puerto API"
    SETTINGS_API_PORT_DESC = "Puerto del servidor backend LLM"
    SETTINGS_MODELS_DIRECTORY = "Directorio de Modelos"
    SETTINGS_MODELS_DIRECTORY_DESC = "Carpeta con archivos de modelo GGUF"
    SETTINGS_CHECK_UPDATES = "Buscar Actualizaciones al Iniciar"
    SETTINGS_CHECK_UPDATES_DESC = "Buscar nuevas versiones automáticamente"
    SETTINGS_AUTO_START_BACKEND = "Iniciar Backend Automáticamente"
    SETTINGS_AUTO_START_BACKEND_DESC = "Lanzar servidor LLM con la aplicación"
    SETTINGS_LOG_LEVEL = "Nivel de Registro"
    SETTINGS_LOG_LEVEL_DESC = "Verbosidad de los registros de aplicación"
    
    # ==========================================================================
    # RAG / SCAN & LEARN
    # ==========================================================================
    RAG_SCAN_LEARN = "Escanear y Aprender (RAG)"
    RAG_ENABLE = "Habilitar Escanear y Aprender (RAG)"
    RAG_SCAN_READ = "Escanear y Leer"
    RAG_START_SCANNING = "Iniciar Escaneo"
    RAG_SOURCE_TYPE = "Tipo de Fuente"
    RAG_WEBSITE = "Sitio Web"
    RAG_LOCAL_DIRECTORY = "Directorio Local"
    RAG_WEBSITE_URL = "URL del Sitio Web"
    RAG_MAX_PAGES = "Máx. Páginas"
    RAG_DIRECTORY_PATH = "Ruta del Directorio"
    RAG_MAX_FILES = "Máx. Archivos"
    RAG_START_SCAN = "Iniciar Escaneo"
    RAG_ANSWERED_FROM_SOURCE = "**🔍 Respuesta de Fuente de Datos**"
    RAG_VIEW_SOURCES = "📂 Ver Datos de Origen"
    
    # ==========================================================================
    # CHAT INTERFACE
    # ==========================================================================
    CHAT_PLACEHOLDER = "Escribe un mensaje..."
    CHAT_PLACEHOLDER_ZENA = "Pregúntame lo que quieras..."
    CHAT_QUICK_ACTIONS = "Acciones Rápidas"
    CHAT_CHECK_MODEL = "Verificar Estado del Modelo"
    CHAT_LATEST_LLAMA = "Último llama.cpp"
    CHAT_RUN_BENCHMARK = "Ejecutar Benchmark"
    CHAT_HELP = "Ayuda"
    CHAT_YOU = "Tú"
    CHAT_THINKING = "Pensando..."
    CHAT_READY = "Listo"
    CHAT_RECORDING = "🔴 Grabando (5s)..."
    CHAT_TRANSCRIBING = "Transcribiendo..."
    
    # ==========================================================================
    # FILE UPLOAD
    # ==========================================================================
    UPLOAD_ATTACHED = "📎 {filename} ({size} caracteres)"
    UPLOAD_SUCCESS = "{filename} adjuntado"
    UPLOAD_FAILED = "Error al subir: {error}"
    
    # ==========================================================================
    # VOICE
    # ==========================================================================
    VOICE_RECORDING = "🔴 Grabando ({seconds}s)..."
    VOICE_TRANSCRIBING = "Transcribiendo..."
    VOICE_TRANSCRIBED = "¡Transcrito!"
    VOICE_NO_SPEECH = "No se detectó voz"
    VOICE_ERROR = "Error de Voz: {error}"
    VOICE_NOT_AVAILABLE = "TTS no disponible (falta pyttsx3)"
    
    # ==========================================================================
    # NOTIFICATIONS & MESSAGES
    # ==========================================================================
    # Model notifications
    NOTIFY_MODEL_LOADING = "🔄 Cargando modelo: {model}..."
    NOTIFY_MODEL_READY = "✅ Modelo listo: {model}"
    NOTIFY_MODEL_ACTIVE = "✅ Modelo activo: {model}"
    NOTIFY_MODEL_SET = "✅ Modelo activo configurado: {model}"
    
    # Download notifications
    NOTIFY_DOWNLOAD_STARTING = "🚀 Iniciando descarga: {filename}..."
    NOTIFY_DOWNLOAD_STARTED = "✅ ¡Descarga iniciada! Revisa el progreso en tu terminal."
    NOTIFY_DOWNLOAD_FAILED = "❌ Descarga fallida: {error}"
    NOTIFY_DOWNLOAD_ERROR = "❌ Error: {error}"
    NOTIFY_HUB_CONNECTION_ERROR = "❌ No se puede conectar al Hub. ¿Está ejecutándose en el puerto 8002?"
    
    # Upload/attachment notifications
    NOTIFY_ATTACHED = "{name} adjuntado"
    NOTIFY_UPLOAD_FAILED = "Error al subir: {error}"
    
    # Voice notifications  
    NOTIFY_SOUNDDEVICE_MISSING = "Error: SoundDevice no encontrado (¿Sin audio?)"
    NOTIFY_TRANSCRIBED = "¡Transcrito!"
    NOTIFY_NO_SPEECH = "No se detectó voz"
    NOTIFY_TRANSCRIPTION_FAILED = "Transcripción Fallida: {error}"
    NOTIFY_VOICE_ERROR = "Error de Voz: {error}"
    
    # RAG notifications
    NOTIFY_RAG_ENABLED = "Modo RAG habilitado"
    NOTIFY_RAG_DISABLED = "Modo RAG deshabilitado"
    NOTIFY_RAG_SCANNING = "🔍 Escaneando {url}..."
    NOTIFY_RAG_SCRAPING = "📄 Extrayendo ({count}/{total}) - ETA: {eta}"
    NOTIFY_RAG_BUILDING = "✅ {count} páginas extraídas. Construyendo índice..."
    NOTIFY_RAG_SUCCESS = "✅ ¡Índice RAG listo!"
    NOTIFY_RAG_NO_DOCS = "No se encontraron documentos o RAG no inicializado"
    NOTIFY_RAG_FAILED = "Escaneo RAG fallido: {error}"
    NOTIFY_RAG_DIRECTORY_NOT_FOUND = "Directorio no encontrado: {path}"
    NOTIFY_RAG_ENTER_URL = "Por favor ingresa una URL de sitio web"
    NOTIFY_RAG_ENTER_PATH = "Por favor ingresa una ruta de directorio"
    NOTIFY_RAG_FINDING_FILES = "📂 Buscando archivos..."
    
    # Version notifications
    NOTIFY_VERSION_UP_TO_DATE = "✅ ¡Actualizado! Versión: {version}"
    NOTIFY_VERSION_CHECK_FAILED = "Verificación de versión fallida: {error}"
    NOTIFY_UPDATE_MANUAL = "La actualización requiere descarga manual actualmente. Abriendo GitHub..."
    
    # Benchmark notifications
    NOTIFY_BENCHMARK_RUNNING = "🏃 Ejecutando benchmark... (esto tomará ~30 segundos)"
    NOTIFY_BENCHMARK_COMPLETE = "✅ ¡Benchmark Completado!"
    NOTIFY_BENCHMARK_FAILED = "❌ Benchmark fallido: {error}"
    NOTIFY_BENCHMARK_RESULT = """✅ ¡Benchmark Completado!

📊 Rendimiento: {tokens_per_sec:.1f} tokens/seg
📝 Generados: {tokens} tokens
⏱️ Tiempo: {seconds:.1f} segundos"""
    
    # Diagnostics
    NOTIFY_DIAGNOSTICS_RUNNING = "Ejecutando diagnósticos..."
    NOTIFY_DIAGNOSTICS_FAILED = "Diagnósticos fallidos: {error}"
    DIAG_LLM_ONLINE = "✅ Backend LLM: En línea"
    DIAG_LLM_ERROR = "❌ Backend LLM: Error {code}"
    DIAG_LLM_OFFLINE = "❌ Backend LLM: Fuera de línea ({error}...)"
    DIAG_RAG_VECTORS = "{emoji} RAG: {count} vectores"
    DIAG_RAG_NOT_INIT = "{emoji} RAG: No inicializado"
    DIAG_MEMORY = "{emoji} Memoria: {percent}% usada"
    
    # Generic
    NOTIFY_ERROR = "❌ Error: {error}"
    NOTIFY_SUCCESS = "✅ ¡Éxito!"
    NOTIFY_WARNING = "⚠️ Advertencia: {message}"
    NOTIFY_INFO = "ℹ️ {message}"
    NOTIFY_ENTER_BOTH_FIELDS = "Por favor ingresa tanto el ID del Repositorio como el Nombre del Archivo"
    
    # ==========================================================================
    # WELCOME MESSAGES
    # ==========================================================================
    WELCOME_ZENA = """👋 **¡Bienvenido a ZenAI!**

{source_msg}. Puedo ayudarte con:
- Responder preguntas sobre el contenido
- Encontrar información rápidamente
- Proporcionar orientación

*¡Pregúntame si quieres!*"""

    WELCOME_SOURCE_WEBSITE = "Escaneé el sitio web: **{url}**"
    WELCOME_SOURCE_FILESYSTEM = "Escaneé el directorio local: **{path}**"
    WELCOME_SOURCE_KB = "Tengo acceso a tu **Base de Conocimiento** configurada"

    WELCOME_DEFAULT = """👋 **¡Bienvenido a ZenAI!**

Soy tu asistente IA potenciado por NiceGUI. Puedo ayudarte con:
- Gestionar modelos de IA
- Analizar archivos de código
- Ejecutar benchmarks
- Transcripción de voz

*¡Recuerda, sigo aprendiendo y mejorando!*"""

    # ==========================================================================
    # RAG SUCCESS MESSAGE
    # ==========================================================================
    RAG_SUCCESS_MSG = """✅ **¡Índice RAG Listo!**

**Estadísticas de la Base de Datos:**
- 📄 **Páginas**: {count}
- 💾 **Tamaño**: {size_mb:.2f} MB
- 📂 **Ruta**: `{path}`
- 🌐 **Fuente**: {source}"""

    RAG_SUCCESS_MSG_WITH_TYPES = """✅ **¡Índice RAG Listo!**

**Estadísticas de la Base de Datos:**
- 📁 **Archivos**: {count}
- 💾 **Tamaño**: {size_mb:.2f} MB
- 📂 **Ruta**: `{path}`
- 🗂️ **Fuente**: {source}
- 📄 **Tipos**: {ext_summary}"""

    # ==========================================================================
    # TOOLTIPS
    # ==========================================================================
    TOOLTIP_DARK_MODE = "Alternar Modo Oscuro"
    TOOLTIP_ATTACH_FILE = "Adjuntar archivo"
    TOOLTIP_VOICE_INPUT = "Entrada de voz"
    TOOLTIP_SEND_MESSAGE = "Enviar mensaje"
    
    # ==========================================================================
    # ERRORS
    # ==========================================================================
    ERROR_WEBSITE_UNREACHABLE = "No se puede acceder al sitio web: {error}"
    ERROR_GENERIC = "Ocurrió un error: {error}"
