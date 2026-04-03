#!/usr/bin/env python3
"""
social_scanner.py — Social Media Chat Scanner for RAG_RAT
=========================================================

Supports:
  1. **WhatsApp**  — exported .txt chat files (Export Chat feature)
  2. **Telegram**  — exported JSON (Telegram Desktop) + live via Telethon API
  3. **Discord**   — exported JSON (DiscordChatExporter) + live via discord.py bot

Returns the standard ``(text, images, sources)`` tuple compatible with
``content_extractor.scan_web``, ``scan_folder``, and ``email_scanner``.

Usage::

    from social_scanner import (
        scan_whatsapp_export, scan_telegram_export, scan_telegram_live,
        scan_discord_export, scan_discord_live, scan_social,
    )

    # WhatsApp exported chat file
    text, images, sources = scan_whatsapp_export("chat.txt", max_messages=500)

    # Telegram exported JSON
    text, images, sources = scan_telegram_export("result.json", max_messages=500)

    # Telegram live (requires telethon + phone auth)
    text, images, sources = await scan_telegram_live(
        api_id=12345, api_hash="abc...", phone="+1234567890",
        chat_name="MyGroup", max_messages=200,
    )

    # Discord live (requires bot token)
    text, images, sources = await scan_discord_live(
        bot_token="...", channel_id=123456, max_messages=500,
    )
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  PLATFORM ENUM
# ═══════════════════════════════════════════════════════════════════════════════

SUPPORTED_PLATFORMS = ("whatsapp", "telegram", "discord")


# ═══════════════════════════════════════════════════════════════════════════════
#  WHATSAPP — Exported .txt Chat Parser
# ═══════════════════════════════════════════════════════════════════════════════

# Match patterns for different WhatsApp export locales:
#   12/25/23, 10:30 AM - John: Hello
#   [25/12/2023, 10:30:00] John: Hello
#   25.12.2023, 10:30 - John: Hello
_WA_PATTERNS = [
    # US: M/D/YY, H:MM AM/PM - Author: Msg
    re.compile(
        r"^(\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?)"
        r"\s*[-–]\s*"
        r"([^:]+):\s*(.+)",
        re.IGNORECASE,
    ),
    # Bracketed: [DD/MM/YYYY, HH:MM:SS] Author: Msg
    re.compile(
        r"^\[(\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}(?::\d{2})?)\]\s*"
        r"([^:]+):\s*(.+)",
    ),
    # European dot: DD.MM.YYYY, HH:MM - Author: Msg
    re.compile(
        r"^(\d{1,2}\.\d{1,2}\.\d{2,4},?\s*\d{1,2}:\d{2}(?::\d{2})?)"
        r"\s*[-–]\s*"
        r"([^:]+):\s*(.+)",
    ),
]

# System message patterns to skip
_WA_SYSTEM = re.compile(
    r"(Messages and calls are end-to-end encrypted|"
    r"created group|added|removed|left|changed the|"
    r"<Media omitted>|image omitted|video omitted|"
    r"audio omitted|sticker omitted|document omitted|"
    r"Missed voice call|Missed video call)",
    re.IGNORECASE,
)


def _parse_wa_line(line: str) -> Optional[Tuple[str, str, str]]:
    """Try to parse a WhatsApp chat line → (timestamp, author, message) or None."""
    for pat in _WA_PATTERNS:
        m = pat.match(line.strip())
        if m:
            return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
    return None


def scan_whatsapp_export(
    path: str,
    max_messages: int = 1000,
    progress_callback: Optional[Callable] = None,
    **kwargs,
) -> Tuple[str, List[Dict], List[Dict]]:
    """
    Parse a WhatsApp exported .txt chat file.

    Parameters
    ----------
    path : str
        Path to the exported .txt file.
    max_messages : int
        Maximum messages to ingest.
    progress_callback : optional
        ``callback(done, total)``

    Returns
    -------
    (str, List[Dict], List[Dict])
        Combined text, media list, source list.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"WhatsApp export not found: {path}")
    if not p.is_file():
        raise ValueError(f"Expected a file, got directory: {path}")

    raw = p.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines()

    messages: List[Dict] = []
    images: List[Dict] = []
    current_msg: Optional[Dict] = None

    for line in lines:
        parsed = _parse_wa_line(line)
        if parsed:
            if current_msg:
                messages.append(current_msg)
                if len(messages) >= max_messages:
                    break
            ts, author, text = parsed

            # Skip system messages
            if _WA_SYSTEM.search(text):
                # Track media as "images" metadata
                if any(kw in text.lower() for kw in ("media omitted", "image omitted", "video omitted")):
                    images.append({"type": "media", "author": author, "timestamp": ts})
                current_msg = None
                continue

            current_msg = {"timestamp": ts, "author": author, "text": text}
        elif current_msg and line.strip():
            # Continuation line (multi-line message)
            current_msg["text"] += "\n" + line.strip()

    # Flush last message
    if current_msg and len(messages) < max_messages:
        messages.append(current_msg)

    total = len(messages)
    logger.info(f"WhatsApp export: parsed {total} messages from {p.name}")

    # Build structured text blocks
    all_text: List[str] = []
    all_sources: List[Dict] = []

    for idx, msg in enumerate(messages):
        block = f"[{msg['timestamp']}] {msg['author']}:\n{msg['text']}\n"
        all_text.append(block)
        all_sources.append(
            {
                "type": "whatsapp",
                "path": f"whatsapp://{p.stem}/{idx}",
                "title": f"{msg['author']} — {msg['timestamp']}",
                "from": msg["author"],
                "date": msg["timestamp"],
                "chars": len(msg["text"]),
                "platform": "whatsapp",
            }
        )

        if progress_callback:
            try:
                progress_callback(idx + 1, total)
            except Exception as exc:
                logger.debug("%s", exc)

    combined = "\n".join(all_text)
    logger.info(f"WhatsApp scan done: {total} messages, {len(combined)} chars, {len(images)} media")
    return combined, images, all_sources


