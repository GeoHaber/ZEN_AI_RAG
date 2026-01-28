# -*- coding: utf-8 -*-
"""
locales/fr.py - French Locale
Translation for French language.
"""

from .base import BaseLocale


class FrenchLocale(BaseLocale):
    """French (Français) locale."""
    
    LANGUAGE_CODE = "fr"
    LANGUAGE_NAME = "French"
    LANGUAGE_NATIVE = "Français"
    
    # ==========================================================================
    # APP METADATA
    # ==========================================================================
    APP_TITLE = "ZenAI"
    APP_SUBTITLE = "Votre Assistant IA Local"
    
    # ==========================================================================
    # NAVIGATION
    # ==========================================================================
    NAV_MODELS = "📦 Modèles"
    NAV_ENGINE = "🤖 Moteur IA"
    NAV_RAG = "📚 Scanner et Apprendre"
    NAV_SYSTEM = "⚙️ Système"
    NAV_POPULAR_MODELS = "🔥 Modèles Populaires"
    NAV_HF_DOWNLOAD = "📥 Télécharger depuis Hugging Face"
    NAV_LOCAL_MODELS = "📂 Modèles Locaux"
    NAV_NO_LOCAL_MODELS = "Aucun modèle local trouvé"
    
    # ==========================================================================
    # BUTTONS
    # ==========================================================================
    BTN_DOWNLOAD = "Télécharger"
    BTN_CANCEL = "Annuler"
    BTN_CLOSE = "Fermer"
    BTN_SAVE = "Enregistrer"
    BTN_LOAD = "Charger"
    BTN_SELECT = "Sélectionner"
    BTN_START = "Démarrer"
    BTN_STOP = "Arrêter"
    BTN_REFRESH = "Actualiser"
    BTN_SETTINGS = "Paramètres"
    BTN_OK = "OK"
    BTN_YES = "Oui"
    BTN_NO = "Non"
    
    # ==========================================================================
    # MODEL CATALOG
    # ==========================================================================
    MODEL_PARAMETERS = "Paramètres"
    MODEL_QUANTIZATION = "Quantification"
    MODEL_SIZE = "Taille"
    MODEL_RAM_NEEDED = "RAM Requise"
    MODEL_SPEED = "Vitesse"
    MODEL_CONTEXT = "Contexte"
    MODEL_UNKNOWN = "Inconnu"
    MODEL_SELECT_FILE = "Sélectionner le fichier à télécharger :"
    MODEL_SELECT_VARIANT = "Sélectionner la variante du modèle"
    MODEL_LOADING_VARIANTS = "Chargement des variantes..."
    MODEL_NO_VARIANTS = "Aucune variante trouvée"
    
    # Speed ratings
    MODEL_SPEED_FAST = "⚡ Très Rapide"
    MODEL_SPEED_GOOD = "🚀 Rapide"
    MODEL_SPEED_MEDIUM = "⏱️ Moyen"
    MODEL_SPEED_SLOW = "🐢 Lent"
    MODEL_SPEED_VERY_SLOW = "🦥 Très Lent"
    
    # ==========================================================================
    # ENGINE / AI
    # ==========================================================================
    ENGINE_LOAD_MODEL = "Charger le Modèle"
    ENGINE_ENTER_MODEL = "Entrez le nom du modèle..."
    ENGINE_COT_SWARM = "Essaim CoT (Multi-Expert)"
    ENGINE_COT_DESCRIPTION = "Arbitrage par Consensus Parallèle"
    ENGINE_QUIET_MODE = "Mode Silencieux (Masquer les Experts)"
    ENGINE_QUIET_DESCRIPTION = "Afficher uniquement la réponse finale vérifiée"
    ENGINE_SCANNING_SWARM = "Analyse de l'essaim..."
    ENGINE_EXPERTS_ONLINE = "{count} Experts En Ligne"
    ENGINE_STANDALONE = "Mode Autonome ZenAI"
    
    # ==========================================================================
    # SYSTEM
    # ==========================================================================
    SYS_CHECK_VERSION = "Vérifier la Version de llama.cpp"
    SYS_RUN_BENCHMARK = "Exécuter le Benchmark"
    SYS_DIAGNOSTICS = "Diagnostics"
    SYS_UPDATE_ENGINE = "Mettre à Jour le Moteur"
    SYS_GET_UPDATE = "Obtenir la Mise à Jour (GitHub)"
    
    # ==========================================================================
    # SETTINGS
    # ==========================================================================
    SETTINGS_TITLE = "Paramètres"
    SETTINGS_SAVE = "Enregistrer les Paramètres"
    SETTINGS_RESET = "Réinitialiser"
    SETTINGS_SAVED = "Paramètres enregistrés avec succès"
    SETTINGS_RESET_CONFIRM = "Êtes-vous sûr de vouloir réinitialiser tous les paramètres ?"
    SETTINGS_LANGUAGE_CHANGED = "Langue changée en {lang}. Actualisez la page pour appliquer."
    
    SETTINGS_CAT_LANGUAGE = "🌐 Langue"
    SETTINGS_CAT_APPEARANCE = "🎨 Apparence"
    SETTINGS_CAT_AI_MODEL = "🤖 Modèle IA"
    SETTINGS_CAT_VOICE = "🎙️ Voix"
    SETTINGS_CAT_RAG = "📚 RAG"
    SETTINGS_CAT_CHAT = "💬 Chat"
    SETTINGS_CAT_SYSTEM = "⚙️ Système"
    
    SETTINGS_UI_LANGUAGE = "Langue de l'Interface"
    SETTINGS_UI_LANGUAGE_DESC = "Sélectionnez la langue de l'interface utilisateur"
    SETTINGS_DARK_MODE = "Mode Sombre"
    SETTINGS_DARK_MODE_DESC = "Activer le thème de couleurs sombres"
    SETTINGS_FONT_SIZE = "Taille de Police"
    SETTINGS_FONT_SIZE_SMALL = "Petit"
    SETTINGS_FONT_SIZE_MEDIUM = "Moyen"
    SETTINGS_FONT_SIZE_LARGE = "Grand"
    SETTINGS_CHAT_DENSITY = "Densité du Chat"
    SETTINGS_CHAT_DENSITY_COMPACT = "Compact"
    SETTINGS_CHAT_DENSITY_COMFORTABLE = "Confortable"
    SETTINGS_CHAT_DENSITY_SPACIOUS = "Spacieux"
    SETTINGS_SHOW_AVATARS = "Afficher les Avatars"
    SETTINGS_ANIMATE_MESSAGES = "Animer les Messages"
    
    SETTINGS_DEFAULT_MODEL = "Modèle par Défaut"
    SETTINGS_DEFAULT_MODEL_DESC = "Modèle à charger au démarrage"
    SETTINGS_TEMPERATURE = "Température"
    SETTINGS_TEMPERATURE_DESC = "Plus élevé = plus créatif, Plus bas = plus ciblé (0.0-2.0)"
    SETTINGS_MAX_TOKENS = "Tokens Maximum"
    SETTINGS_MAX_TOKENS_DESC = "Longueur maximale de la réponse"
    SETTINGS_CONTEXT_WINDOW = "Fenêtre de Contexte"
    SETTINGS_CONTEXT_WINDOW_DESC = "Combien d'historique de conversation retenir"
    
    SETTINGS_TTS_ENABLED = "Synthèse Vocale"
    SETTINGS_TTS_ENABLED_DESC = "Activer la sortie vocale"
    SETTINGS_VOICE_SPEED = "Vitesse de la Voix"
    SETTINGS_VOICE_SPEED_DESC = "Vitesse de parole TTS (0.5x - 2.0x)"
    SETTINGS_AUTO_SPEAK = "Parler Automatiquement"
    SETTINGS_AUTO_SPEAK_DESC = "Lire automatiquement les réponses à haute voix"
    SETTINGS_RECORDING_DURATION = "Durée d'Enregistrement"
    SETTINGS_RECORDING_DURATION_DESC = "Temps d'enregistrement vocal (secondes)"
    
    SETTINGS_RAG_ENABLED = "Activer RAG"
    SETTINGS_RAG_ENABLED_DESC = "Utiliser la base de connaissances pour les réponses"
    SETTINGS_CHUNK_SIZE = "Taille des Segments"
    SETTINGS_CHUNK_SIZE_DESC = "Taille des segments de texte pour l'indexation"
    SETTINGS_SIMILARITY_THRESHOLD = "Seuil de Similarité"
    SETTINGS_SIMILARITY_THRESHOLD_DESC = "Score de pertinence minimum (0.0-1.0)"
    SETTINGS_MAX_RESULTS = "Résultats Maximum"
    SETTINGS_MAX_RESULTS_DESC = "Nombre de sources à récupérer"
    
    SETTINGS_SHOW_TIMESTAMPS = "Afficher les Horodatages"
    SETTINGS_SHOW_TIMESTAMPS_DESC = "Afficher l'heure sur chaque message"
    SETTINGS_AUTO_SCROLL = "Défilement Automatique"
    SETTINGS_AUTO_SCROLL_DESC = "Défiler vers les nouveaux messages automatiquement"
    SETTINGS_STREAM_RESPONSES = "Diffuser les Réponses"
    SETTINGS_STREAM_RESPONSES_DESC = "Afficher la réponse pendant sa génération"
    SETTINGS_SAVE_CONVERSATIONS = "Sauvegarder les Conversations"
    SETTINGS_SAVE_CONVERSATIONS_DESC = "Retenir l'historique entre les sessions"
    
    SETTINGS_API_PORT = "Port API"
    SETTINGS_API_PORT_DESC = "Port du serveur backend LLM"
    SETTINGS_MODELS_DIRECTORY = "Répertoire des Modèles"
    SETTINGS_MODELS_DIRECTORY_DESC = "Dossier contenant les fichiers de modèle GGUF"
    SETTINGS_CHECK_UPDATES = "Vérifier les Mises à Jour au Démarrage"
    SETTINGS_CHECK_UPDATES_DESC = "Rechercher de nouvelles versions automatiquement"
    SETTINGS_AUTO_START_BACKEND = "Démarrer le Backend Automatiquement"
    SETTINGS_AUTO_START_BACKEND_DESC = "Lancer le serveur LLM avec l'application"
    SETTINGS_LOG_LEVEL = "Niveau de Journalisation"
    SETTINGS_LOG_LEVEL_DESC = "Verbosité des journaux de l'application"
    
    # ==========================================================================
    # RAG / SCAN & LEARN
    # ==========================================================================
    RAG_SCAN_LEARN = "Scanner et Apprendre (RAG)"
    RAG_ENABLE = "Activer Scanner et Apprendre (RAG)"
    RAG_SCAN_READ = "Scanner et Lire"
    RAG_START_SCANNING = "Démarrer l'Analyse"
    RAG_SOURCE_TYPE = "Type de Source"
    RAG_WEBSITE = "Site Web"
    RAG_LOCAL_DIRECTORY = "Répertoire Local"
    RAG_WEBSITE_URL = "URL du Site Web"
    RAG_MAX_PAGES = "Pages Max"
    RAG_DIRECTORY_PATH = "Chemin du Répertoire"
    RAG_MAX_FILES = "Fichiers Max"
    RAG_START_SCAN = "Démarrer l'Analyse"
    RAG_ANSWERED_FROM_SOURCE = "**🔍 Réponse à partir de la Source de Données**"
    RAG_VIEW_SOURCES = "📂 Voir les Données Sources"
    
    # ==========================================================================
    # CHAT INTERFACE
    # ==========================================================================
    CHAT_PLACEHOLDER = "Écrivez un message..."
    CHAT_PLACEHOLDER_ZENAI = "Posez-moi une question..."
    CHAT_QUICK_ACTIONS = "Actions Rapides"
    CHAT_CHECK_MODEL = "Vérifier l'État du Modèle"
    CHAT_LATEST_LLAMA = "Dernier llama.cpp"
    CHAT_RUN_BENCHMARK = "Exécuter le Benchmark"
    CHAT_HELP = "Aide"
    CHAT_YOU = "Vous"
    CHAT_THINKING = "Réflexion..."
    CHAT_READY = "Prêt"
    CHAT_RECORDING = "🔴 Enregistrement (5s)..."
    CHAT_TRANSCRIBING = "Transcription..."
    
    # ==========================================================================
    # FILE UPLOAD
    # ==========================================================================
    UPLOAD_ATTACHED = "📎 {filename} ({size} caractères)"
    UPLOAD_SUCCESS = "{filename} joint"
    UPLOAD_FAILED = "Échec du téléchargement : {error}"
    
    # ==========================================================================
    # VOICE
    # ==========================================================================
    VOICE_RECORDING = "🔴 Enregistrement ({seconds}s)..."
    VOICE_TRANSCRIBING = "Transcription..."
    VOICE_TRANSCRIBED = "Transcrit !"
    VOICE_NO_SPEECH = "Aucune parole détectée"
    VOICE_ERROR = "Erreur Vocale : {error}"
    VOICE_NOT_AVAILABLE = "TTS non disponible (pyttsx3 manquant)"
    
    # ==========================================================================
    # NOTIFICATIONS & MESSAGES
    # ==========================================================================
    # Model notifications
    NOTIFY_MODEL_LOADING = "🔄 Chargement du modèle : {model}..."
    NOTIFY_MODEL_READY = "✅ Modèle prêt : {model}"
    NOTIFY_MODEL_ACTIVE = "✅ Modèle actif : {model}"
    NOTIFY_MODEL_SET = "✅ Modèle actif défini : {model}"
    
    # Download notifications
    NOTIFY_DOWNLOAD_STARTING = "🚀 Démarrage du téléchargement : {filename}..."
    NOTIFY_DOWNLOAD_STARTED = "✅ Téléchargement démarré ! Vérifiez la progression dans votre terminal."
    NOTIFY_DOWNLOAD_FAILED = "❌ Échec du téléchargement : {error}"
    NOTIFY_DOWNLOAD_ERROR = "❌ Erreur : {error}"
    NOTIFY_HUB_CONNECTION_ERROR = "❌ Impossible de se connecter au Hub. Est-il en cours d'exécution sur le port 8002 ?"
    
    # Upload/attachment notifications
    NOTIFY_ATTACHED = "{name} joint"
    NOTIFY_UPLOAD_FAILED = "Échec du téléchargement : {error}"
    
    # Voice notifications  
    NOTIFY_SOUNDDEVICE_MISSING = "Erreur : SoundDevice introuvable (Mode sans tête ?)"
    NOTIFY_TRANSCRIBED = "Transcrit !"
    NOTIFY_NO_SPEECH = "Aucune parole détectée"
    NOTIFY_TRANSCRIPTION_FAILED = "Échec de la Transcription : {error}"
    NOTIFY_VOICE_ERROR = "Erreur Vocale : {error}"
    
    # RAG notifications
    NOTIFY_RAG_ENABLED = "Mode RAG activé"
    NOTIFY_RAG_DISABLED = "Mode RAG désactivé"
    NOTIFY_RAG_SCANNING = "🔍 Analyse de {url}..."
    NOTIFY_RAG_SCRAPING = "📄 Extraction ({count}/{total}) - ETA : {eta}"
    NOTIFY_RAG_BUILDING = "✅ {count} pages extraites. Construction de l'index..."
    NOTIFY_RAG_SUCCESS = "✅ Index RAG prêt !"
    NOTIFY_RAG_NO_DOCS = "Aucun document trouvé ou RAG non initialisé"
    NOTIFY_RAG_FAILED = "Échec de l'analyse RAG : {error}"
    NOTIFY_RAG_DIRECTORY_NOT_FOUND = "Répertoire introuvable : {path}"
    NOTIFY_RAG_ENTER_URL = "Veuillez entrer une URL de site web"
    NOTIFY_RAG_ENTER_PATH = "Veuillez entrer un chemin de répertoire"
    NOTIFY_RAG_FINDING_FILES = "📂 Recherche de fichiers..."
    
    # Version notifications
    NOTIFY_VERSION_UP_TO_DATE = "✅ À jour ! Version : {version}"
    NOTIFY_VERSION_CHECK_FAILED = "Échec de la vérification de version : {error}"
    NOTIFY_UPDATE_MANUAL = "La mise à jour nécessite actuellement un téléchargement manuel. Ouverture de GitHub..."
    
    # Benchmark notifications
    NOTIFY_BENCHMARK_RUNNING = "🏃 Exécution du benchmark... (environ 30 secondes)"
    NOTIFY_BENCHMARK_COMPLETE = "✅ Benchmark Terminé !"
    NOTIFY_BENCHMARK_FAILED = "❌ Échec du benchmark : {error}"
    NOTIFY_BENCHMARK_RESULT = """✅ Benchmark Terminé !

📊 Performance : {tokens_per_sec:.1f} tokens/sec
📝 Générés : {tokens} tokens
⏱️ Temps : {seconds:.1f} secondes"""
    
    # Diagnostics
    NOTIFY_DIAGNOSTICS_RUNNING = "Exécution des diagnostics..."
    NOTIFY_DIAGNOSTICS_FAILED = "Échec des diagnostics : {error}"
    DIAG_LLM_ONLINE = "✅ Backend LLM : En ligne"
    DIAG_LLM_ERROR = "❌ Backend LLM : Erreur {code}"
    DIAG_LLM_OFFLINE = "❌ Backend LLM : Hors ligne ({error}...)"
    DIAG_RAG_VECTORS = "{emoji} RAG : {count} vecteurs"
    DIAG_RAG_NOT_INIT = "{emoji} RAG : Non initialisé"
    DIAG_MEMORY = "{emoji} Mémoire : {percent}% utilisée"
    
    # Generic
    NOTIFY_ERROR = "❌ Erreur : {error}"
    NOTIFY_SUCCESS = "✅ Succès !"
    NOTIFY_WARNING = "⚠️ Avertissement : {message}"
    NOTIFY_INFO = "ℹ️ {message}"
    NOTIFY_ENTER_BOTH_FIELDS = "Veuillez entrer l'ID du Dépôt et le Nom du Fichier"
    
    # ==========================================================================
    # WELCOME MESSAGES
    # ==========================================================================
    WELCOME_ZENAI = """👋 **Bienvenue sur ZenAI !**

{source_msg}. Je peux vous aider à :
- Répondre aux questions sur le contenu
- Trouver des informations rapidement
- Fournir des conseils

*N'hésitez pas à me poser des questions !*"""

    WELCOME_SOURCE_WEBSITE = "J'ai analysé le site web : **{url}**"
    WELCOME_SOURCE_FILESYSTEM = "J'ai analysé le répertoire local : **{path}**"
    WELCOME_SOURCE_KB = "J'ai accès à votre **Base de Connaissances** configurée"

    WELCOME_DEFAULT = """👋 **Bienvenue sur ZenAI !**

Je suis votre assistant IA propulsé par NiceGUI. Je peux vous aider à :
- Gérer les modèles d'IA
- Analyser les fichiers de code
- Exécuter des benchmarks
- Transcription vocale

*N'oubliez pas, je continue à apprendre et à m'améliorer !*"""

    # ==========================================================================
    # RAG SUCCESS MESSAGE
    # ==========================================================================
    RAG_SUCCESS_MSG = """✅ **Index RAG Prêt !**

**Statistiques de la Base de Données :**
- 📄 **Pages** : {count}
- 💾 **Taille** : {size_mb:.2f} Mo
- 📂 **Chemin** : `{path}`
- 🌐 **Source** : {source}"""

    RAG_SUCCESS_MSG_WITH_TYPES = """✅ **Index RAG Prêt !**

**Statistiques de la Base de Données :**
- 📁 **Fichiers** : {count}
- 💾 **Taille** : {size_mb:.2f} Mo
- 📂 **Chemin** : `{path}`
- 🗂️ **Source** : {source}
- 📄 **Types** : {ext_summary}"""

    # ==========================================================================
    # TOOLTIPS
    # ==========================================================================
    TOOLTIP_DARK_MODE = "Basculer le Mode Sombre"
    TOOLTIP_ATTACH_FILE = "Joindre un fichier"
    TOOLTIP_VOICE_INPUT = "Entrée vocale"
    TOOLTIP_SEND_MESSAGE = "Envoyer le message"
    
    # ==========================================================================
    # ERRORS
    # ==========================================================================
    ERROR_WEBSITE_UNREACHABLE = "Impossible d'accéder au site web : {error}"
    ERROR_GENERIC = "Une erreur s'est produite : {error}"
