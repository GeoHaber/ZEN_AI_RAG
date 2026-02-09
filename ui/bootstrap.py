
import sys
import logging
import time
import traceback
import io
from pathlib import Path
from config_system import config

# Logging - output to BOTH file and console
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler('nebula_debug.log', mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)  # Also print to console
        ]
    )
    return logging.getLogger("ZenAI")

# --- Global Crash Handler ---
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    try:
        with open("ui_fatal_crash.txt", "w", encoding='utf-8') as f:
            f.write(f"Timestamp: {time.ctime()}\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    except (OSError, IOError):
        pass  # Can't write crash log, silently continue

def setup_crash_handler():
    sys.excepthook = handle_exception

def initialize_services():
    """Initialize all backend services (RAG, Memory, Features, Cleanup)."""
    logger = logging.getLogger("ZenAI.Bootstrap")
    
    # 1. Config Mode
    ZENA_MODE = config.zena_mode_enabled
    ZENA_CONFIG = {
        'enabled': config.zena_mode_enabled,
        'rag_enabled': True,
        'rag_source': 'knowledge_base',
        'swarm_enabled': config.swarm_enabled
    }
    logger.info(f"[Core] v3.1 Spec Initialization | Mode: {'Native' if ZENA_MODE else 'Legacy'} | Swarm: {config.swarm_enabled}")

    # 2. RAG System
    rag_system = None
    universal_extractor = None
    if ZENA_MODE:
        try:
            from zena_mode import LocalRAG
            from zena_mode.universal_extractor import UniversalExtractor
            
            # Universal Extractor for PDF/Image OCR in chat
            universal_extractor = UniversalExtractor()
            logger.info("[RAG] Universal Extractor ready for OCR")

            rag_cache = config.BASE_DIR / "rag_cache"
            rag_cache.mkdir(exist_ok=True)

            # RAG system initialization
            rag_system = LocalRAG(cache_dir=rag_cache)
            # Default RAG to enabled in config if not present
            if 'rag_enabled' not in ZENA_CONFIG:
                ZENA_CONFIG['rag_enabled'] = True
            logger.info("[RAG] RAG system initialized")
        except Exception as e:
            logger.error(f"[RAG] Failed to initialize: {e}")

    # 3. Conversation Memory
    conversation_memory = None
    try:
        from zena_mode import ConversationMemory
        conv_cache = config.BASE_DIR / "conversation_cache"
        conv_cache.mkdir(exist_ok=True)
        
        conversation_memory = ConversationMemory(cache_dir=conv_cache)
        logger.info("[Memory] Conversation memory initialized")
    except Exception as e:
        logger.error(f"[Memory] Failed to initialize conversation memory: {e}")

    # 4. Feature Detection
    from feature_detection import get_feature_detector
    feature_detector = get_feature_detector()
    logger.info("[Features] Feature detection complete")

    # 5. Cleanup Policy
    from cleanup_policy import get_cleanup_policy
    upload_cleanup = get_cleanup_policy(config.BASE_DIR / "uploads")
    logger.info("[Cleanup] Upload cleanup policy initialized")
    
    # 6. Help System
    try:
        if rag_system:
            from zena_mode.help_system import index_internal_docs
            from zena_mode.help_system import index_internal_docs
            # index_internal_docs(config.BASE_DIR, rag_system) # Blocking startup, disabled for debugging
            logger.info("[HelpSystem] Internal documentation indexing skipped (DEBUG)")
    except Exception as e:
        logger.warning(f"[HelpSystem] Failed to index internal docs: {e}")

    return {
        "rag_system": rag_system,
        "universal_extractor": universal_extractor,
        "conversation_memory": conversation_memory,
        "feature_detector": feature_detector,
        "upload_cleanup": upload_cleanup,
        "ZENA_CONFIG": ZENA_CONFIG,
        "ZENA_MODE": ZENA_MODE
    }