# ═══════════════════════════════════════════════════════════════════════════════
#  TELEGRAM — Exported JSON Parser
# ═══════════════════════════════════════════════════════════════════════════════


def _telegram_text_to_str(text_field: Any) -> str:
    """Convert Telegram's mixed text field to plain string.

    Telegram exports text as either a plain string or a list of
    text_entity dicts like [{"type": "plain", "text": "Hello"}, ...].
    """
    if isinstance(text_field, str):
        return text_field
    if isinstance(text_field, list):
        parts = []
        for item in text_field:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text", ""))
        return "".join(parts)
    return str(text_field) if text_field else ""


def scan_telegram_export(
    path: str,
    max_messages: int = 1000,
    progress_callback: Optional[Callable] = None,
    **kwargs,
) -> Tuple[str, List[Dict], List[Dict]]:
    """
    Parse a Telegram Desktop JSON export (``result.json``).

    Parameters
    ----------
    path : str
        Path to the exported JSON file.
    max_messages : int
        Maximum messages to ingest.
    progress_callback : optional
        ``callback(done, total)``

    Returns
    -------
    (str, List[Dict], List[Dict])
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Telegram export not found: {path}")

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {}

    chat_name = data.get("name", "Telegram Chat")
    raw_messages = data.get("messages", [])

    # Filter to actual text messages
    messages: List[Dict] = []
    images: List[Dict] = []

    for msg in raw_messages:
        if msg.get("type") != "message":
            continue

        text = _telegram_text_to_str(msg.get("text", ""))
        if not text.strip():
            # Check for media
            if msg.get("photo") or msg.get("file"):
                images.append(
                    {
                        "type": "media",
                        "media_type": msg.get("media_type", "unknown"),
                        "file": msg.get("file", msg.get("photo", "")),
                    }
                )
            continue

        messages.append(
            {
                "id": msg.get("id", ""),
                "author": msg.get("from", msg.get("actor", "Unknown")),
                "date": msg.get("date", ""),
                "text": text,
            }
        )

        if len(messages) >= max_messages:
            break

    total = len(messages)
    logger.info(f"Telegram export '{chat_name}': parsed {total} messages")

    all_text: List[str] = []
    all_sources: List[Dict] = []

    for idx, msg in enumerate(messages):
        block = f"[{msg['date']}] {msg['author']}:\n{msg['text']}\n"
        all_text.append(block)
        all_sources.append(
            {
                "type": "telegram",
                "path": f"telegram://{chat_name}/{msg['id']}",
                "title": f"{msg['author']} — {msg['date']}",
                "from": msg["author"],
                "date": msg["date"],
                "chars": len(msg["text"]),
                "platform": "telegram",
                "chat_name": chat_name,
            }
        )

        if progress_callback:
            try:
                progress_callback(idx + 1, total)
            except Exception as exc:
                logger.debug("%s", exc)

    combined = "\n".join(all_text)
    logger.info(f"Telegram scan done: {total} messages, {len(combined)} chars")
    return combined, images, all_sources


# ═══════════════════════════════════════════════════════════════════════════════
#  TELEGRAM — Live via Telethon (async)
# ═══════════════════════════════════════════════════════════════════════════════


async def scan_telegram_live(
    api_id: int,
    api_hash: str,
    phone: str,
    chat_name: str,
    max_messages: int = 200,
    session_name: str = "rag_rat_telegram",
    progress_callback: Optional[Callable] = None,
    **kwargs,
) -> Tuple[str, List[Dict], List[Dict]]:
    """
    Fetch messages from a Telegram chat/group using the Telethon API.

    Requires ``pip install telethon``.

    Parameters
    ----------
    api_id : int
        Telegram API ID from https://my.telegram.org
    api_hash : str
        Telegram API hash.
    phone : str
        Phone number (e.g. "+1234567890").
    chat_name : str
        Chat/group name or username (e.g. "@mygroup" or "My Group").
    max_messages : int
        Maximum messages to fetch.
    session_name : str
        Telethon session file name.
    progress_callback : optional
        ``callback(done, total)``

    Returns
    -------
    (str, List[Dict], List[Dict])
    """
    try:
        from telethon import TelegramClient
        from telethon.errors import SessionPasswordNeededError  # noqa: F401
    except ImportError:
        raise ImportError("telethon is required for live Telegram scanning. Install with: pip install telethon")

    session_dir = Path("data/social_sessions")
    session_dir.mkdir(parents=True, exist_ok=True)
    session_path = str(session_dir / session_name)

    client = TelegramClient(session_path, api_id, api_hash)
    await client.start(phone=phone)

    if not await client.is_user_authorized():
        raise PermissionError(
            "Telegram authentication failed. You may need to enter the code "
            "sent to your Telegram app. Run interactively first."
        )

    # Resolve chat entity
    try:
        entity = await client.get_entity(chat_name)
    except Exception as exc:
        await client.disconnect()
        raise ValueError(f"Cannot find Telegram chat '{chat_name}': {exc}") from exc

    messages_list: List[Dict] = []
    images: List[Dict] = []

    async for message in client.iter_messages(entity, limit=max_messages):
        if message.text:
            sender = ""
            if message.sender:
                sender = getattr(message.sender, "first_name", "") or ""
                last = getattr(message.sender, "last_name", "") or ""
                if last:
                    sender += f" {last}"
                if not sender:
                    sender = getattr(message.sender, "username", "Unknown") or "Unknown"

            messages_list.append(
                {
                    "id": message.id,
                    "author": sender,
                    "date": message.date.isoformat() if message.date else "",
                    "text": message.text,
                }
            )
        elif message.photo or message.document:
            images.append(
                {
                    "type": "media",
                    "media_type": "photo" if message.photo else "document",
                    "message_id": message.id,
                }
            )

        if progress_callback and messages_list:
            try:
                progress_callback(len(messages_list), max_messages)
            except Exception as exc:
                logger.debug("%s", exc)

    await client.disconnect()

    # Reverse to chronological order
    messages_list.reverse()

    total = len(messages_list)
    resolved_name = getattr(entity, "title", chat_name)
    logger.info(f"Telegram live '{resolved_name}': fetched {total} messages")

    all_text: List[str] = []
    all_sources: List[Dict] = []

    for idx, msg in enumerate(messages_list):
        block = f"[{msg['date']}] {msg['author']}:\n{msg['text']}\n"
        all_text.append(block)
        all_sources.append(
            {
                "type": "telegram",
                "path": f"telegram://{resolved_name}/{msg['id']}",
                "title": f"{msg['author']} — {msg['date']}",
                "from": msg["author"],
                "date": msg["date"],
                "chars": len(msg["text"]),
                "platform": "telegram",
                "chat_name": resolved_name,
            }
        )

    combined = "\n".join(all_text)
    logger.info(f"Telegram live scan done: {total} messages, {len(combined)} chars")
    return combined, images, all_sources


# ═══════════════════════════════════════════════════════════════════════════════
#  DISCORD — Exported JSON Parser (DiscordChatExporter format)
# ═══════════════════════════════════════════════════════════════════════════════


def scan_discord_export(
    path: str,
    max_messages: int = 1000,
    progress_callback: Optional[Callable] = None,
    **kwargs,
) -> Tuple[str, List[Dict], List[Dict]]:
    """
    Parse a Discord chat export JSON (DiscordChatExporter format).

    Parameters
    ----------
    path : str
        Path to the exported JSON file.
    max_messages : int
        Maximum messages to ingest.
    progress_callback : optional
        ``callback(done, total)``

    Returns
    -------
    (str, List[Dict], List[Dict])
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Discord export not found: {path}")

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {}

    guild_name = data.get("guild", {}).get("name", "Discord")
    channel_name = data.get("channel", {}).get("name", "unknown")
    raw_messages = data.get("messages", [])

    messages: List[Dict] = []
    images: List[Dict] = []

    for msg in raw_messages:
        content = msg.get("content", "").strip()
        author = msg.get("author", {}).get("name", "Unknown")
        timestamp = msg.get("timestamp", "")

        # Track embeds and attachments as images
        for att in msg.get("attachments", []):
            images.append(
                {
                    "type": "attachment",
                    "filename": att.get("fileName", ""),
                    "url": att.get("url", ""),
                }
            )

        if not content:
            continue

        messages.append(
            {
                "id": msg.get("id", ""),
                "author": author,
                "date": timestamp,
                "text": content,
            }
        )

        if len(messages) >= max_messages:
            break

    total = len(messages)
    logger.info(f"Discord export '{guild_name}/{channel_name}': parsed {total} messages")

    all_text: List[str] = []
    all_sources: List[Dict] = []

    for idx, msg in enumerate(messages):
        block = f"[{msg['date']}] {msg['author']}:\n{msg['text']}\n"
        all_text.append(block)
        all_sources.append(
            {
                "type": "discord",
                "path": f"discord://{guild_name}/{channel_name}/{msg['id']}",
                "title": f"{msg['author']} — {msg['date']}",
                "from": msg["author"],
                "date": msg["date"],
                "chars": len(msg["text"]),
                "platform": "discord",
                "guild": guild_name,
                "channel": channel_name,
            }
        )

        if progress_callback:
            try:
                progress_callback(idx + 1, total)
            except Exception as exc:
                logger.debug("%s", exc)

    combined = "\n".join(all_text)
    logger.info(f"Discord scan done: {total} messages, {len(combined)} chars")
    return combined, images, all_sources


