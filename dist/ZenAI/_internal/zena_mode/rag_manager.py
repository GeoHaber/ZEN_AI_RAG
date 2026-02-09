import threading
from typing import List, Any
from typing import Optional


class RAGManager:
    """Thread-safe manager for RAG-related state (documents, file paths, model).

    This is intentionally minimal: it provides atomic update and snapshot accessors
    so callers (UI and workers) can rely on consistent views of the state.
    """
    def __init__(self):
        self._lock = threading.RLock()
        self._model = None
        self._documents: List[Any] = []
        self._file_paths: List[str] = []

    @property
    def model(self):
        with self._lock:
            return self._model

    def set_model(self, model_obj) -> None:
        with self._lock:
            self._model = model_obj

    # Allow setting the underlying RAG system implementation so callers can
    # continue to use its methods via this manager (proxying).
    def set_system(self, system_obj) -> None:
        with self._lock:
            self._model = system_obj

    def warmup(self):
        with self._lock:
            if self._model and hasattr(self._model, 'warmup'):
                return self._model.warmup()
            return None

    def build_index(self, documents):
        with self._lock:
            if self._model and hasattr(self._model, 'build_index'):
                return self._model.build_index(documents)
            raise RuntimeError('No underlying RAG system set')

    def save(self, path):
        with self._lock:
            if self._model and hasattr(self._model, 'save'):
                return self._model.save(path)
            raise RuntimeError('No underlying RAG system set')

    def hybrid_search(self, *args, **kwargs):
        with self._lock:
            if self._model and hasattr(self._model, 'hybrid_search'):
                return self._model.hybrid_search(*args, **kwargs)
            raise RuntimeError('No underlying RAG system set')

    def query(self, *args, **kwargs):
        with self._lock:
            if self._model and hasattr(self._model, 'query'):
                return self._model.query(*args, **kwargs)
            raise RuntimeError('No underlying RAG system set')

    @property
    def index(self):
        with self._lock:
            if self._model and hasattr(self._model, 'index'):
                return getattr(self._model, 'index')
            return None

    @property
    def documents(self) -> List[Any]:
        with self._lock:
            return list(self._documents)

    @property
    def file_paths(self) -> List[str]:
        with self._lock:
            return list(self._file_paths)

    def update_documents(self, docs: List[Any], paths: List[str]) -> None:
        """Atomically replace document list and file paths.

        This avoids races where a reader sees a partially-updated list.
        """
        with self._lock:
            self._documents = list(docs)
            self._file_paths = list(paths)

    def clear_documents(self) -> None:
        with self._lock:
            self._documents.clear()
            self._file_paths.clear()
