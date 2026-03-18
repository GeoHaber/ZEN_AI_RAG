"""
Session Service — Conversation Management.

Responsibility: Manage conversation history and context.
  - Create sessions
  - Add messages
  - Track conversation state
  - Persist history to disk

Pure Python, type hinted, fully testable.
Adapted from RAG_RAT/Core/services/session_service.py.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from Core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class SessionService:
    """
    Service for session management.

    Pure business logic — no UI dependencies.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        if storage_dir is None:
            try:
                from config_system import config

                storage_dir = config.BASE_DIR / "conversation_cache"
            except ImportError:
                storage_dir = Path.cwd() / "conversation_cache"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        logger.info(f"✓ SessionService initialized: {self.storage_dir}")

    def create_session(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        session: Dict[str, Any] = {
            "id": session_id,
            "user_id": user_id or "anonymous",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": [],
            "metadata": {},
        }
        self._active_sessions[session_id] = session
        self._save_session(session)
        logger.info(f"✓ Created session: {session_id}")
        return session

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Add a message to a session."""
        if not session_id:
            raise ValidationError("Session ID is required", field="session_id")
        if role not in ("user", "assistant", "system"):
            raise ValidationError(f"Invalid role: {role}", field="role")
        if not content or not content.strip():
            raise ValidationError("Content cannot be empty", field="content")

        session = self._get_or_load(session_id)
        msg: Dict[str, Any] = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        session["messages"].append(msg)
        session["updated_at"] = datetime.now().isoformat()
        self._save_session(session)
        return msg

    def get_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get the last *limit* messages for a session."""
        session = self._get_or_load(session_id)
        return session["messages"][-limit:]

    def clear_session(self, session_id: str) -> bool:
        """Clear all messages in a session."""
        session = self._get_or_load(session_id)
        session["messages"] = []
        session["updated_at"] = datetime.now().isoformat()
        self._save_session(session)
        self._active_sessions.pop(session_id, None)
        logger.info(f"✓ Cleared session: {session_id}")
        return True

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions (summaries only)."""
        summaries: List[Dict[str, Any]] = []
        for path in self.storage_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                summaries.append(
                    {
                        "id": data.get("id"),
                        "user_id": data.get("user_id"),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at"),
                        "message_count": len(data.get("messages", [])),
                    }
                )
            except Exception:
                continue
        return summaries

    # ─── Private helpers ─────────────────────────────────

    def _get_or_load(self, session_id: str) -> Dict[str, Any]:
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]
        path = self.storage_dir / f"{session_id}.json"
        if path.exists():
            try:
                session = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise ValidationError(f"Corrupt session file: {session_id}", field="session_id") from exc
            self._active_sessions[session_id] = session
            return session
        raise ValidationError(f"Session not found: {session_id}", field="session_id")

    def _save_session(self, session: Dict[str, Any]) -> None:
        path = self.storage_dir / f"{session['id']}.json"
        path.write_text(json.dumps(session, indent=2), encoding="utf-8")