# ═══════════════════════════════════════════════════════════════════════════════
#  DISCORD — Live via discord.py Bot
# ═══════════════════════════════════════════════════════════════════════════════


async def scan_discord_live(
    bot_token: str,
    channel_id: int,
    max_messages: int = 500,
    progress_callback: Optional[Callable] = None,
    **kwargs,
) -> Tuple[str, List[Dict], List[Dict]]:
    """
    Fetch messages from a Discord channel using a bot token.

    Requires ``pip install discord.py``.

    Parameters
    ----------
    bot_token : str
        Discord Bot token.
    channel_id : int
        Numeric channel ID.
    max_messages : int
        Maximum messages to fetch.
    progress_callback : optional
        ``callback(done, total)``

    Returns
    -------
    (str, List[Dict], List[Dict])
    """
    try:
        import discord
    except ImportError:
        raise ImportError("discord.py is required for live Discord scanning. Install with: pip install discord.py")

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    messages_list: List[Dict] = []
    images: List[Dict] = []
    fetch_done = False

    @client.event
    async def on_ready():
        nonlocal fetch_done
        try:
            channel = client.get_channel(channel_id)
            if channel is None:
                channel = await client.fetch_channel(channel_id)

            count = 0
            async for message in channel.history(limit=max_messages):
                if message.content:
                    messages_list.append(
                        {
                            "id": str(message.id),
                            "author": message.author.display_name,
                            "date": message.created_at.isoformat(),
                            "text": message.content,
                        }
                    )

                for att in message.attachments:
                    images.append(
                        {
                            "type": "attachment",
                            "filename": att.filename,
                            "url": att.url,
                        }
                    )

                count += 1
                if progress_callback:
                    try:
                        progress_callback(count, max_messages)
                    except Exception as exc:
                        logger.debug("%s", exc)
        except Exception as exc:
            logger.error(f"Discord fetch error: {exc}")
        finally:
            fetch_done = True
            await client.close()

    try:
        await client.start(bot_token)
    except Exception:
        pass  # client.close() was called in on_ready

    # Reverse to chronological order
    messages_list.reverse()

    total = len(messages_list)
    logger.info(f"Discord live: fetched {total} messages from channel {channel_id}")

    all_text: List[str] = []
    all_sources: List[Dict] = []

    for idx, msg in enumerate(messages_list):
        block = f"[{msg['date']}] {msg['author']}:\n{msg['text']}\n"
        all_text.append(block)
        all_sources.append(
            {
                "type": "discord",
                "path": f"discord://live/{channel_id}/{msg['id']}",
                "title": f"{msg['author']} — {msg['date']}",
                "from": msg["author"],
                "date": msg["date"],
                "chars": len(msg["text"]),
                "platform": "discord",
                "channel_id": str(channel_id),
            }
        )

    combined = "\n".join(all_text)
    return combined, images, all_sources


