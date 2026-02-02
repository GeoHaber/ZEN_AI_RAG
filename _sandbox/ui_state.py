import threading
import time
from typing import Any


class UIState:
    """A small thread-safe container for shared UI state.

    Methods operate under an internal lock so callers from threads
    or async tasks can safely mutate and read shared structures.
    """
    def __init__(self, initial: dict | None = None):
        self._lock = threading.RLock()
        self._state: dict[str, Any] = dict(initial or {})

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            val = self._state.get(key, default)
            # Return a shallow copy for lists to avoid callers mutating internal lists
            if isinstance(val, list):
                return list(val)
            return val

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._state[key] = value

    def update_model_options(self, models: list[str]) -> None:
        """Atomically update model options and trigger a UI update if widget present."""
        with self._lock:
            # store a copy
            self._state['model_select_options'] = list(models)
            sel = self._state.get('model_select')
            if sel is not None:
                try:
                    sel.options = list(models)
                    # some UI widgets provide an update() method; call if available
                    if hasattr(sel, 'update'):
                        sel.update()
                except Exception:
                    # UI update failure should not crash the caller
                    pass

    def clear_chat(self) -> None:
        """Clear chat container and history atomically."""
        with self._lock:
            cont = self._state.get('chat_container')
            if isinstance(cont, list):
                cont.clear()
            hist = self._state.get('chat_history')
            if isinstance(hist, list):
                hist.clear()

    def append_chat_message(self, msg: Any) -> None:
        """Append a message to both container and history in one atomic step."""
        with self._lock:
            cont = self._state.setdefault('chat_container', [])
            hist = self._state.setdefault('chat_history', [])
            cont.append(msg)
            hist.append(msg)

    def push_engagement(self, key: str, params: dict | None = None) -> None:
        """Push an engagement message key (localized) to the UI state."""
        with self._lock:
            msgs = self._state.setdefault('engagement_messages', [])
            msgs.append({'key': key, 'params': params or {}, 'ts': time.time()})

    def set_animation(self, name: str, value: bool) -> None:
        """Enable or disable a named animation (e.g., 'thinking')."""
        with self._lock:
            an = self._state.setdefault('animations', {})
            an[name] = bool(value)
