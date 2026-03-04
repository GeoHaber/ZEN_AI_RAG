import threading
from typing import List, Any, Optional


class _RAGManagerBase:
    """Base methods for RAGManager."""

    def __init__(self):
        """Initialize instance."""
        self._lock = threading.Lock()
        self._model = None
        self._documents: List[Any] = []
        self._file_paths: List[str] = []

    @property
    def model(self):
        """Get the current RAG model/system (thread-safe)."""
        with self._lock:
            return self._model

    def set_model(self, model_obj) -> None:
        """Set the RAG model object."""
        with self._lock:
            self._model = model_obj

    def set_system(self, system_obj) -> None:
        """Set the underlying RAG system implementation for proxying."""
        with self._lock:
            self._model = system_obj

    def warmup(self) -> Optional[Any]:
        """Warm up the underlying RAG model."""
        with self._lock:
            if self._model and hasattr(self._model, 'warmup'):
                return self._model.warmup()
            return None

    def build_index(self, documents):
        """Build the RAG index from documents."""
        with self._lock:
            if self._model and hasattr(self._model, 'build_index'):
                return self._model.build_index(documents)
            raise RuntimeError('No underlying RAG system set')

    def save(self, path):
        """Save RAG state to disk."""
        with self._lock:
            if self._model and hasattr(self._model, 'save'):
                return self._model.save(path)
            raise RuntimeError('No underlying RAG system set')


class RAGManager(_RAGManagerBase):
    """Thread-safe manager for RAG-related state (documents, file paths, model).

    This is intentionally minimal: it provides atomic update and snapshot accessors
    so callers (UI and workers) can rely on consistent views of the state.

    All methods are synchronous — the underlying LocalRAG is synchronous.
    Uses threading.Lock for thread safety (NOT asyncio.Lock which requires async context).
    """

    def hybrid_search(self, *args, **kwargs):
        """Perform hybrid search via the underlying RAG system."""
        with self._lock:
            if self._model and hasattr(self._model, 'hybrid_search'):
                return self._model.hybrid_search(*args, **kwargs)
            raise RuntimeError('No underlying RAG system set')

    def query(self, *args, **kwargs):
        """Query the RAG system."""
        with self._lock:
            if self._model and hasattr(self._model, 'query'):
                return self._model.query(*args, **kwargs)
            raise RuntimeError('No underlying RAG system set')

    @property
    def index(self):
        """Get the current index object (thread-safe)."""
        with self._lock:
            if self._model and hasattr(self._model, 'index'):
                return getattr(self._model, 'index')
            return None

    @property
    def documents(self) -> List[Any]:
        """Get a snapshot copy of the document list (thread-safe)."""
        with self._lock:
            return list(self._documents)

    @property
    def file_paths(self) -> List[str]:
        """Get a snapshot copy of file paths (thread-safe)."""
        with self._lock:
            return list(self._file_paths)

    def update_documents(self, docs: List[Any], paths: List[str]) -> None:
        """Atomically replace document list and file paths.

        Avoids races where a reader sees a partially-updated list.
        """
        with self._lock:
            self._documents = list(docs)
            self._file_paths = list(paths)

    def clear_documents(self) -> None:
        """Clear all documents and file paths."""
        with self._lock:
            self._documents.clear()
            self._file_paths.clear()

    def get_stats(self) -> dict:
        """Get stats from the underlying RAG system."""
        with self._lock:
            if self._model and hasattr(self._model, 'get_stats'):
                return self._model.get_stats()
            return {"status": "no_model"}