# ═══════════════════════════════════════════════════════════════════════════════
#  UNIFIED ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════


def scan_social(
    platform: str,
    mode: str = "export",
    **kwargs,
) -> Tuple[str, List[Dict], List[Dict]]:
    """
    Unified synchronous entry point for social media scanning.

    Parameters
    ----------
    platform : str
        One of ``"whatsapp"``, ``"telegram"``, ``"discord"``.
    mode : str
        ``"export"`` for file-based parsing, ``"live"`` for API-based.
    **kwargs
        Forwarded to the underlying scanner function.

    Returns
    -------
    (str, List[Dict], List[Dict])
    """
    platform = platform.lower().strip()

    if platform == "whatsapp":
        if mode == "live":
            raise NotImplementedError(
                "WhatsApp does not offer a public API for personal accounts. "
                "Please use the 'Export Chat' feature in WhatsApp to create a "
                ".txt file, then use mode='export'."
            )
        return scan_whatsapp_export(**kwargs)

    elif platform == "telegram":
        if mode == "live":
            import asyncio

            return asyncio.run(scan_telegram_live(**kwargs))
        return scan_telegram_export(**kwargs)

    elif platform == "discord":
        if mode == "live":
            import asyncio

            return asyncio.run(scan_discord_live(**kwargs))
        return scan_discord_export(**kwargs)

    else:
        raise ValueError(f"Unsupported platform: '{platform}'. Supported: {', '.join(SUPPORTED_PLATFORMS)}")
